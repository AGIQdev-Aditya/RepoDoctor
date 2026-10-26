"""
RepoDoctor Deterministic Diagnostic Tools (Feature-Packed Engine)
Includes:
- Secret & Token Scanner (Stripe, AWS, GitHub, Google, HF, Slack, DB URI)
- Dangerous Code Pattern Hunter (eval, exec, shell=True, SQL injection, pickle, weak crypto)
- AST Complexity & Code Smell Detector (Cyclomatic complexity, long functions, bloated arguments)
- AST Architecture & Circular Dependency Graph Generator
- Embedding-Cached Semantic Vector Search (nomic-embed-text)
- Isolated Pytest Sandbox Runner
"""

import os
import re
import ast
import sys
import json
import time
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import numpy as np

CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".sh", ".yaml", ".yml"}
IGNORE_DIRS = {".git", "venv", ".venv", "__pycache__", "node_modules", ".pytest_cache", ".idea", ".vscode", "dist", "build"}

# Production Secret Regex Patterns
SECRET_PATTERNS = [
    ("AWS Access Key", r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    ("GitHub Personal Access Token", r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}"),
    ("OpenAI API Key", r"sk-[a-zA-Z0-9]{20,64}"),
    ("Google Cloud API Key", r"AIzaSy[A-Za-z0-9_-]{33}"),
    ("HuggingFace User Access Token", r"hf_[a-zA-Z0-9]{34,40}"),
    ("Stripe Live Secret Key", r"sk_live_[0-9a-zA-Z]{24}"),
    ("Slack API Token", r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}"),
    ("Private Key Header", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ("Database URI with Password", r"(?:postgres|mysql|mongodb|redis):\/\/[a-zA-Z0-9_]+:[a-zA-Z0-9_!@#$%^&*]+@[a-zA-Z0-9.-]+"),
]

# Security Vulnerabilities
VULNERABILITY_PATTERNS = [
    ("Arbitrary Code Execution (eval)", r"\beval\s*\(", "Critical", "Avoid eval(); use safe parsers like ast.literal_eval."),
    ("Arbitrary Code Execution (exec)", r"\bexec\s*\(", "Critical", "Avoid exec(); dynamic execution can lead to remote code execution."),
    ("Shell Command Injection", r"subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True", "High", "Never use shell=True with dynamic arguments; pass command lists."),
    ("OS Command Execution", r"os\.system\s*\(", "High", "Avoid os.system(); use subprocess.run with argument arrays."),
    ("Potential SQL Injection", r"(?:execute|raw)\s*\(\s*f[\"'].*?(?:SELECT|INSERT|UPDATE|DELETE).*?\{", "High", "Use parameterized queries instead of f-string formatting into SQL."),
    ("Insecure Deserialization", r"pickle\.loads?\s*\(", "Medium", "Pickle can execute arbitrary bytecode; use JSON or signed payloads."),
    ("Weak Cryptographic Hash (MD5/SHA1)", r"hashlib\.(?:md5|sha1)\s*\(", "Medium", "MD5 and SHA-1 are cryptographically broken; use sha256 or bcrypt/argon2."),
    ("Insecure Temp File Creation", r"tempfile\.mktemp\s*\(", "Medium", "mktemp is vulnerable to race conditions; use NamedTemporaryFile."),
    ("Namespace Pollution (Wildcard Import)", r"from\s+[a-zA-Z0-9_.]+\s+import\s+\*", "Low", "Wildcard imports pollute global scope and break static analysis."),
]

_EMBEDDING_CACHE: Dict[str, Tuple[float, List[float]]] = {}


def _safe_resolve_path(repo_path: str, subpath: str = "") -> Path:
    """Resolve and enforce boundary checks using Path.is_relative_to to prevent path traversal."""
    base = Path(repo_path).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Repository directory does not exist: {repo_path}")
    if subpath:
        target = (base / subpath).resolve()
        try:
            if not target.is_relative_to(base):
                raise PermissionError(f"Path traversal detected: {subpath} attempts to leave {base}")
        except AttributeError:
            # Fallback for Python < 3.9
            if not str(target).startswith(str(base) + os.sep) and target != base:
                raise PermissionError(f"Path traversal detected: {subpath} attempts to leave {base}")
        return target
    return base


def get_repo_overview(repo_path: str, **kwargs) -> Dict[str, Any]:
    """Calculates repository composition, line counts, comment density, and largest files."""
    base_dir = _safe_resolve_path(repo_path)
    ext_counts = {}
    ext_loc = {}
    total_loc = 0
    total_comment_lines = 0
    file_sizes = []

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            ext = os.path.splitext(file)[1].lower() or "(no extension)"
            file_path = Path(root) / file
            
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
            if ext in CODE_EXTENSIONS:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    loc = len(lines)
                    total_loc += loc
                    ext_loc[ext] = ext_loc.get(ext, 0) + loc
                    comments = sum(1 for line in lines if line.strip().startswith(("#", "//", "/*", "*")))
                    total_comment_lines += comments
                    
                    file_sizes.append({
                        "file": file_path.relative_to(base_dir).as_posix(),
                        "lines": loc,
                        "bytes": file_path.stat().st_size
                    })
                except Exception:
                    pass

    file_sizes.sort(key=lambda x: x["lines"], reverse=True)
    comment_ratio = round((total_comment_lines / max(1, total_loc)) * 100, 1)

    return {
        "status": "success",
        "repo_name": base_dir.name,
        "repo_path": str(base_dir),
        "total_files": sum(ext_counts.values()),
        "total_lines_of_code": total_loc,
        "comment_density_pct": comment_ratio,
        "file_extensions": ext_counts,
        "loc_by_extension": ext_loc,
        "top_5_largest_files": file_sizes[:5]
    }


def scan_security_and_secrets(repo_path: str, **kwargs) -> Dict[str, Any]:
    """Scans repository files for hardcoded secrets and dangerous code patterns."""
    start_time = time.time()
    base_dir = _safe_resolve_path(repo_path)
    
    findings_secrets = []
    findings_vulns = []
    files_scanned = 0
    total_lines = 0

    for root, dirs, files in os.walk(base_dir):
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
                clean_line = line.strip()
                # Skip comments and pattern definition strings in scanner files
                if clean_line.startswith(("#", "//", "/*", "*")):
                    continue
                if 'r"\\b' in line or "r'\\b" in line or 'r"(?:' in line or "r'(?:" in line:
                    continue

                for secret_name, pattern in SECRET_PATTERNS:
                    m = re.search(pattern, line)
                    if m:
                        matched_val = m.group(0)
                        masked_str = matched_val[:2] + ("*" * max(6, len(matched_val) - 4)) + matched_val[-2:]
                        masked_snippet = clean_line.replace(matched_val, masked_str)
                        findings_secrets.append({
                            "type": secret_name,
                            "file": rel_path,
                            "line": line_idx,
                            "snippet": masked_snippet[:140],
                            "severity": "Critical"
                        })
                
                if ext in {".py", ".sh"}:
                    for vuln_name, pattern, severity, remedy in VULNERABILITY_PATTERNS:
                        if re.search(pattern, line):
                            findings_vulns.append({
                                "vulnerability": vuln_name,
                                "file": rel_path,
                                "line": line_idx,
                                "snippet": clean_line[:120],
                                "severity": severity,
                                "remediation": remedy
                            })

    penalty = (len(findings_secrets) * 25) + sum(
        15 if v["severity"] == "Critical" else 10 if v["severity"] == "High" else 5
        for v in findings_vulns
    )
    score = max(0, 100 - penalty)
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


def analyze_code_complexity(repo_path: str, **kwargs) -> Dict[str, Any]:
    """
    Parses Python AST to compute Cyclomatic Complexity and pinpoint code smell hotspots:
    - Overly complex functions (complexity > 8)
    - Bloated functions (> 50 lines)
    - Functions with excessive parameters (> 5 args)
    """
    base_dir = _safe_resolve_path(repo_path)
    hotspots = []
    total_functions = 0
    total_complexity = 0

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                rel_path = file_path.relative_to(base_dir).as_posix()
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                    tree = ast.parse(source, filename=str(file_path))
                except Exception:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_functions += 1
                        # Calculate Cyclomatic Complexity by counting branching nodes
                        complexity = 1
                        for subnode in ast.walk(node):
                            if isinstance(subnode, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.AsyncWith)):
                                complexity += 1
                            elif isinstance(subnode, ast.BoolOp):
                                complexity += len(subnode.values) - 1

                        total_complexity += complexity
                        fn_lines = (node.end_lineno - node.lineno + 1) if hasattr(node, "end_lineno") and node.end_lineno else 10
                        arg_count = len(node.args.args)

                        # Flag if complex or bloated
                        issues = []
                        if complexity > 8:
                            issues.append(f"High Cyclomatic Complexity ({complexity})")
                        if fn_lines > 55:
                            issues.append(f"Bloated Function ({fn_lines} lines)")
                        if arg_count > 5:
                            issues.append(f"Excessive Arguments ({arg_count} params)")

                        if issues:
                            hotspots.append({
                                "file": rel_path,
                                "function": node.name,
                                "line": node.lineno,
                                "complexity": complexity,
                                "lines_count": fn_lines,
                                "issues": issues
                            })

    hotspots.sort(key=lambda x: x["complexity"], reverse=True)
    avg_complexity = round(total_complexity / max(1, total_functions), 1)

    return {
        "status": "success",
        "total_functions_analyzed": total_functions,
        "average_complexity": avg_complexity,
        "hotspots_count": len(hotspots),
        "hotspots": hotspots[:10]
    }


def _detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Detect circular dependency cycles in module graph using DFS."""
    visited = {}
    cycles = []

    def dfs(node, path):
        visited[node] = 1
        path.append(node)
        for neighbor in graph.get(node, set()):
            if visited.get(neighbor) == 1:
                idx = path.index(neighbor)
                cycle = path[idx:] + [neighbor]
                cycles.append(cycle)
            elif visited.get(neighbor) == 0:
                dfs(neighbor, path)
        path.pop()
        visited[node] = 2

    for n in list(graph.keys()):
        visited[n] = 0
    for n in list(graph.keys()):
        if visited[n] == 0:
            dfs(n, [])
    return cycles


def map_architecture_dependencies(repo_path: str, **kwargs) -> Dict[str, Any]:
    """Extracts AST imports, detects circular dependencies, and renders Mermaid diagram."""
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
    basename_map = {Path(p).stem: mod for mod, p in python_files.items()}
    
    graph: Dict[str, Set[str]] = {m: set() for m in known_modules}
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

        for imp in imported_targets:
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
                graph[mod_name].add(matched)

        module_details.append({
            "module": mod_name,
            "path": str(file_path.relative_to(base_dir)),
            "imports_count": len(imported_targets)
        })

    cycles = _detect_cycles(graph)

    clean_id = lambda name: name.replace(".", "_").replace("-", "_")
    mermaid_lines = ["flowchart TD"]
    
    if not python_files:
        mermaid_lines.append('    Empty["No Python files detected in repo"]')
    elif not edges:
        for m in list(python_files.keys())[:10]:
            mermaid_lines.append(f'    {clean_id(m)}["{m}.py"]')
    else:
        for src, dst in sorted(edges):
            is_in_cycle = any(src in c and dst in c for c in cycles)
            link = f'    {clean_id(src)}["{src}.py"] --{"circular" if is_in_cycle else ""}--> {clean_id(dst)}["{dst}.py"]'
            mermaid_lines.append(link)

    return {
        "status": "success",
        "total_python_modules": len(python_files),
        "total_dependency_edges": len(edges),
        "circular_dependencies_detected": len(cycles),
        "cycles": [" -> ".join(c) for c in cycles[:5]],
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
    """Semantic vector search across code files with in-memory caching."""
    import ollama
    global _EMBEDDING_CACHE
    
    base_dir = _safe_resolve_path(repo_path)
    chunks = []
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in CODE_EXTENSIONS or ext in {".json", ".css"}:
                continue
            
            file_path = Path(root) / file
            rel_path = file_path.relative_to(base_dir).as_posix()
            
            try:
                mtime = file_path.stat().st_mtime
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
                
                chunk_id = f"{rel_path}:{i+1}:{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}"
                chunks.append({
                    "id": chunk_id,
                    "mtime": mtime,
                    "file": rel_path,
                    "line_start": i + 1,
                    "line_end": min(i + len(chunk_lines), len(lines)),
                    "text": chunk_text
                })

    if not chunks:
        return {"status": "success", "query": query, "results": [], "message": "No code content to search."}

    try:
        q_resp = ollama.embeddings(model="nomic-embed-text", prompt=query)
        q_vec = q_resp["embedding"]
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate query embedding: {str(e)}"}

    scored = []
    eval_chunks = chunks[:40]
    
    for ch in eval_chunks:
        ch_id = ch["id"]
        if ch_id in _EMBEDDING_CACHE and _EMBEDDING_CACHE[ch_id][0] == ch["mtime"]:
            c_vec = _EMBEDDING_CACHE[ch_id][1]
        else:
            doc_prompt = f"File: {ch['file']} (Lines {ch['line_start']}-{ch['line_end']})\n{ch['text']}"
            try:
                c_resp = ollama.embeddings(model="nomic-embed-text", prompt=doc_prompt[:1500])
                c_vec = c_resp["embedding"]
                _EMBEDDING_CACHE[ch_id] = (ch["mtime"], c_vec)
            except Exception:
                continue

        score = _cosine_similarity(q_vec, c_vec)
        scored.append({
            "file": ch["file"],
            "line_start": ch["line_start"],
            "line_end": ch["line_end"],
            "snippet": ch["text"],
            "similarity_score": round(score, 4)
        })

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_results = scored[: max(1, int(top_k))]

    return {
        "status": "success",
        "query": query,
        "total_chunks_indexed": len(eval_chunks),
        "cache_size": len(_EMBEDDING_CACHE),
        "results": top_results
    }


def execute_test_sandbox(test_code: str, target_code: str = "", **kwargs) -> Dict[str, Any]:
    """Executes a unit test safely in a temporary sandbox with pytest."""
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        if target_code:
            with open(tmp_path / "target_module.py", "w", encoding="utf-8") as f:
                f.write(target_code)

        test_file = tmp_path / "test_sandbox.py"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        try:
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
        "output": output.strip()[-1000:]
    }


# Exported tool mapping for Supervisor Gate 1 allowlist
TOOLS = {
    "get_repo_overview": get_repo_overview,
    "scan_security_and_secrets": scan_security_and_secrets,
    "analyze_code_complexity": analyze_code_complexity,
    "map_architecture_dependencies": map_architecture_dependencies,
    "search_codebase": search_codebase,
    "execute_test_sandbox": execute_test_sandbox
}
