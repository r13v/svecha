#!/usr/bin/env python3
"""Run the same rendered lighting regression on the exported WebGL resources."""

import argparse
import base64
import functools
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import threading


ROOT = Path(__file__).resolve().parent.parent
SESSION = "svecha-lighting-check"


def browser(*args):
    return subprocess.check_output(
        ["agent-browser", "--session", SESSION, *args], text=True
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true", help="Disable the fix; the regression must fail")
    args = parser.parse_args()
    mode = "baseline" if args.baseline else "fixed"
    output = ROOT / ".tools/checks/web-lighting" / mode
    server_files = ROOT / ".tools/checks/web-lighting/server"
    output.mkdir(parents=True, exist_ok=True)
    server_files.mkdir(parents=True, exist_ok=True)
    for source in (ROOT / "builds/web").iterdir():
        target = server_files / source.name
        if source.is_file() and not target.exists():
            target.symlink_to(source)
    shutil.copyfile(ROOT / "tools/check_lighting.gd", server_files / "lighting_check.gd")
    # Official export templates ignore --script. A config override selects the test
    # scene without rebuilding or modifying the exported game pack.
    (server_files / "override.cfg").write_text('[application]\nrun/main_scene="/lighting_bootstrap.tscn"\n')
    (server_files / "lighting_bootstrap.gd").write_text(
        'extends Node\n\nfunc _ready() -> void:\n'
        '\tvar tree := get_tree()\n'
        '\ttree.set_script(load("/lighting_check.gd"))\n'
        '\ttree.call_deferred("_run")\n'
    )
    (server_files / "lighting_bootstrap.tscn").write_text(
        '[gd_scene load_steps=2 format=3]\n'
        '[ext_resource type="Script" path="/lighting_bootstrap.gd" id="1"]\n'
        '[node name="LightingCheck" type="Node"]\nscript = ExtResource("1")\n'
    )
    (server_files / "review.html").write_text("""<!doctype html>
<html lang="ru"><meta charset="utf-8"><title>Проверка света «Свечи»</title><link rel="icon" href="data:,">
<style>body{margin:0;background:#000}canvas{display:block;width:960px;height:540px}</style>
<canvas id="canvas" width="960" height="540"></canvas><script src="index.js"></script>
<script>
const args = ['--'];
if (location.search.includes('baseline')) args.push('--baseline');
const engine = new Engine({executable:'index',canvas:document.getElementById('canvas'),
    canvasResizePolicy:0,focusCanvas:false,args});
Promise.all(['override.cfg','lighting_check.gd','lighting_bootstrap.gd','lighting_bootstrap.tscn']
    .map(file => engine.preloadFile(file, '/' + file)))
    .then(() => engine.startGame()).catch(error => {
        window.lightingCheck = {failures:[String(error)]};
        window.lightingCaptures = {};
    });
</script></html>""", encoding="utf-8")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(server_files))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        print(f"WEB_LIGHTING: {mode}, captures 960×540, benchmark 1600×900", flush=True)
        browser("--headed", "open", f"http://127.0.0.1:{server.server_port}/review.html?{mode}")
        browser("set", "viewport", "960", "540")
        try:
            browser("wait", "--fn", "window.lightingCheck !== undefined", "--timeout", "55000")
        except subprocess.CalledProcessError:
            print("WEB_LIGHTING: waiting for the rendered route", flush=True)
            browser("wait", "--fn", "window.lightingCheck !== undefined", "--timeout", "55000")
        data = json.loads(browser("eval", "({report:window.lightingCheck,captures:window.lightingCaptures})", "--json"))["data"]["result"]
        errors = json.loads(browser("errors", "--json"))["data"]["errors"]
        messages = json.loads(browser("console", "--json"))["data"]["messages"]
        if errors or (not args.baseline and any(message["type"] == "error" for message in messages)):
            data["report"]["failures"].append("Browser reported an error; see console.json and errors.json")
        (output / "report.json").write_text(json.dumps(data["report"], indent=2), encoding="utf-8")
        for label, image in data["captures"].items():
            (output / f"{label}.png").write_bytes(base64.b64decode(image))
        print(json.dumps(data["report"], ensure_ascii=False), flush=True)
        return 1 if data["report"]["failures"] else 0
    finally:
        for kind in ("console", "errors"):
            (output / f"{kind}.json").write_text(browser(kind, "--json"), encoding="utf-8")
        browser("close")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
