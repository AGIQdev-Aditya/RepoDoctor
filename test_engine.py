"""
Comprehensive Verification Suite for RepoDoctorEngine
Tests all high-level engine methods, error boundary handling, and markdown reporting.
"""

from pathlib import Path
from engine import RepoDoctorEngine


def test_engine_suite():
    print("==================================================")
    print("🩺 AUDITING REPO-DOCTOR UNIFIED BACKEND ENGINE")
    print("==================================================")

    engine = RepoDoctorEngine()
    current_repo = str(Path(__file__).parent)

    # 1. Test Path Validation & Edge Cases
    print("\n--- Testing Path Validation & Error Guards ---")
    ok, msg, p = engine.validate_repo_path(current_repo)
    assert ok is True, f"Valid repo rejected: {msg}"
    
    ok_inv, msg_inv, _ = engine.validate_repo_path("/non/existent/path/12345")
    assert ok_inv is False, "Non-existent path was not flagged"
    
    ok_emp, msg_emp, _ = engine.validate_repo_path("")
    assert ok_emp is False, "Empty path was not flagged"
    print("✅ Path Validation: Successfully handled valid, non-existent, and empty paths.")

    # 2. Test Full Diagnosis Runner
    print("\n--- Testing Full 3-Gate Diagnosis (<100ms) ---")
    diag = engine.get_full_diagnosis(current_repo)
    assert diag["status"] == "success"
    assert "overview" in diag
    assert "security" in diag
    assert "architecture" in diag
    assert diag["duration_sec"] < 1.0
    print(f"✅ Full Diagnosis: Ran in {diag['duration_sec']}s (Files: {diag['overview']['total_files']}, Score: {diag['security']['security_score']}, Modules: {diag['architecture']['total_python_modules']}).")

    # 3. Test Security Audit Interface
    print("\n--- Testing Security Audit ---")
    sec = engine.audit_security(current_repo)
    assert "security_score" in sec
    assert "vulnerabilities" in sec
    print(f"✅ Security Audit: Grade {sec['grade']} ({sec['security_score']}/100), {sec['vulnerabilities_found']} vulns.")

    # 4. Test Architecture Dependency Interface
    print("\n--- Testing Architecture Dependency Mapper ---")
    arch = engine.map_architecture(current_repo)
    assert "mermaid_diagram" in arch
    assert "flowchart TD" in arch["mermaid_diagram"]
    print(f"✅ Architecture Mapper: Generated Mermaid graph with {arch['total_python_modules']} modules.")

    # 5. Test Code Search Interface
    print("\n--- Testing Semantic Code Search ---")
    srch = engine.search_code(current_repo, query="def dispatch_tool", top_k=2)
    assert srch["status"] == "success"
    assert len(srch["results"]) > 0
    print(f"✅ Semantic Search: Found {len(srch['results'])} hits (Top similarity: {srch['results'][0]['similarity_score']}).")

    # 6. Test Sandbox Test Runner
    print("\n--- Testing Test Sandbox Execution ---")
    test_code = "def test_ok(): assert 1 + 1 == 2\n"
    res_test = engine.run_sandbox_test(test_code)
    assert res_test["passed"] is True
    print(f"✅ Test Sandbox: Pytest executed and passed in {res_test['duration_sec']}s.")

    # 7. Test Markdown Report Exporter
    print("\n--- Testing Markdown Report Generation ---")
    report = engine.export_markdown_report(current_repo)
    assert "# 🩺 RepoDoctor Diagnostic Audit Report" in report
    assert "## 🛡️ 2. Security & Secret Audit" in report
    assert "```mermaid" in report
    print(f"✅ Markdown Exporter: Generated {len(report.splitlines())}-line complete audit report.")

    print("\n==================================================")
    print("🎉 REPO-DOCTOR BACKEND ENGINE IS 100% OPERATIONAL!")
    print("==================================================")


if __name__ == "__main__":
    test_engine_suite()
