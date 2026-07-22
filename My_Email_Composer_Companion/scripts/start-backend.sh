#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your GROQ_API_KEY before generating emails."
fi

mkdir -p data uploads vector_db logs workspaces prompts

echo "==> Starting backend on :8000"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$ROOT/backend"
cd "$ROOT"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
