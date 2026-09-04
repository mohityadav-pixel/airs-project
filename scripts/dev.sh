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

# First run installs numpy/pandas/scikit-learn, which takes a few minutes on a
# laptop. Print progress rather than sitting silent — a quiet pip looks hung.
if [ ! -x .venv/bin/python ]; then
  echo "==> Creating the Python virtual environment (first run only)"
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import fastapi, sklearn, pandas" >/dev/null 2>&1; then
  echo "==> Installing backend dependencies"
  echo "    This downloads numpy, pandas and scikit-learn and takes 2-5 minutes"
  echo "    the first time. Later runs skip straight past this."
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r backend/requirements.txt
  echo "==> Backend dependencies ready"
fi

if [ ! -d frontend/node_modules ]; then
  echo "==> Installing frontend dependencies (about a minute)"
  (cd frontend && npm install)
fi

echo "==> Preparing the database"
(cd backend && "$ROOT/.venv/bin/python" -m app.db.init_db)

# A fresh database has stations but no readings, so the dashboard would be
# empty. Say what to do about it rather than showing blank cards.
READINGS=$(cd backend && "$ROOT/.venv/bin/python" - <<'PY'
try:
    from sqlalchemy import func, select
    from app.db.models import AirQualityReading
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        print(db.scalar(select(func.count()).select_from(AirQualityReading)) or 0)
except Exception:
    print(0)
PY
)
if [ "${READINGS:-0}" -eq 0 ]; then
  echo
  echo "    No readings stored yet, so the charts will be empty."
  echo "    In another terminal, either collect live data:"
  echo "        .venv/bin/python -m scripts.ingest"
  echo "    or generate a labelled demo history to explore straight away:"
  echo "        .venv/bin/python -m scripts.backfill_history --days 120"
  echo
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "==> Backend  http://localhost:8000  (API docs at /docs)"
(cd backend && "$ROOT/.venv/bin/python" -m uvicorn app.main:app --reload --port 8000) &

echo "==> Frontend http://localhost:5173"
(cd frontend && npm run dev) &

wait
