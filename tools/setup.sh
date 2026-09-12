#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv_binary="${UV_BIN:-$(command -v uv || true)}"
if [[ -z "$uv_binary" && -x "$HOME/.local/bin/uv" ]]; then
  uv_binary="$HOME/.local/bin/uv"
fi
[[ -x "$uv_binary" ]] || { echo 'Install uv from https://docs.astral.sh/uv/getting-started/installation/' >&2; exit 1; }
if [[ ! -x .tools/venv/bin/python ]]; then
  "$uv_binary" venv --python 3.11 .tools/venv
fi
"$uv_binary" pip install --python .tools/venv/bin/python -r tools/requirements.txt
.tools/venv/bin/python tools/configure_mcp.py
