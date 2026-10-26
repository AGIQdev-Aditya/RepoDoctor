"""
Unit Verification and Audit Suite for RepoDoctor Tools
Tests security scanner, AST dependency mapper, vector code search, and test runner sandbox.
"""

import os
import sys
import tempfile
from pathlib import Path
from tools import (
    scan_security_and_secrets,
    map_architecture_dependencies,
    search_codebase,
    execute_test_sandbox,
    TOOLS
)


def audit_tools():
    print("==================================================")
    print("🔍 AUDITING REPO-DOCTOR CORE TOOLS (PHASE 1)")
    print("==================================================")

    # 1. Audit Tool Registry (Gate 1 Allowlist)
    assert len(TOOLS) == 4, f"Expected 4 tools in registry, found {len(TOOLS)}"
    print("✅ Gate 1 Tool Registry: 4/4 tools registered properly.")

    # 2. Audit Security Scanner
    print("\n--- Testing Security & Secret Scanner ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = Path(tmpdir) / "vulnerable_sample.py"
        with open(sample_file, "w") as f:
            f.write(
                'AWS_TOKEN = "AKIA1234567890ABCDEF"\n'
                'def run_input(user_data):\n'
                '    return eval(user_data)\n'
                'def safe_func():\n'
                '    return 42\n'
            )

        report = scan_security_and_secrets(tmpdir)
        assert report["status"] == "success"
        assert report["critical_secrets_found"] == 1, f"Expected 1 secret, found {report['critical_secrets_found']}"
        assert report["vulnerabilities_found"] == 1, f"Expected 1 vuln, found {report['vulnerabilities_found']}"
        assert report["secrets"][0]["type"] == "AWS Access Key"
        assert "eval" in report["vulnerabilities"][0]["vulnerability"]
        print(f"✅ Security Scanner Audit: Grade {report['grade']} ({report['security_score']}/100), detected {report['critical_secrets_found']} secrets & {report['vulnerabilities_found']} CVEs in {report['scan_duration_sec']}s.")

    # 3. Audit AST Dependency Mapper
    print("\n--- Testing AST Architecture Dependency Mapper ---")
    current_repo = Path(__file__).parent
    dep_report = map_architecture_dependencies(str(current_repo))
    assert dep_report["status"] == "success"
    assert "flowchart TD" in dep_report["mermaid_diagram"]
    print(f"✅ AST Dependency Mapper Audit: Found {dep_report['total_python_modules']} modules, generated Mermaid flowchart.")
    print("Mermaid Preview:\n" + "\n".join(dep_report["mermaid_diagram"].splitlines()[:4]))

    # 4. Audit Semantic Vector Search with nomic-embed-text
    print("\n--- Testing Semantic Vector Code Search (Ollama) ---")
    search_report = search_codebase(str(current_repo), query="security scanner secrets", top_k=2)
    assert search_report["status"] == "success"
    assert len(search_report["results"]) > 0, "Expected at least 1 search result"
    top_hit = search_report["results"][0]
    print(f"✅ Vector Search Audit: Top hit in '{top_hit['file']}' (lines {top_hit['line_start']}-{top_hit['line_end']}) with similarity {top_hit['similarity_score']:.4f}.")

    # 5. Audit Test Sandbox Runner (pytest)
    print("\n--- Testing Autonomous Test Sandbox ---")
    target_code = "def add(a, b):\n    return a + b\n"
    test_code = (
        "from target_module import add\n"
        "def test_add_positive():\n"
        "    assert add(2, 3) == 5\n"
        "def test_add_negative():\n"
        "    assert add(-1, -1) == -2\n"
    )
    test_res = execute_test_sandbox(test_code=test_code, target_code=target_code)
    assert test_res["status"] == "success"
    assert test_res["passed"] is True, f"Test failed with output: {test_res['output']}"
    print(f"✅ Test Sandbox Audit: Synthesized pytest passed in {test_res['duration_sec']}s.")

    print("\n==================================================")
    print("🎉 ALL 4 TOOLS PASSED 100% OF VERIFICATION AUDITS!")
    print("==================================================")


if __name__ == "__main__":
    audit_tools()
