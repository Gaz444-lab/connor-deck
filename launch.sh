#!/bin/zsh
# Start Connor's Deck control plane and open the browser
set -e
cd "$(dirname "$0")"

PORT=8764
PID_FILE=".server.pid"
URL="http://127.0.0.1:${PORT}/"
LOG="/tmp/connor-deck-server.log"

# Already running?
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Connor's Deck already running — opening browser…"
  open "$URL"
  exit 0
fi

if lsof -ti :$PORT >/dev/null 2>&1; then
  echo "Port $PORT busy — opening existing Deck…"
  open "$URL"
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found — opening static UI only (launch/update API unavailable)."
  open "index.html"
  exit 0
fi

python3 server.py >>"$LOG" 2>&1 &
echo $! > "$PID_FILE"
sleep 0.4
open "$URL"
echo "Connor's Deck → $URL (PID $(cat "$PID_FILE"))"
