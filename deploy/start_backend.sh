#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python}"
APP_ENV="${APP_ENV:-development}"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
UVICORN_RELOAD="${UVICORN_RELOAD:-false}"

APP_ENV_NORMALIZED="$(echo "$APP_ENV" | tr '[:upper:]' '[:lower:]')"
ARGS=(
  -m uvicorn
  app.main:app
  --app-dir backend
  --host "$APP_HOST"
  --port "$APP_PORT"
  --proxy-headers
  --forwarded-allow-ips=*
)

if [[ "$UVICORN_RELOAD" == "true" && "$APP_ENV_NORMALIZED" != "production" ]]; then
  ARGS+=(--reload)
fi

echo "Starting backend (env=$APP_ENV_NORMALIZED host=$APP_HOST port=$APP_PORT reload=$UVICORN_RELOAD)"
exec "$PYTHON_BIN" "${ARGS[@]}"
