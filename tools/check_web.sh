#!/bin/sh
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$TASK_ROOT"
mkdir -p .tools/checks
export AGENT_BROWSER_SESSION=svecha-web-check
python3 -m http.server 8788 --bind 127.0.0.1 --directory builds/web > .tools/checks/web-server.log 2>&1 &
TASK_SERVER_PID=$!
trap 'agent-browser console --json > .tools/checks/web-console.json; agent-browser errors --json > .tools/checks/web-errors.json; agent-browser screenshot "$TASK_ROOT/.tools/checks/web-browser-final.png" || true; agent-browser close; kill "$TASK_SERVER_PID"' EXIT
if [ "$(uname -s)" = Linux ]; then
	agent-browser --webgpu --headed open http://127.0.0.1:8788
else
	agent-browser --headed open http://127.0.0.1:8788
fi
agent-browser set viewport 640 360
agent-browser wait --fn '!document.getElementById("status")' --timeout 120000
agent-browser press Enter
agent-browser wait --fn 'document.pointerLockElement !== null'
# Пять секунд ходьбы приводят от старта к двери по обычным коллизиям.
agent-browser keydown w
agent-browser wait 5000
agent-browser keyup w
agent-browser press e
agent-browser wait 1500
agent-browser keydown w
agent-browser wait 2000
agent-browser keyup w
agent-browser screenshot "$TASK_ROOT/.tools/checks/web-browser-interior.png" || true
agent-browser press Escape
agent-browser wait --fn 'document.pointerLockElement === null'
agent-browser screenshot "$TASK_ROOT/.tools/checks/web-browser-pause.png" || true
agent-browser wait 1500
agent-browser press Enter
agent-browser wait --fn 'document.pointerLockElement !== null'
