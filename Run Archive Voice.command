#!/bin/zsh
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$APP_DIR/.venv/bin/python"

cd "$APP_DIR"

if [ ! -x "$PYTHON" ]; then
  echo "Archive Voice could not find its local Python environment."
  echo ""
  echo "Expected:"
  echo "$PYTHON"
  echo ""
  echo "Open Terminal once and run:"
  echo "cd \"$APP_DIR\""
  echo "python3 -m venv .venv"
  echo ".venv/bin/python -m pip install -e ."
  echo ""
  echo "Then double-click this file again."
  echo ""
  read "reply?Press Return to close this window."
  exit 1
fi

echo "Starting Archive Voice..."
echo "Keeping this Mac awake while Archive Voice is open."

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PYTHON" -m archive_voice
else
  "$PYTHON" -m archive_voice
fi
