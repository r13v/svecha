#!/bin/sh
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TASK_WEB_PROJECT="$TASK_ROOT/.tools/web-project"
mkdir -p "$TASK_ROOT/builds/web" "$TASK_WEB_PROJECT"
rsync -a --delete --exclude='.godot/' "$TASK_ROOT/game/" "$TASK_WEB_PROJECT/"
# Профиль применяется только в копии для Web; исходники сохраняют качество.
python3 "$TASK_ROOT/tools/prepare_web.py" "$TASK_WEB_PROJECT"
"$TASK_ROOT/tools/godot" --headless --editor --path "$TASK_WEB_PROJECT" --import
"$TASK_ROOT/tools/godot" --headless --path "$TASK_WEB_PROJECT" --export-release Web "$TASK_ROOT/builds/web/index.html"
cp "$TASK_ROOT/game/assets/CREDITS_RU.txt" "$TASK_ROOT/builds/web/CREDITS_RU.txt"
cp "$TASK_ROOT/game/assets/GODOT_LICENSES.txt" "$TASK_ROOT/builds/web/GODOT_LICENSES.txt"
touch "$TASK_ROOT/builds/web/.nojekyll"
python3 "$TASK_ROOT/tools/compact_web.py" "$TASK_ROOT/builds/web" "$TASK_ROOT/.tools/checks/web-size.json"
