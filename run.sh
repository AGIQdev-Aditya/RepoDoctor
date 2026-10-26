#!/usr/bin/env bash
# ==============================================================================
# RepoDoctor 1-Click Launch Script
# Modes:
#   ./run.sh            -> Web Console (http://127.0.0.1:8502)
#   ./run.sh --cli      -> Terminal Rich CLI
#   ./run.sh --streamlit -> Streamlit Console (http://localhost:8501)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Verify Ollama is running
if command -v ollama &> /dev/null; then
    if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
        echo "⚠️ Starting background Ollama service..."
        ollama serve > /dev/null 2>&1 &
        sleep 2
    fi
fi

# 2. Setup Virtual Environment if missing
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt rich
fi

# 3. Route execution by mode
if [ "$1" == "--cli" ]; then
    shift
    exec venv/bin/python cli.py "$@"
elif [ "$1" == "--streamlit" ]; then
    echo "🚀 Starting Streamlit Console on http://localhost:8501 ..."
    exec venv/bin/streamlit run ui.py --server.port=8501
else
    echo "🚀 Starting RepoDoctor Air-Gapped Console on http://127.0.0.1:8502 ..."
    exec venv/bin/python web_server.py
fi
