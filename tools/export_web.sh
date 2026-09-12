#!/bin/sh
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TASK_WEB_PROJECT="$TASK_ROOT/.tools/web-project"
mkdir -p "$TASK_ROOT/builds/web" "$TASK_WEB_PROJECT"
rsync -a --delete --exclude='.godot/' "$TASK_ROOT/game/" "$TASK_WEB_PROJECT/"
# Лимит текстур применяется только в копии для Web; исходники сохраняют качество.
python3 - "$TASK_WEB_PROJECT" <<'PY'
import re
import sys
from pathlib import Path

project = Path(sys.argv[1])
for path in project.rglob('*.import'):
    text = path.read_text()
    if 'importer="texture"' in text:
        text = re.sub(r'^process/size_limit=\d+', 'process/size_limit=1024', text, flags=re.M)
        path.write_text(text)
settings = project / 'project.godot'
settings.write_text(settings.read_text().replace('import_etc2_astc=true', 'import_etc2_astc=false'))
PY
"$TASK_ROOT/tools/godot" --headless --editor --path "$TASK_WEB_PROJECT" --import
"$TASK_ROOT/tools/godot" --headless --path "$TASK_WEB_PROJECT" --export-release Web "$TASK_ROOT/builds/web/index.html"
cp "$TASK_ROOT/game/assets/CREDITS_RU.txt" "$TASK_ROOT/builds/web/CREDITS_RU.txt"
cp "$TASK_ROOT/game/assets/GODOT_LICENSES.txt" "$TASK_ROOT/builds/web/GODOT_LICENSES.txt"
touch "$TASK_ROOT/builds/web/.nojekyll"
