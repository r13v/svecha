#!/bin/sh
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$TASK_ROOT/builds/macos"
"$TASK_ROOT/tools/godot" --headless --editor --path "$TASK_ROOT/game" --import
"$TASK_ROOT/tools/godot" --headless --path "$TASK_ROOT/game" --export-release macOS "$TASK_ROOT/builds/macos/Svecha.app"
cp "$TASK_ROOT/game/assets/CREDITS_RU.txt" "$TASK_ROOT/builds/macos/Svecha.app/Contents/Resources/CREDITS_RU.txt"
cp "$TASK_ROOT/game/assets/GODOT_LICENSES.txt" "$TASK_ROOT/builds/macos/Svecha.app/Contents/Resources/GODOT_LICENSES.txt"
# Updating Resources invalidates the local ad-hoc signature; re-sign this build.
codesign --force --deep --sign - "$TASK_ROOT/builds/macos/Svecha.app"
