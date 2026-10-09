#!/usr/bin/env sh
set -eu
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
exec uvicorn backend.main:app --host "$HOST" --port "$PORT"
