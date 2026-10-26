"""
RepoDoctor Interactive Web Console (Streamlit Frontend)
Baseline UI ready for styling and customization by Abhay.
"""

import streamlit as st
from engine import RepoDoctorEngine

# Page configuration
st.set_page_config(
    page_title="RepoDoctor — Autonomous Codebase Health & DevSecOps",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Engine in session state
if "engine" not in st.session_state:
    st.session_state["engine"] = RepoDoctorEngine()

engine: RepoDoctorEngine = st.session_state["engine"]

# Custom Header
st.title("🩺 RepoDoctor")
st.caption("Autonomous Codebase Health, Security Auditing & PR Engine | Powered by Google Gemma & Ollama (100% Offline)")

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")
repo_path = st.sidebar.text_input("Target Repository Path", value=".")
model_choice = st.sidebar.selectbox("Gemma Reasoning Model", ["gemma4:e4b", "gemma4:12b", "llama3.1:8b"], index=0)

if st.sidebar.button("🚀 Run Full Diagnosis", type="primary", use_container_width=True):
    with st.spinner("Executing 3-Gate Diagnostic Suite..."):
        diag = engine.get_full_diagnosis(repo_path)
        st.session_state["diag"] = diag
        st.sidebar.success(f"Scanned in {diag.get('duration_sec', 0)}s!")

# Load cached diagnosis or run initial scan
if "diag" not in st.session_state:
    st.session_state["diag"] = engine.get_full_diagnosis(repo_path)

diag = st.session_state["diag"]
overview = diag.get("overview", {})
security = diag.get("security", {})
architecture = diag.get("architecture", {})

# Top KPI Metric Cards
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🩺 Security Grade", f"{security.get('grade', 'N/A')}", f"{security.get('security_score', 0)}/100")
col2.metric("📁 Files Scanned", f"{overview.get('total_files', 0)}")
col3.metric("💻 Total LOC", f"{overview.get('total_lines_of_code', 0)}")
col4.metric("🔐 Secrets Found", f"{security.get('critical_secrets_found', 0)}")
col5.metric("⚠️ Vulnerabilities", f"{security.get('vulnerabilities_found', 0)}")

st.divider()

# Main Interactive Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Executive Metrics & Architecture",
    "🛡️ DevSecOps & Security Auditor",
    "🧪 Unit Test Synthesizer",
    "💬 AI Code Copilot (Chat)"
])

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE METRICS & ARCHITECTURE
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("🗺️ Architecture & Component Dependencies")
    mermaid_code = architecture.get("mermaid_diagram", "flowchart TD\n  Empty[No Data]")
    st.markdown(f"```mermaid\n{mermaid_code}\n```")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("### 📈 Language Breakdown")
        exts = overview.get("file_extensions", {})
        if exts:
            st.bar_chart(exts)
    with col_b:
        st.write("### 📑 Top Largest Files")
        top_files = overview.get("top_5_largest_files", [])
        if top_files:
            st.dataframe(top_files, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: DEVSECOPS & SECURITY AUDITOR
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("🛡️ Detected Vulnerabilities & Leaked Secrets")
    
    secrets = security.get("secrets", [])
    if secrets:
        st.error(f"🚨 Found {len(secrets)} Leaked API Tokens / Secrets!")
        st.dataframe(secrets, use_container_width=True)
    else:
        st.success("✅ Zero leaked secrets or credentials detected in repository.")

    vulns = security.get("vulnerabilities", [])
    if vulns:
        st.warning(f"Found {len(vulns)} Code Security Weaknesses:")
        for idx, v in enumerate(vulns):
            with st.expander(f"[{v['severity']}] {v['vulnerability']} — `{v['file']}:{v['line']}`"):
                st.code(v["snippet"], language="python")
                st.info(f"💡 **Remediation:** {v['remediation']}")
                
                if st.button("🛠️ Generate AI Security Patch", key=f"fix_{idx}"):
                    with st.spinner("Gemma drafting secure replacement patch..."):
                        fix_res = engine.generate_vulnerability_fix(
                            vulnerability=v["vulnerability"],
                            snippet=v["snippet"],
                            file_path=v["file"],
                            model=model_choice
                        )
                        st.markdown(fix_res.get("fix_analysis", "Fix analysis complete."))
    else:
        st.success("✅ No dangerous function calls or code injection vulnerabilities found.")

# -----------------------------------------------------------------------------
# TAB 3: UNIT TEST SYNTHESIZER
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("🧪 Autonomous Pytest Generator & Sandbox")
    sample_code = "def calculate_discount(price: float, discount_pct: float) -> float:\n    if discount_pct < 0 or discount_pct > 100:\n        raise ValueError('Invalid discount')\n    return price * (1 - discount_pct / 100)\n"
    code_input = st.text_area("Function Code to Test:", value=sample_code, height=130)

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("🤖 Synthesize Pytest Suite (Gemma)", use_container_width=True):
            with st.spinner("Gemma writing test suite..."):
                test_synth = engine.synthesize_unit_test(code_input, model=model_choice)
                st.session_state["current_test_code"] = test_synth.get("test_code", "")

    test_code_to_run = st.text_area(
        "Synthesized Pytest Code:",
        value=st.session_state.get("current_test_code", ""),
        height=180
    )

    with col_btn2:
        if st.button("⚡ Execute Test in Isolated Sandbox", use_container_width=True):
            if test_code_to_run:
                with st.spinner("Running test inside safe pytest sandbox..."):
                    exec_res = engine.run_sandbox_test(test_code_to_run, target_code=code_input)
                    if exec_res.get("passed"):
                        st.success(f"🎉 All Tests Passed in {exec_res.get('duration_sec', 0)}s!")
                    else:
                        st.error("❌ Tests Failed or Encountered Errors:")
                    st.code(exec_res.get("output", "No output."), language="text")

# -----------------------------------------------------------------------------
# TAB 4: AI CODE COPILOT (CHAT)
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("💬 Deep Codebase Q&A & Semantic Copilot")
    st.caption("Ask questions, find bugs, or trace architectures using Gemma's 3-Gate Agent Loop.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("thinking"):
                with st.expander("🧠 Gemma Reasoning Chain"):
                    st.markdown(msg["thinking"])

    user_query = st.chat_input("Ask a question about this codebase...")
    if user_query:
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Gemma reasoning and dispatching tools..."):
                agent_res = engine.chat_with_agent(user_query, repo_path=repo_path, model=model_choice)
                final_text = agent_res.get("final_response", "Diagnosis complete.")
                thinking = agent_res.get("thinking_trace", "")
                
                if thinking:
                    with st.expander("🧠 Gemma Reasoning Chain"):
                        st.markdown(thinking)
                        
                st.markdown(final_text)
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": final_text,
                    "thinking": thinking
                })

# Sidebar Report Exporter
st.sidebar.divider()
st.sidebar.subheader("📥 Export Audit")
report_markdown = engine.export_markdown_report(repo_path)
st.sidebar.download_button(
    label="Download Audit Report (MD)",
    data=report_markdown,
    file_name="REPO_DOCTOR_AUDIT_REPORT.md",
    mime="text/markdown",
    use_container_width=True
)
