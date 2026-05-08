#!/usr/bin/env bash
# transcription — start backend + optionally open app window
# Standardized start script (compatible with ops-dashboard)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Optional .env overrides
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a; source "$SCRIPT_DIR/.env"; set +a
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-${transcription_PORT:-8039}}"
APP_URL="${APP_URL:-http://${HOST}:${PORT}/pinocchio}"
VENV_BIN="$SCRIPT_DIR/.venv/bin"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
REQUIREMENTS_STAMP="$SCRIPT_DIR/.venv/.requirements-stamp"
PID_FILE="$SCRIPT_DIR/.transcription.pid"
LOG_DIR="${LOG_DIR:-$HOME/.dev-logs}"
LOG_FILE="$LOG_DIR/transcription.log"

# ── stop any existing instance ───────────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
    old_pid=$(<"$PID_FILE")
    kill "$old_pid" 2>/dev/null || true
    rm -f "$PID_FILE"
fi
lsof -ti :"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true

# ── python venv ──────────────────────────────────────────────────────────────
if [[ ! -x "$VENV_BIN/python" ]]; then
    echo "Creating Python venv…"
    python3 -m venv "$SCRIPT_DIR/.venv"
fi
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    if [[ ! -f "$REQUIREMENTS_STAMP" || "$REQUIREMENTS_FILE" -nt "$REQUIREMENTS_STAMP" ]]; then
        echo "Installing Python dependencies…"
        "$VENV_BIN/pip" install -q --upgrade pip
        "$VENV_BIN/pip" install -q --prefer-binary -r "$REQUIREMENTS_FILE"
        touch "$REQUIREMENTS_STAMP"
    fi
fi

# ── start backend ────────────────────────────────────────────────────────────
echo "Starting transcription on :${PORT}…"
mkdir -p "$LOG_DIR"
nohup env PYTHONUNBUFFERED=1 \
    "$VENV_BIN/uvicorn" src.main:app --host "$HOST" --port "$PORT" \
    >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

# ── wait until backend is ready (up to 15 s) ─────────────────────────────────
echo "Waiting for backend…"
for i in $(seq 1 30); do
    if curl -sf "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# ── optional headless app launch ─────────────────────────────────────────────
if [[ -n "${OPEN_APP:-}" ]] && command -v open >/dev/null 2>&1; then
    echo "Opening $APP_URL"
    for candidate in \
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        "/Applications/Chromium.app/Contents/MacOS/Chromium" \
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"; do
        if [[ -x "$candidate" ]]; then
            "$candidate" --app="$APP_URL" --window-size=1300,920 --no-first-run --no-default-browser-check 2>/dev/null &
            break
        fi
    done
    open "$APP_URL" 2>/dev/null &
fi

echo ""
echo "transcription is running."
echo "  URL  : $APP_URL"
echo "  PID  : $(cat "$PID_FILE")"
echo "  Log  : $LOG_FILE"
echo "  Stop : ./stop.sh"
