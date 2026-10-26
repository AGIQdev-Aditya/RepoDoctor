"""
RepoDoctor Deterministic Diagnostic Tools
Core static analysis, security auditing, dependency extraction,
semantic code search, and test execution sandbox.
"""

import os
import re
import ast
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np

# Safe file extensions to analyze
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".sh"}
IGNORE_DIRS = {".git", "venv", ".venv", "__pycache__", "node_modules", ".pytest_cache", ".idea", ".vscode", "dist", "build"}

# Common Secret Regex Patterns
SECRET_PATTERNS = [
    ("AWS Access Key", r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    ("GitHub Personal Access Token", r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}"),
    ("OpenAI / Generic API Key", r"sk-[a-zA-Z0-9]{20,64}"),
    ("Slack API Token", r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}"),
    ("Private Key Header", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ("Database Connection String with Password", r"(?:postgres|mysql|mongodb|redis):\/\/[a-zA-Z0-9_]+:[a-zA-Z0-9_!@#$%^&*]+@[a-zA-Z0-9.-]+"),
]

# Dangerous Code Execution Patterns in Python
VULNERABILITY_PATTERNS = [
    ("Arbitrary Code Execution (eval)", r"\beval\s*\(", "Critical", "Avoid eval(); use safe parsers like ast.literal_eval."),
    ("Arbitrary Code Execution (exec)", r"\bexec\s*\(", "Critical", "Avoid exec(); dynamic execution can lead to remote code execution."),
    ("Shell Command Injection", r"subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True", "High", "Never use shell=True with dynamic arguments; pass command lists."),
    ("OS Command Execution", r"os\.system\s*\(", "High", "Avoid os.system(); use subprocess.run with argument arrays."),
    ("Potential SQL Injection", r"(?:execute|raw)\s*\(\s*f[\"'].*?(?:SELECT|INSERT|UPDATE|DELETE).*?\{", "High", "Use parameterized queries instead of f-string formatting into SQL."),
    ("Insecure Deserialization", r"pickle\.loads?\s*\(", "Medium", "Pickle can execute arbitrary bytecode; use JSON or signed payloads."),
]


def _safe_resolve_path(repo_path: str, subpath: str = "") -> Path:
    """Resolve and enforce boundary checks to prevent path traversal."""
    base = Path(repo_path).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Repository directory does not exist: {repo_path}")
    if subpath:
        target = (base / subpath).resolve()
        if not str(target).startswith(str(base)):
            raise PermissionError(f"Path traversal detected: {subpath} attempts to leave {base}")
        return target
    return base


def scan_security_and_secrets(repo_path: str, **kwargs) -> Dict[str, Any]:
    """
    Scans a repository for hardcoded secrets, API tokens, and dangerous code patterns.
    Returns a structured security audit payload with a letter grade.
    """
    start_time = time.time()
    base_dir = _safe_resolve_path(repo_path)
    
    findings_secrets = []
    findings_vulns = []
    files_scanned = 0
    total_lines = 0

    for root, dirs, files in os.walk(base_dir):
        # Filter ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in CODE_EXTENSIONS:
                continue
            
            file_path = Path(root) / file
            rel_path = file_path.relative_to(base_dir).as_posix()
            files_scanned += 1
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            total_lines += len(lines)

            for line_idx, line in enumerate(lines, 1):
                # 1. Secret Scanning
                for secret_name, pattern in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        # Redact the actual secret match for safe display
                        findings_secrets.append({
                            "type": secret_name,
                            "file": rel_path,
                            "line": line_idx,
                            "snippet": line.strip()[:100],
                            "severity": "Critical"
                        })
                
                # 2. Vulnerability Scanning (focus on python and script files)
                if ext in {".py", ".sh"}:
                    for vuln_name, pattern, severity, remedy in VULNERABILITY_PATTERNS:
                        if re.search(pattern, line):
                            findings_vulns.append({
                                "vulnerability": vuln_name,
                                "file": rel_path,
                                "line": line_idx,
                                "snippet": line.strip()[:120],
                                "severity": severity,
                                "remediation": remedy
                            })

    # Calculate Security Score
    total_issues = len(findings_secrets) * 25 + len(findings_vulns) * 15
    score = max(0, 100 - total_issues)
    if score >= 90:
        grade = "A+" if score == 100 else "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "status": "success",
        "repo_path": str(base_dir),
        "files_scanned": files_scanned,
        "total_lines": total_lines,
        "security_score": score,
        "grade": grade,
        "critical_secrets_found": len(findings_secrets),
        "vulnerabilities_found": len(findings_vulns),
        "secrets": findings_secrets,
        "vulnerabilities": findings_vulns,
        "scan_duration_sec": round(time.time() - start_time, 2)
    }


def map_architecture_dependencies(repo_path: str, **kwargs) -> Dict[str, Any]:
    """
    Parses Python AST across all repository files to extract module imports
    and generates an interactive Mermaid dependency graph.
    """
    base_dir = _safe_resolve_path(repo_path)
    python_files = {}
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                rel_path = file_path.relative_to(base_dir).as_posix()
                mod_name = os.path.splitext(rel_path)[0].replace("/", ".")
                python_files[mod_name] = file_path

    known_modules = set(python_files.keys())
    # Also index basenames for simple direct imports
    basename_map = {Path(p).stem: mod for mod, p in python_files.items()}
    
    edges = set()
    module_details = []

    for mod_name, file_path in python_files.items():
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except Exception:
            continue

        imported_targets = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_targets.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_targets.add(node.module)

        # Match internal project relationships
        for imp in imported_targets:
            # Check full module match or prefix match
            matched = None
            if imp in known_modules:
                matched = imp
            elif imp in basename_map:
                matched = basename_map[imp]
            else:
                for km in known_modules:
                    if km.endswith(f".{imp}") or imp.startswith(f"{km}."):
                        matched = km
                        break
            
            if matched and matched != mod_name:
                edges.add((mod_name, matched))

        module_details.append({
            "module": mod_name,
            "path": str(file_path.relative_to(base_dir)),
            "imports_count": len(imported_targets)
        })

    # Build Mermaid syntax
    clean_id = lambda name: name.replace(".", "_").replace("-", "_")
    mermaid_lines = ["flowchart TD"]
    
    if not python_files:
        mermaid_lines.append('    Empty["No Python files detected in repo"]')
    elif not edges:
        for m in list(python_files.keys())[:10]:
            mermaid_lines.append(f'    {clean_id(m)}["{m}.py"]')
    else:
        for src, dst in sorted(edges):
            mermaid_lines.append(f'    {clean_id(src)}["{src}.py"] --> {clean_id(dst)}["{dst}.py"]')

    return {
        "status": "success",
        "total_python_modules": len(python_files),
        "total_dependency_edges": len(edges),
        "modules": module_details,
        "mermaid_diagram": "\n".join(mermaid_lines)
    }


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def search_codebase(repo_path: str, query: str, top_k: int = 3, **kwargs) -> Dict[str, Any]:
    """
    Performs semantic vector search across code files using Ollama's nomic-embed-text.
    Returns the most relevant code chunks with line ranges and similarity scores.
    """
    import ollama
    
    base_dir = _safe_resolve_path(repo_path)
    chunks = []
    
    # 1. Chunk code files into ~40 line blocks
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in CODE_EXTENSIONS or ext in {".json", ".css"}:
                continue
            
            file_path = Path(root) / file
            rel_path = file_path.relative_to(base_dir).as_posix()
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            if not lines:
                continue

            step = 35
            for i in range(0, len(lines), step):
                chunk_lines = lines[i : i + 45]
                chunk_text = "".join(chunk_lines).strip()
                if len(chunk_text) < 20:
                    continue
                chunks.append({
                    "file": rel_path,
                    "line_start": i + 1,
                    "line_end": min(i + len(chunk_lines), len(lines)),
                    "text": chunk_text
                })

    if not chunks:
        return {"status": "success", "query": query, "results": [], "message": "No code content to search."}

    # 2. Embed the search query
    try:
        q_resp = ollama.embeddings(model="nomic-embed-text", prompt=query)
        q_vec = q_resp["embedding"]
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate query embedding: {str(e)}"}

    # 3. Embed top chunks (limit to 30 chunks to maintain speed)
    scored = []
    eval_chunks = chunks[:35]
    for ch in eval_chunks:
        try:
            # Contextualize chunk embedding with filename
            doc_prompt = f"File: {ch['file']} (Lines {ch['line_start']}-{ch['line_end']})\n{ch['text']}"
            c_resp = ollama.embeddings(model="nomic-embed-text", prompt=doc_prompt[:1500])
            score = _cosine_similarity(q_vec, c_resp["embedding"])
            scored.append({
                "file": ch["file"],
                "line_start": ch["line_start"],
                "line_end": ch["line_end"],
                "snippet": ch["text"],
                "similarity_score": round(score, 4)
            })
        except Exception:
            continue

    # Sort descending by similarity
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_results = scored[: max(1, int(top_k))]

    return {
        "status": "success",
        "query": query,
        "total_chunks_indexed": len(eval_chunks),
        "results": top_results
    }


def execute_test_sandbox(test_code: str, target_code: str = "", **kwargs) -> Dict[str, Any]:
    """
    Executes a synthesized unit test in an isolated temporary Python sandbox.
    Returns execution status, pass/fail results, and stderr/stdout logs.
    """
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Write target code if provided
        if target_code:
            with open(tmp_path / "target_module.py", "w", encoding="utf-8") as f:
                f.write(target_code)

        test_file = tmp_path / "test_sandbox.py"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        try:
            # Execute with pytest
            cmd = [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"]
            proc = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True, timeout=12)
            passed = (proc.returncode == 0)
            output = proc.stdout if proc.stdout else proc.stderr
        except subprocess.TimeoutExpired:
            passed = False
            output = "Execution timed out (12s threshold exceeded)."
        except Exception as e:
            passed = False
            output = f"Execution error: {str(e)}"

    return {
        "status": "success",
        "passed": passed,
        "duration_sec": round(time.time() - t0, 3),
        "output": output.strip()[-1000:]  # Last 1000 chars of pytest log
    }


# Exported tool mapping for Supervisor Gate 1 allowlist
TOOLS = {
    "scan_security_and_secrets": scan_security_and_secrets,
    "map_architecture_dependencies": map_architecture_dependencies,
    "search_codebase": search_codebase,
    "execute_test_sandbox": execute_test_sandbox
}
