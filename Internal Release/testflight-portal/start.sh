#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r backend/requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ""
  echo "Created .env from .env.example — add your Apple ID and Groq API key, then run again."
  exit 0
fi

cd backend
echo ""
echo "TestFlight Release Portal → http://127.0.0.1:8787"
echo ""
python -m uvicorn main:app --host 127.0.0.1 --port 8787 --reload
