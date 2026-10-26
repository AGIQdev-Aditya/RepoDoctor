# Contributing to RepoDoctor 🩺

Thank you for contributing to **RepoDoctor** during Hacktoberfest 2026!

## 🚀 How to Contribute

1. **Fork & Clone**
   ```bash
   git clone https://github.com/AGIQdev-Aditya/RepoDoctor.git
   cd RepoDoctor
   ```

2. **Set up Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run Verification Audits**
   Ensure all 3 security gates and tools pass:
   ```bash
   python demo_tools.py
   python test_engine.py
   ```

4. **Launch the Offline Console**
   ```bash
   python web_server.py
   # Or run: ./run.sh
   ```

5. **Submit a Pull Request**
   - Follow clean code practices.
   - Ground all diagnostics in deterministic AST inspection or Ollama Gemma reasoning.
   - Verify zero unhandled exceptions before opening your PR!

---
*Built with ❤️ for Hacktoberfest Hack Day Pune × NIAT–ADYPU 2026*
