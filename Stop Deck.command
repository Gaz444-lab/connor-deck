#!/bin/zsh
# Stop Connor's Deck local server
set -e
cd "$(dirname "$0")"

PORT=8764
PID_FILE=".server.pid"

echo ""
echo "=== Stopping Connor's Deck ==="

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  kill "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "Stopped process from PID file."
fi

if lsof -ti :$PORT >/dev/null 2>&1; then
  lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
  echo "Freed port $PORT."
fi

rm -f "$PID_FILE"
echo "Done."
echo ""
read -r "?Press Enter to close… "
