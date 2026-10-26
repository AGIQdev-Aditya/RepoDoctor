"""
Unit Verification and Audit Suite for RepoDoctor Tools (Extended & Optimized)
Audits:
1. Tool Registry (Gate 1 Allowlist)
2. High-level Repo Metric Profiling (LOC, languages, comment density)
3. Extended Security & Secret Scanning (Stripe, HuggingFace, Google, Weak Hashes, Wildcards)
4. AST Architecture Mapping with Circular Dependency Detection
5. In-Memory Cached Semantic Vector Search (Ollama)
6. Isolated Test Sandbox Runner (pytest)
"""

import os
import sys
import time
import tempfile
from pathlib import Path
from tools import (
    get_repo_overview,
    scan_security_and_secrets,
    map_architecture_dependencies,
    search_codebase,
    execute_test_sandbox,
    TOOLS
)


def audit_tools():
    print("==================================================")
    print("🔍 AUDITING REPO-DOCTOR CORE TOOLS (PHASE 1 - OPTIMIZED)")
    print("==================================================")

    # 1. Audit Tool Registry (Gate 1 Allowlist)
    assert len(TOOLS) == 5, f"Expected 5 tools in registry, found {len(TOOLS)}"
    print("✅ Gate 1 Tool Registry: 5/5 tools registered properly.")

    # 2. Audit Repo Overview Tool
    print("\n--- Testing Repo Overview Profiler ---")
    current_repo = Path(__file__).parent
    overview = get_repo_overview(str(current_repo))
    assert overview["status"] == "success"
    assert overview["total_files"] >= 3
    assert overview["total_lines_of_code"] > 100
    print(f"✅ Repo Overview Audit: Scanned {overview['total_files']} files ({overview['total_lines_of_code']} LOC, {overview['comment_density_pct']}% comments).")

    # 3. Audit Extended Security & Secret Scanner
    print("\n--- Testing Extended Security & Secret Scanner ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = Path(tmpdir) / "vulnerable_sample.py"
        # Construct simulated secret dynamically so Git push protection does not flag test fixture
        dummy_secret = "ghp_" + "FakeGitHubTokenForTesting1234567890ABCDEF"
        with open(sample_file, "w") as f:
            f.write(
                f'GITHUB_TOKEN = "{dummy_secret}"\n'
                'import hashlib\n'
                'def insecure_hash(data):\n'
                '    return hashlib.md5(data.encode()).hexdigest()\n'
                'def run_eval(user_data):\n'
                '    return eval(user_data)\n'
            )

        report = scan_security_and_secrets(tmpdir)
        assert report["status"] == "success"
        assert report["critical_secrets_found"] == 1
        assert report["vulnerabilities_found"] == 2  # md5 and eval
        print(f"✅ Extended Security Audit: Grade {report['grade']} ({report['security_score']}/100), detected {report['critical_secrets_found']} secrets & {report['vulnerabilities_found']} CVEs in {report['scan_duration_sec']}s.")

    # 4. Audit Circular Dependency Detection
    print("\n--- Testing AST Architecture & Circular Dependency Detection ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create circular dependency: module_a -> module_b -> module_a
        with open(Path(tmpdir) / "module_a.py", "w") as f:
            f.write("import module_b\ndef func_a(): return 1\n")
        with open(Path(tmpdir) / "module_b.py", "w") as f:
            f.write("import module_a\ndef func_b(): return 2\n")

        dep_report = map_architecture_dependencies(tmpdir)
        assert dep_report["status"] == "success"
        assert dep_report["circular_dependencies_detected"] >= 1, "Failed to detect circular dependency"
        print(f"✅ Circular Dependency Audit: Successfully detected {dep_report['circular_dependencies_detected']} circular cycles:")
        for c in dep_report["cycles"]:
            print(f"   ⚠️ Warning: {c}")

    # 5. Audit Vector Search with In-Memory Cache Speedup
    print("\n--- Testing Semantic Search with Embedding Cache ---")
    t0 = time.time()
    res1 = search_codebase(str(current_repo), query="security scanner secrets", top_k=2)
    t_first = time.time() - t0
    
    t0 = time.time()
    res2 = search_codebase(str(current_repo), query="security scanner secrets", top_k=2)
    t_cached = time.time() - t0
    
    assert res1["status"] == "success" and res2["status"] == "success"
    assert res1["results"][0]["file"] == res2["results"][0]["file"]
    print(f"✅ Vector Search Audit: First query took {t_first:.3f}s. Cached query took {t_cached:.3f}s (Cache size: {res2['cache_size']}).")

    # 6. Audit Test Sandbox Runner (pytest)
    print("\n--- Testing Autonomous Test Sandbox ---")
    target_code = "def multiply(a, b):\n    return a * b\n"
    test_code = (
        "from target_module import multiply\n"
        "def test_multiply():\n"
        "    assert multiply(3, 4) == 12\n"
        "def test_zero():\n"
        "    assert multiply(5, 0) == 0\n"
    )
    test_res = execute_test_sandbox(test_code=test_code, target_code=target_code)
    assert test_res["status"] == "success"
    assert test_res["passed"] is True
    print(f"✅ Test Sandbox Audit: Synthesized pytest passed in {test_res['duration_sec']}s.")

    print("\n==================================================")
    print("🎉 ALL 5 TOOLS PASSED 100% OF EXTENDED AUDITS!")
    print("==================================================")


if __name__ == "__main__":
    audit_tools()
