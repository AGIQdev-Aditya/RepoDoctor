# 🩺 RepoDoctor: Autonomous Codebase Health, Security & Automated PR Engine

> **Built for Hacktoberfest Hack Day Pune × NIAT–ADYPU 2026**  
> *100% Offline, Privacy-First Code Intelligence powered by Google Gemma (`gemma4:e4b`) and Ollama.*

---

## 👥 Team
- **Aditya Sharma** ([@AGIQdev-Aditya](https://github.com/AGIQdev-Aditya))
- **Abhay Singh** ([@abhaysingh1230](https://github.com/abhaysingh1230))

---

## 💡 The Problem
During Hacktoberfest and large open-source software cycles, maintainers and engineering teams face acute bottlenecks:
1. **Hidden Security Blindspots**: Codebases unknowingly leak API tokens, AWS keys, and harbor critical vulnerabilities (SQL Injection, command execution, path traversal).
2. **Missing Test Suites**: Rapid prototyping leaves critical business logic uncovered by unit tests.
3. **Architecture Opacity**: Complex dependency webs make onboarding difficult and result in fragile PRs.
4. **Cloud Privacy Risks**: Enterprise and proprietary code cannot be sent to public cloud LLM APIs.

---

## 🚀 The Solution: RepoDoctor
**RepoDoctor** is an air-gapped, local-first autonomous code health engine. It actively diagnoses repositories, hunts vulnerabilities, generates verified tests, and visualizes architecture graphs—all running locally on developer hardware with zero cloud data transmission.

### 🌟 Core Capabilities
1. 🛡️ **DevSecOps Secret & Vulnerability Hunter**: Detects leaked credentials and OWASP code injection risks, generating green/red git diff patches.
2. 🧪 **Autonomous Unit Test Synthesizer**: Inspects untested functions and synthesizes runnable, passing `pytest` test suites.
3. 🗺️ **Architecture & Dependency Mapper**: Parses Python AST import structures to render interactive dependency graphs.
4. 💬 **Semantic Code Copilot (RAG)**: Indexes local code with `nomic-embed-text` and reasons with `gemma4:e4b`, providing line-by-line citations and live reasoning traces.

---

## 🏗️ 3-Gate Verification Architecture
RepoDoctor strictly enforces the KT Workshop 3-Gate Execution Protocol:
- **Gate 1: Tool Allowlist Check** — Restricts LLM to registered diagnostic tools.
- **Gate 2: Signature Validation** — Enforces parameter bounds and type validity with `inspect.signature()`.
- **Gate 3: Safe Bounded Execution** — Sandbox guards prevent directory traversal (`../`) and unauthorized system modifications.

---

## 🛠️ Quickstart

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) running locally with:
  ```bash
  ollama pull gemma4:e4b
  ollama pull nomic-embed-text
  ```

### Installation
```bash
git clone https://github.com/AGIQdev-Aditya/RepoDoctor.git
cd RepoDoctor

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Launch the Web Console
```bash
streamlit run ui.py
```
