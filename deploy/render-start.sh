#!/bin/sh
set -eu

public_port="${PORT:-10000}"

PORT=8080 /usr/local/bin/worker &
worker_pid=$!

cleanup() {
  kill "$worker_pid" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

cd /app/IngestionService
exec uvicorn main:app --host 0.0.0.0 --port "$public_port"
