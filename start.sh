#!/usr/bin/env bash
# start.sh - used by Docker CMD
set -e
# create outputs dir if missing
mkdir -p "${OUTPUT_DIR:-./outputs}"
# start uvicorn
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
