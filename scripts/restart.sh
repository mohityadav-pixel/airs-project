#!/usr/bin/env bash
# Stop everything AIRS has running and start it again cleanly.
#
# Use this whenever the site shows "Could not load this / Not Found": that
# almost always means an old backend process is still holding port 8000 and
# serving code from before the last change. A stale server is invisible from
# the browser, so this script makes it explicit.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

echo "==> Stopping anything already running on ports 8000 and 5173"
for port in 8000 5173; do
  pids=$(lsof -ti :$port 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "    port $port was busy (pid $pids) — stopping it"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(lsof -ti :$port 2>/dev/null || true)
    # shellcheck disable=SC2086
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  else
    echo "    port $port free"
  fi
done
# Catch any uvicorn or vite this project started on another port.
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "airs-project/frontend.*vite" 2>/dev/null || true
sleep 1

echo
echo "==> Checking your data is where the app expects it"
"$ROOT/.venv/bin/python" - <<'PY'
import sqlite3, sys
from pathlib import Path
db_path = Path("data/airs.sqlite3")
if not db_path.exists():
    print("    !! no database at data/airs.sqlite3")
    print("       run: .venv/bin/python -m scripts.backfill_history --days 45")
    sys.exit(0)
db = sqlite3.connect(db_path)
cities = db.execute("select count(*) from cities").fetchone()[0]
readings = db.execute("select count(*) from air_quality_readings").fetchone()[0]
newest = db.execute("select max(observed_at) from air_quality_readings").fetchone()[0]
print(f"    {cities} cities, {readings:,} readings, newest {newest}")
if cities == 0 or readings == 0:
    print("    !! the database is empty")
    print("       run: .venv/bin/python -m scripts.backfill_history --days 45")
PY

models=$(ls backend/ml/artifacts/*.joblib 2>/dev/null | wc -l | tr -d ' ')
echo "    $models trained forecast models"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo
echo "==> Starting the backend on http://localhost:8000"
(cd backend && "$ROOT/.venv/bin/python" -m uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

# Do not send anyone to the site until the API actually answers, and prove the
# new endpoints exist rather than assuming a fresh process picked them up.
echo -n "    waiting for the API"
for _ in $(seq 1 40); do
  if curl -fsS http://localhost:8000/api/v1/system/health >/dev/null 2>&1; then
    echo " — up"
    break
  fi
  echo -n "."
  sleep 1
done

if curl -fsS "http://localhost:8000/api/v1/air-quality/india" >/dev/null 2>&1; then
  echo "    new India endpoint responding — this is the current code"
else
  echo "    !! the API is up but /air-quality/india is missing."
  echo "       An old server is still bound to port 8000. Close every other"
  echo "       Terminal tab running AIRS and run this script again."
fi

echo
echo "==> Starting the site on http://localhost:5173"
(cd frontend && npm run dev) &

echo
echo "    Open http://localhost:5173 once you see 'ready in ...' above."
echo "    Press Ctrl-C here to stop both."
wait
