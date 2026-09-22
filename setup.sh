#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then
  if [ ! -x .venv/bin/python ]; then uv venv --python 3.12 .venv; fi
  uv pip install --python .venv/bin/python -r requirements.lock.txt
else
  if [ ! -x .venv/bin/python ]; then
    python3 -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ is required. Install Python or uv, then retry."'
    python3 -m venv .venv
  fi
  .venv/bin/python -m pip install -r requirements.lock.txt
fi
if [ ! -f frontend/dist/index.html ]; then
  cd frontend
  npm ci
  npm run build
fi
echo 'Signal Desk is ready. Run ./Start.command and open http://127.0.0.1:8765'
