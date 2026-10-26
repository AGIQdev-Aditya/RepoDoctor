#!/usr/bin/env bash
# ==============================================================================
# RepoDoctor 1-Click Launch Script
# Starts the local air-gapped web console and verifies local Ollama engines.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🩺 LAUNCHING REPO-DOCTOR (100% LOCAL & AIR-GAPPED)"
echo "=================================================="

# 1. Verify Ollama is running
if ! command -v ollama &> /dev/null; then
    echo "❌ Error: 'ollama' is not installed or not in PATH."
    exit 1
fi

if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "⚠️ Ollama daemon not running. Attempting to start ollama serve..."
    ollama serve > /dev/null 2>&1 &
    sleep 2
fi

echo "✅ Ollama service is active."

# 2. Setup Virtual Environment if missing
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt
fi

echo "✅ Virtual environment verified."

# 3. Launch Streamlit Console
echo "🚀 Starting RepoDoctor Web Console on http://localhost:8501 ..."
venv/bin/streamlit run ui.py --server.port=8501 --server.headless=false
