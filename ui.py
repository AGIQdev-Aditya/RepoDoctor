"""
RepoDoctor Executive Web Console (Streamlit Frontend)
Autonomous Codebase Health, Security Auditing, Test Synthesizer & Copilot.
Powered by Google Gemma 4 (via Ollama) with 3-Gate Verification Architecture.
"""

import os
from pathlib import Path
import streamlit as st
from engine import RepoDoctorEngine

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & METADATA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RepoDoctor — Code Intelligence & DevSecOps",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# PREMIUM LINEAR / VERCEL THEME & ANIMATIONS (Fixes Header Cutoff & Bad Colors)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Fix top header padding so title is NEVER cut off */
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1300px;
    }
    
    /* Make Streamlit top header bar blend seamlessly */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Pulse Dot Animation for Status Pill */
    @keyframes pulse-glow {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(0.85); opacity: 0.4; }
    }
    .pulse-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        margin-right: 6px;
        animation: pulse-glow 2s infinite ease-in-out;
    }

    /* Hero Header */
    .hero-container {
        margin-bottom: 1.2rem;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 50%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-sub {
        font-size: 0.95rem;
        color: #94a3b8;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.6rem;
    }

    /* Premium Status Pills */
    .status-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #34d399;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-pill-offline {
        display: inline-flex;
        align-items: center;
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.25);
        color: #a5b4fc;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Workflow Banner */
    .workflow-banner {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .step-badge {
        background: #1e293b;
        border: 1px solid #334155;
        color: #38bdf8;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 6px;
        font-size: 0.75rem;
    }

    /* Sleek Metric Cards with Hover Animations */
    .metric-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.1rem 1rem;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
        box-shadow: 0 8px 24px -4px rgba(56, 189, 248, 0.12);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.02em;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.06em;
        margin-top: 0.3rem;
    }

    /* Refined Grade Badges */
    .grade-badge-A { color: #34d399; font-size: 2.1rem; font-weight: 800; }
    .grade-badge-B { color: #38bdf8; font-size: 2.1rem; font-weight: 800; }
    .grade-badge-C { color: #fbbf24; font-size: 2.1rem; font-weight: 800; }
    .grade-badge-D { color: #f97316; font-size: 2.1rem; font-weight: 800; }
    .grade-badge-F { color: #f43f5e; font-size: 2.1rem; font-weight: 800; }

    /* Custom Primary Button Styling */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4) !important;
        transform: translateY(-1px) !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# ENGINE INITIALIZATION
# -----------------------------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state["engine"] = RepoDoctorEngine()

engine: RepoDoctorEngine = st.session_state["engine"]

# -----------------------------------------------------------------------------
# HERO HEADER (Properly spaced, never cut off)
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div class="hero-title">🩺 RepoDoctor</div>
    <div class="hero-sub">
        <span class="status-pill"><span class="pulse-dot"></span>Google Gemma 4 Active</span>
        <span class="status-pill-offline">🛡️ 100% Offline & Air-Gapped</span>
        <span>• Autonomous Codebase Health, Security & Test Engine</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Workflow Banner
st.markdown("""
<div class="workflow-banner">
    <span class="step-badge">1. TARGET</span> Choose repo in sidebar &nbsp;➔&nbsp;
    <span class="step-badge">2. AUDIT</span> Review architecture & vulnerabilities &nbsp;➔&nbsp;
    <span class="step-badge">3. RESOLVE</span> Synthesize tests, patches, or ask Copilot
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR REPOSITORY SELECTOR
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 📁 Select Repository")

base_workspace = Path(__file__).parent.parent
repodoctor_path = str(Path(__file__).parent.resolve())
workshop_path = str((base_workspace / "workshop-agent").resolve())

preset_options = {
    "RepoDoctor (Current Project)": repodoctor_path,
    "Workshop Agent (Hackathon Baseline)": workshop_path,
    "Custom Directory...": "custom"
}

chosen_preset = st.sidebar.radio(
    "Target Codebase:",
    list(preset_options.keys()),
    index=0
)

if chosen_preset == "Custom Directory...":
    target_repo = st.sidebar.text_input("Folder Path:", value=".")
else:
    target_repo = preset_options[chosen_preset]
    st.sidebar.caption(f"Inspecting: `{Path(target_repo).name}/`")

st.sidebar.markdown("### 🤖 Reasoning Engine")
model_choice = st.sidebar.selectbox(
    "Active Model:",
    ["gemma4:e4b", "gemma4:12b", "llama3.1:8b"],
    index=0,
    help="Gemma 4 e4b generates 16.6 tok/s directly on your GPU."
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Re-Scan Codebase", type="primary", use_container_width=True):
    with st.spinner("Analyzing repository through 3-Gate engine..."):
        st.session_state["diag"] = engine.get_full_diagnosis(target_repo)
        st.sidebar.success(f"Audit completed in {st.session_state['diag'].get('duration_sec', 0)}s!")

# Load initial state or update if target changed
if "current_target_repo" not in st.session_state or st.session_state["current_target_repo"] != target_repo:
    st.session_state["current_target_repo"] = target_repo
    with st.spinner("Initializing repository diagnostic..."):
        st.session_state["diag"] = engine.get_full_diagnosis(target_repo)

diag = st.session_state["diag"]
overview = diag.get("overview", {})
security = diag.get("security", {})
architecture = diag.get("architecture", {})

grade = security.get("grade", "N/A")
score = security.get("security_score", 0)

# -----------------------------------------------------------------------------
# TOP KPI METRICS BAR
# -----------------------------------------------------------------------------
mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)

with mcol1:
    grade_class = f"grade-badge-{grade[0]}" if grade in {"A+", "A", "B", "C", "D", "F"} else "metric-value"
    st.markdown(f"""
    <div class="metric-card">
        <div class="{grade_class}">{grade} <span style="font-size: 0.95rem; color: #64748b; font-weight: 500;">({score}/100)</span></div>
        <div class="metric-label">Security Grade</div>
    </div>
    """, unsafe_allow_html=True)

with mcol2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{overview.get('total_files', 0)}</div>
        <div class="metric-label">Files Scanned</div>
    </div>
    """, unsafe_allow_html=True)

with mcol3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{overview.get('total_lines_of_code', 0):,}</div>
        <div class="metric-label">Lines of Code</div>
    </div>
    """, unsafe_allow_html=True)

with mcol4:
    secrets_count = security.get("critical_secrets_found", 0)
    color = "#f43f5e" if secrets_count > 0 else "#34d399"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color: {color};">{secrets_count}</div>
        <div class="metric-label">Secrets Detected</div>
    </div>
    """, unsafe_allow_html=True)

with mcol5:
    vulns_count = security.get("vulnerabilities_found", 0)
    color = "#f43f5e" if vulns_count > 0 else "#34d399"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color: {color};">{vulns_count}</div>
        <div class="metric-label">Vulnerabilities</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# -----------------------------------------------------------------------------
# MAIN INTERACTIVE TABS
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive & Architecture",
    "🛡️ DevSecOps & Security",
    "🧪 Unit Test Synthesizer",
    "🔍 Semantic Code Search",
    "💬 AI Copilot (Supervisor)"
])

# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE & ARCHITECTURE
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("🗺️ Module Architecture & Dependency Graph")
    st.caption("Extracted via AST import inspection. Visualizes internal module connections.")
    
    cycles_count = architecture.get("circular_dependencies_detected", 0)
    if cycles_count > 0:
        st.error(f"⚠️ Warning: Detected {cycles_count} Circular Dependency Loop(s)!")
        for c in architecture.get("cycles", []):
            st.code(c, language="text")
    else:
        st.success("✅ Clean Architecture: Zero circular dependencies detected.")

    mermaid_code = architecture.get("mermaid_diagram", "flowchart TD\n  Empty[No Python Modules Detected]")
    st.markdown(f"```mermaid\n{mermaid_code}\n```")

    st.markdown("---")
    st.subheader("📈 Repository Composition")
    col_chart, col_table = st.columns([1, 1])

    with col_chart:
        st.write("**File Breakdown by Extension**")
        exts = overview.get("file_extensions", {})
        if exts:
            st.bar_chart(exts)
        st.write(f"**Comment Density:** `{overview.get('comment_density_pct', 0)}%` of code lines are documentation/comments.")

    with col_table:
        st.write("**Top Largest Files**")
        top_files = overview.get("top_5_largest_files", [])
        if top_files:
            st.dataframe(top_files, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: DEVSECOPS & SECURITY AUDITOR
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("🛡️ Automated Security Audit & Leaked Secret Hunter")
    st.caption("Scans for hardcoded API keys, private credentials, and dangerous execution patterns.")

    # Leaked Secrets Section
    secrets = security.get("secrets", [])
    if secrets:
        st.error(f"🚨 CRITICAL: Found {len(secrets)} hardcoded secrets in codebase!")
        st.dataframe(secrets, use_container_width=True)
    else:
        st.success("✅ Clean Secret Scan: No AWS keys, GitHub tokens, database passwords, or private keys found.")

    # Vulnerabilities Section
    vulns = security.get("vulnerabilities", [])
    if vulns:
        st.warning(f"⚠️ Detected {len(vulns)} Code Security Weaknesses:")
        
        # Severity Filter Pills
        sev_filter = st.radio("Filter by Severity:", ["All", "Critical", "High", "Medium"], horizontal=True)
        filtered_vulns = [v for v in vulns if sev_filter == "All" or v.get("severity") == sev_filter]

        for idx, v in enumerate(filtered_vulns):
            with st.expander(f"[{v['severity']}] {v['vulnerability']} — `{v['file']}:{v['line']}`", expanded=(idx == 0)):
                st.code(v["snippet"], language="python")
                st.info(f"💡 **Remediation:** {v['remediation']}")
                
                col_btn, col_res = st.columns([1, 3])
                with col_btn:
                    if st.button(f"🛠️ Generate AI Patch", key=f"patch_btn_{idx}", use_container_width=True):
                        with st.spinner("Gemma 4 drafting secure patch..."):
                            fix = engine.generate_vulnerability_fix(
                                vulnerability=v["vulnerability"],
                                snippet=v["snippet"],
                                file_path=v["file"],
                                model=model_choice
                            )
                            st.session_state[f"patch_{idx}"] = fix.get("fix_analysis", "")
                
                if f"patch_{idx}" in st.session_state:
                    st.markdown("#### 🔒 Gemma 4 Recommended Secure Fix:")
                    st.markdown(st.session_state[f"patch_{idx}"])
    else:
        st.success("✅ Clean Code Audit: Zero dangerous function calls or SQL/Command injection patterns found.")

# -----------------------------------------------------------------------------
# TAB 3: UNIT TEST SYNTHESIZER (Dynamic File Picker)
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("🧪 Autonomous Pytest Generator & Verification Sandbox")
    st.caption("Select an actual Python file from the repository, have Gemma generate tests, and execute them in a sandbox.")

    py_files = []
    base_p = Path(target_repo)
    if base_p.exists():
        for root, dirs, files in os.walk(base_p):
            dirs[:] = [d for d in dirs if d not in {".git", "venv", ".venv", "__pycache__"}]
            for f in sorted(files):
                if f.endswith(".py"):
                    rel = Path(root).relative_to(base_p) / f
                    py_files.append(str(rel))

    col_src_mode, col_file_sel = st.columns([1, 2])
    with col_src_mode:
        source_mode = st.radio("Source Mode:", ["Select Repo File", "Paste Custom Code"], horizontal=True)

    loaded_code = ""
    if source_mode == "Select Repo File" and py_files:
        with col_file_sel:
            selected_file = st.selectbox("Choose Python File to Test:", py_files)
        if selected_file:
            full_file_path = base_p / selected_file
            try:
                loaded_code = full_file_path.read_text(encoding="utf-8", errors="ignore")[:2500]
            except Exception:
                loaded_code = ""
    
    fn_input = st.text_area(
        "Python Code to Test:",
        value=loaded_code,
        height=160,
        placeholder="Paste Python code or select a file from the repository above..."
    )

    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if st.button("🤖 Synthesize Pytest Suite (Gemma 4)", type="primary", use_container_width=True):
            if fn_input.strip():
                with st.spinner("Gemma analyzing edge cases & writing tests..."):
                    synth = engine.synthesize_unit_test(fn_input, model=model_choice)
                    st.session_state["synth_test_code"] = synth.get("test_code", "")
            else:
                st.warning("Please select a file or paste Python code first.")

    test_editor = st.text_area(
        "Synthesized Pytest Suite:",
        value=st.session_state.get("synth_test_code", ""),
        height=180,
        placeholder="Synthesized test code will appear here. You can edit it before executing..."
    )

    with btn_col2:
        if st.button("⚡ Run Tests in Isolated Sandbox", use_container_width=True):
            if test_editor.strip():
                with st.spinner("Executing pytest inside isolated sandbox..."):
                    test_exec = engine.run_sandbox_test(test_editor, target_code=fn_input)
                    st.session_state["test_exec_result"] = test_exec
            else:
                st.warning("No test code available to execute. Generate or paste a test above.")

    if "test_exec_result" in st.session_state:
        tres = st.session_state["test_exec_result"]
        if tres.get("passed"):
            st.success(f"🎉 100% of Pytest Unit Tests Passed in {tres.get('duration_sec', 0)}s!")
        else:
            st.error("❌ Tests Failed or Encountered Assertions:")
        st.code(tres.get("output", "No output."), language="text")

# -----------------------------------------------------------------------------
# TAB 4: SEMANTIC CODE SEARCH (RAG)
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("🔍 Semantic Vector Code Search")
    st.caption("Powered by Ollama's `nomic-embed-text` with in-memory caching (sub-15ms queries).")

    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        search_query = st.text_input("Enter code query or concept:", placeholder="e.g. where are security checks handled? or dispatch tool gates")
    with q_col2:
        top_k = st.number_input("Top Matches", min_value=1, max_value=8, value=3)

    if st.button("🔎 Search Codebase", use_container_width=True):
        if search_query.strip():
            with st.spinner("Embedding query & searching vector chunks..."):
                search_res = engine.search_code(target_repo, query=search_query, top_k=top_k)
                st.session_state["search_res"] = search_res
        else:
            st.warning("Please enter a search query.")

    if "search_res" in st.session_state:
        sres = st.session_state["search_res"]
        results = sres.get("results", [])
        if results:
            st.write(f"**Found {len(results)} relevant code snippets:**")
            for idx, r in enumerate(results, 1):
                st.markdown(f"##### {idx}. `{r['file']}` (Lines {r['line_start']}–{r['line_end']}) — *Similarity: {r['similarity_score']}*")
                st.code(r["snippet"], language="python")
        else:
            st.info("No matching snippets found.")

# -----------------------------------------------------------------------------
# TAB 5: AI COPILOT (SUPERVISOR LOOP - Fixed Bottom-Anchored Input)
# -----------------------------------------------------------------------------
with tab5:
    st.subheader("💬 Deep Codebase Q&A & Supervisor Agent")
    st.caption("Full 3-Gate Autonomous Supervisor loop. Gemma decides which tools to call and verifies data.")

    st.write("**Quick Inquiries:**")
    qc1, qc2, qc3 = st.columns(3)
    preset_query = None
    if qc1.button("🔒 Security Architecture", use_container_width=True):
        preset_query = "Explain how the security and secret auditing works in this codebase."
    if qc2.button("🛡️ 3-Gate Security Loop", use_container_width=True):
        preset_query = "What are the 3 Security Gates and how do they prevent unauthorized code execution?"
    if qc3.button("🗺️ Module Dependencies", use_container_width=True):
        preset_query = "Summarize the architectural dependencies between modules in this repository."

    if "chat_msgs" not in st.session_state:
        st.session_state["chat_msgs"] = []

    # 1. Render all messages in chat history FIRST
    for msg in st.session_state["chat_msgs"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("thinking"):
                with st.expander("🧠 Gemma 4 Reasoning Trace"):
                    st.markdown(msg["thinking"])

    # 2. Render input box AT THE BOTTOM
    user_input = st.chat_input("Ask a question about this repository...")
    active_prompt = preset_query or user_input

    if active_prompt:
        st.session_state["chat_msgs"].append({"role": "user", "content": active_prompt})
        with st.chat_message("user"):
            st.markdown(active_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Gemma reasoning and orchestrating diagnostic tools..."):
                agent_res = engine.chat_with_agent(active_prompt, repo_path=target_repo, model=model_choice)
                ans = agent_res.get("final_response", "Diagnosis complete.")
                thinking = agent_res.get("thinking_trace", "")
                
                if thinking:
                    with st.expander("🧠 Gemma 4 Reasoning Trace"):
                        st.markdown(thinking)
                        
                st.markdown(ans)
                st.session_state["chat_msgs"].append({
                    "role": "assistant",
                    "content": ans,
                    "thinking": thinking
                })
        st.rerun()

# -----------------------------------------------------------------------------
# SIDEBAR REPORT EXPORTER
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 📥 Export Executive Report")
report_md = engine.export_markdown_report(target_repo)
st.sidebar.download_button(
    label="Download Audit Report (MD)",
    data=report_md,
    file_name="REPO_DOCTOR_AUDIT_REPORT.md",
    mime="text/markdown",
    use_container_width=True
)

st.sidebar.caption("RepoDoctor v1.0.0 | Hacktoberfest 2026")
