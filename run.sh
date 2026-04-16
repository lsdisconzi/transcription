#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-${PINOCCHIO_PORT:-8039}}"
VENV_BIN="$SCRIPT_DIR/.venv/bin"

if [ ! -x "$VENV_BIN/python" ]; then
	python3 -m venv "$SCRIPT_DIR/.venv"
	"$VENV_BIN/pip" install -q -r requirements.txt
fi

echo "Starting SA-Pinocchio Transcription API on :$PORT..."
exec "$VENV_BIN/uvicorn" src.main:app --host 0.0.0.0 --port "$PORT" --reload
