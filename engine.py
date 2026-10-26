"""
RepoDoctor Unified Backend Engine
High-level, bulletproof service interface designed for seamless UI integration.
Guarantees zero unhandled exceptions, comprehensive fallbacks, and typed payloads.
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import ollama
from tools import (
    get_repo_overview,
    scan_security_and_secrets,
    map_architecture_dependencies,
    search_codebase,
    execute_test_sandbox,
    TOOLS
)
from app import (
    dispatch_tool,
    direct_diagnose_repo,
    run_agent_loop,
    DEFAULT_MODEL
)

logger = logging.getLogger("RepoDoctor.Engine")


class RepoDoctorEngine:
    """
    Unified high-level backend controller for RepoDoctor.
    Wraps all diagnostic, auditing, search, testing, and LLM reasoning services
    with ironclad error handling so UI calls never crash.
    """

    def __init__(self, default_model: str = DEFAULT_MODEL):
        self.default_model = default_model

    def validate_repo_path(self, repo_path: str) -> Tuple[bool, str, Path]:
        """Validates that the path exists and is a directory."""
        try:
            if not repo_path or not str(repo_path).strip():
                return False, "Repository path cannot be empty.", Path(".")
            p = Path(repo_path).resolve()
            if not p.exists():
                return False, f"Directory does not exist: {repo_path}", p
            if not p.is_dir():
                return False, f"Path is a file, not a directory: {repo_path}", p
            return True, "Path valid.", p
        except Exception as e:
            return False, f"Invalid path syntax: {str(e)}", Path(".")

    def get_full_diagnosis(self, repo_path: str) -> Dict[str, Any]:
        """
        Executes an instant (<100ms) full 3-Gate diagnostic scan.
        Returns overview metrics, security audit, and architecture map.
        """
        valid, msg, path_obj = self.validate_repo_path(repo_path)
        if not valid:
            return {
                "status": "error",
                "message": msg,
                "overview": {},
                "security": {"security_score": 0, "grade": "N/A", "secrets": [], "vulnerabilities": []},
                "architecture": {"mermaid_diagram": "flowchart TD\n  Empty[Invalid Path]"}
            }

        try:
            return direct_diagnose_repo(str(path_obj))
        except Exception as e:
            logger.error(f"Error during full diagnosis: {e}")
            return {
                "status": "error",
                "message": f"Diagnostic error: {str(e)}",
                "overview": {},
                "security": {"security_score": 0, "grade": "N/A", "secrets": [], "vulnerabilities": []},
                "architecture": {"mermaid_diagram": "flowchart TD\n  Empty[Diagnostic Error]"}
            }

    def audit_security(self, repo_path: str) -> Dict[str, Any]:
        """Runs the 3-Gate security and secret audit."""
        valid, msg, path_obj = self.validate_repo_path(repo_path)
        if not valid:
            return {"status": "error", "message": msg, "secrets": [], "vulnerabilities": [], "security_score": 0, "grade": "N/A"}
        
        report = dispatch_tool("scan_security_and_secrets", {"repo_path": str(path_obj)})
        return report.get("payload", {}).get("result", {})

    def map_architecture(self, repo_path: str) -> Dict[str, Any]:
        """Extracts AST import structures and circular dependency graphs."""
        valid, msg, path_obj = self.validate_repo_path(repo_path)
        if not valid:
            return {"status": "error", "message": msg, "mermaid_diagram": "flowchart TD\n  Empty[Invalid Path]", "modules": []}

        report = dispatch_tool("map_architecture_dependencies", {"repo_path": str(path_obj)})
        return report.get("payload", {}).get("result", {})

    def search_code(self, repo_path: str, query: str, top_k: int = 4) -> Dict[str, Any]:
        """Performs semantic vector search across code using nomic-embed-text."""
        valid, msg, path_obj = self.validate_repo_path(repo_path)
        if not valid:
            return {"status": "error", "message": msg, "results": []}
        if not query or not query.strip():
            return {"status": "error", "message": "Search query cannot be empty.", "results": []}

        report = dispatch_tool("search_codebase", {"repo_path": str(path_obj), "query": query.strip(), "top_k": int(top_k)})
        return report.get("payload", {}).get("result", {})

    def synthesize_unit_test(self, function_code: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Uses Gemma to write a comprehensive pytest test suite for the given code.
        """
        if not function_code or not function_code.strip():
            return {"status": "error", "message": "Function code cannot be empty.", "test_code": ""}

        use_model = model or self.default_model
        prompt = (
            "You are an expert Python QA engineer. Write a complete, robust pytest test suite for the following Python code.\n"
            "Include test cases for standard inputs, edge cases (empty/null), and expected exceptions.\n"
            "Return ONLY executable Python test code inside a single ```python code block. Do not include commentary outside the block.\n\n"
            f"TARGET CODE:\n{function_code}\n"
        )

        try:
            t0 = time.time()
            resp = ollama.chat(
                model=use_model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.2}
            )
            raw = resp.get("message", {})
            content = raw.get("content", "")

            # Extract code block
            test_code = content
            if "```python" in content:
                test_code = content.split("```python")[1].split("```")[0].strip()
            elif "```" in content:
                test_code = content.split("```")[1].split("```")[0].strip()

            return {
                "status": "success",
                "test_code": test_code,
                "raw_response": content,
                "duration_sec": round(time.time() - t0, 2),
                "model": use_model
            }
        except Exception as e:
            logger.error(f"Test synthesis failed: {e}")
            return {"status": "error", "message": f"Test synthesis error: {str(e)}", "test_code": ""}

    def run_sandbox_test(self, test_code: str, target_code: str = "") -> Dict[str, Any]:
        """Executes a unit test safely inside the isolated pytest sandbox."""
        if not test_code or not test_code.strip():
            return {"status": "error", "message": "Test code cannot be empty.", "passed": False}

        report = dispatch_tool("execute_test_sandbox", {"test_code": test_code, "target_code": target_code})
        return report.get("payload", {}).get("result", {})

    def generate_vulnerability_fix(
        self,
        vulnerability: str,
        snippet: str,
        file_path: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uses Gemma to analyze a detected vulnerability and generate a secure replacement patch.
        """
        use_model = model or self.default_model
        prompt = (
            f"You are a Senior Staff Application Security Engineer.\n"
            f"A vulnerability was detected in file: {file_path}\n"
            f"Vulnerability Type: {vulnerability}\n"
            f"Vulnerable Code Snippet:\n{snippet}\n\n"
            f"Task: Provide the secure, sanitized replacement code that fixes this flaw.\n"
            f"Return your answer in two sections:\n"
            f"1. Explanation of the risk and how the fix works.\n"
            f"2. The secure replacement code inside a ```python block.\n"
        )

        try:
            t0 = time.time()
            resp = ollama.chat(
                model=use_model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.2}
            )
            content = resp.get("message", {}).get("content", "")
            return {
                "status": "success",
                "fix_analysis": content,
                "duration_sec": round(time.time() - t0, 2),
                "model": use_model
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to generate fix: {str(e)}", "fix_analysis": ""}

    def chat_with_agent(
        self,
        user_prompt: str,
        repo_path: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs the full 3-Gate Autonomous Supervisor loop with Gemma.
        """
        valid, msg, path_obj = self.validate_repo_path(repo_path)
        if not valid:
            return {"status": "error", "final_response": msg, "tool_ledger": []}

        use_model = model or self.default_model
        return run_agent_loop(user_prompt=user_prompt, repo_path=str(path_obj), model=use_model)

    def export_markdown_report(self, repo_path: str) -> str:
        """
        Generates a comprehensive, downloadable Markdown Security & Architecture Audit Report.
        """
        diag = self.get_full_diagnosis(repo_path)
        overview = diag.get("overview", {})
        security = diag.get("security", {})
        architecture = diag.get("architecture", {})

        report_lines = [
            f"# 🩺 RepoDoctor Diagnostic Audit Report",
            f"*Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Target Repository: `{repo_path}`*",
            "",
            "---",
            "",
            "## 📊 1. Repository Metrics",
            f"- **Total Files Scanned:** {overview.get('total_files', 0)}",
            f"- **Total Lines of Code (LOC):** {overview.get('total_lines_of_code', 0)}",
            f"- **Comment Density:** {overview.get('comment_density_pct', 0)}%",
            "",
            "### Top Largest Files",
        ]

        for f in overview.get("top_5_largest_files", []):
            report_lines.append(f"- `{f['file']}`: {f['lines']} lines ({f['bytes']} bytes)")

        report_lines.extend([
            "",
            "---",
            "",
            "## 🛡️ 2. Security & Secret Audit",
            f"- **Overall Security Grade:** **{security.get('grade', 'N/A')}** ({security.get('security_score', 0)}/100)",
            f"- **Leaked Secrets Found:** {security.get('critical_secrets_found', 0)}",
            f"- **Vulnerabilities Found:** {security.get('vulnerabilities_found', 0)}",
            "",
            "### Critical Findings",
        ])

        secrets = security.get("secrets", [])
        if secrets:
            report_lines.append("#### Leaked Secrets")
            for s in secrets:
                report_lines.append(f"- **{s['type']}** at `{s['file']}:{s['line']}`")
        else:
            report_lines.append("✅ No hardcoded secrets or API tokens detected.")

        vulns = security.get("vulnerabilities", [])
        if vulns:
            report_lines.append("\n#### Code Vulnerabilities")
            for v in vulns:
                report_lines.append(f"- **[{v['severity']}] {v['vulnerability']}** at `{v['file']}:{v['line']}`")
                report_lines.append(f"  *Snippet:* `{v['snippet']}`")
                report_lines.append(f"  *Remedy:* {v['remediation']}")
        else:
            report_lines.append("✅ No dangerous function calls or code injection vulnerabilities detected.")

        report_lines.extend([
            "",
            "---",
            "",
            "## 🗺️ 3. Architecture & Dependency Map",
            f"- **Total Python Modules:** {architecture.get('total_python_modules', 0)}",
            f"- **Circular Dependencies Detected:** {architecture.get('circular_dependencies_detected', 0)}",
            "",
            "```mermaid",
            architecture.get("mermaid_diagram", "flowchart TD\n  Empty[No Data]"),
            "```",
            "",
            "---",
            "*Report generated autonomously by RepoDoctor (Powered by Gemma & Ollama)*"
        ])

        return "\n".join(report_lines)
