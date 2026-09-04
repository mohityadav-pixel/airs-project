#!/usr/bin/env bash
# Start AIRS locally: backend on :8000, frontend on :5173.
# Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

if [ ! -f .env ]; then
  echo "No .env found. Copy .env.example to .env and fill in your keys."
  exit 1
fi

if [ ! -d .venv ]; then
  echo "==> Creating the Python virtual environment"
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r backend/requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  echo "==> Installing frontend dependencies"
  (cd frontend && npm install)
fi

echo "==> Preparing the database"
.venv/bin/python -m backend.app.db.init_db 2>/dev/null \
  || (cd backend && "$ROOT/.venv/bin/python" -m app.db.init_db)

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "==> Backend  http://localhost:8000  (docs at /docs)"
(cd backend && "$ROOT/.venv/bin/python" -m uvicorn app.main:app --reload --port 8000) &

echo "==> Frontend http://localhost:5173"
(cd frontend && npm run dev) &

wait
