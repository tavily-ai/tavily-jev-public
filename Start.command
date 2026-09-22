#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ] || [ ! -f frontend/dist/index.html ]; then
  bash setup.sh
fi
echo ''
echo 'Signal Desk · Jev + Tavily'
echo 'Open http://127.0.0.1:8765 in your browser.'
echo 'Keep this window open while using the app. Press Ctrl+C to stop.'
echo ''
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
