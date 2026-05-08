#!/usr/bin/env bash
# transcription — stop backend
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.transcription.pid"
PORT="${PORT:-${transcription_PORT:-8039}}"

if [[ -f "$PID_FILE" ]]; then
    pid=$(<"$PID_FILE")
    if kill "$pid" 2>/dev/null; then
        echo "Stopped transcription (PID $pid)"
    else
        echo "PID $pid was not running"
    fi
    rm -f "$PID_FILE"
fi

# Belt-and-braces: clear the port too
pids=$(lsof -ti :"$PORT" 2>/dev/null || true)
if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
    echo "Cleared port :$PORT"
fi

echo "Done"
