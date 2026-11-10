#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d venv ] || $PY -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example. Paste your API keys into .env."; }
echo
echo " RRR AI Help Desk is starting at  http://localhost:8000"
echo
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
