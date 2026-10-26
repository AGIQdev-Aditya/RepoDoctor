# 🎨 RepoDoctor UI Integration Guide (For Abhay & Frontend)

Welcome Abhay! The backend engine (`engine.py`) is fully built, hardened, and verified with zero unhandled exceptions. All services enforce the **3-Gate Security Loop** (Allowlist $\to$ Signature Check $\to$ Safe Bounded Execution).

You can build the Streamlit UI effortlessly by importing `RepoDoctorEngine`:

```python
from engine import RepoDoctorEngine
engine = RepoDoctorEngine()
```

---

## 🛠️ Quick Cheat-Sheet for Each Tab

### 1. Sidebar & Instant Dashboard Loading (< 60ms)
To populate KPI cards, language charts, and repo statistics instantaneously:
```python
repo_path = st.sidebar.text_input("Repository Path", value=".")
if st.sidebar.button("Run Full Diagnosis"):
    diag = engine.get_full_diagnosis(repo_path)
    st.session_state["diag"] = diag
```
**Data Structure in `diag`:**
* `diag["overview"]`: `{"total_files": 9, "total_lines_of_code": 1045, "comment_density_pct": 5.4, "top_5_largest_files": [...]}`
* `diag["security"]`: `{"security_score": 35, "grade": "F", "critical_secrets_found": 0, "vulnerabilities_found": 6, "secrets": [...], "vulnerabilities": [...]}`
* `diag["architecture"]`: `{"total_python_modules": 5, "circular_dependencies_detected": 0, "mermaid_diagram": "flowchart TD..."}`

---

### 2. Tab 1: 📊 Executive Metrics & Architecture
Display the Mermaid diagram directly in Streamlit:
```python
# Render Mermaid Architecture Map
st.subheader("🗺️ Architecture & Dependency Map")
mermaid_code = diag["architecture"]["mermaid_diagram"]
st.markdown(f"```mermaid\n{mermaid_code}\n```")
```

---

### 3. Tab 2: 🛡️ DevSecOps & Security Auditor
Display the security score, secrets, and vulnerabilities:
```python
sec = diag["security"]
st.metric("Security Grade", f"{sec['grade']} ({sec['security_score']}/100)")

# Vulnerability table
for v in sec["vulnerabilities"]:
    with st.expander(f"[{v['severity']}] {v['vulnerability']} at {v['file']}:{v['line']}"):
        st.code(v["snippet"], language="python")
        st.write(f"**Remedy:** {v['remediation']}")
        if st.button("Generate AI Patch", key=f"patch_{v['file']}_{v['line']}"):
            fix = engine.generate_vulnerability_fix(v["vulnerability"], v["snippet"], v["file"])
            st.markdown(fix["fix_analysis"])
```

---

### 4. Tab 3: 🧪 Autonomous Unit Test Synthesizer
Generate and execute tests live:
```python
code_to_test = st.text_area("Paste Python Code to Test", value="def add(a, b): return a + b")
if st.button("Synthesize Pytest Suite with Gemma"):
    test_res = engine.synthesize_unit_test(code_to_test)
    st.session_state["gen_test"] = test_res["test_code"]
    st.code(test_res["test_code"], language="python")

if "gen_test" in st.session_state and st.button("Run in Isolated Sandbox"):
    run_res = engine.run_sandbox_test(st.session_state["gen_test"], target_code=code_to_test)
    if run_res["passed"]:
        st.success(f"✅ All Tests Passed ({run_res['duration_sec']}s)!")
    else:
        st.error("❌ Tests Failed!")
    st.text(run_res["output"])
```

---

### 5. Tab 4: 💬 AI Code Copilot (3-Gate Supervisor Loop)
Chat with your codebase using Gemma 4 e4b:
```python
user_query = st.chat_input("Ask about this codebase...")
if user_query:
    with st.spinner("Gemma reasoning and dispatching tools..."):
        agent_res = engine.chat_with_agent(user_query, repo_path=repo_path)
        
        # Display thinking trace if available
        if agent_res.get("thinking_trace"):
            with st.expander("🧠 Gemma 4 Reasoning Trace"):
                st.markdown(agent_res["thinking_trace"])
                
        # Display final synthesized answer
        st.markdown(agent_res["final_response"])
```

---

### 6. 📄 1-Click Export Report Button
Download complete Markdown audit report:
```python
report_md = engine.export_markdown_report(repo_path)
st.download_button(
    label="📥 Download Executive Audit Report (Markdown)",
    data=report_md,
    file_name="REPO_DOCTOR_AUDIT_REPORT.md",
    mime="text/markdown"
)
```
