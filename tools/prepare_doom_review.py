#!/usr/bin/env python3
"""Prepare a local Web review of the exported pack, with an ordinary walked route."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
site = ROOT / ".tools/checks/doom/site"
site.mkdir(parents=True, exist_ok=True)
for source in (ROOT / "builds/web").iterdir():
    if source.name == "index.html":
        continue
    target = site / source.name
    if not target.exists():
        target.symlink_to(source)
shutil.copyfile(ROOT / "tools/doom_review.gd", site / "doom_review.gd")
(site / "override.cfg").write_text('[application]\nrun/main_scene="/doom_review.tscn"\n')
(site / "doom_review.tscn").write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="/doom_review.gd" id="1"]\n[node name="DoomReview" type="Node"]\nscript = ExtResource("1")\n')
(site / "index.html").write_text('''<!doctype html><html lang="ru"><meta charset="utf-8">
<title>Свеча — проверка терминала</title><link rel="icon" href="data:,">
<style>body{margin:0;background:#111}canvas{display:block;width:100vw;height:100vh}</style>
<canvas id="canvas" tabindex="0"></canvas><script src="doom_bridge.js"></script><script src="index.js"></script>
<script>
const engine=new Engine({executable:'index',canvas:document.getElementById('canvas'),canvasResizePolicy:2,focusCanvas:true});
Promise.all(['override.cfg','doom_review.gd','doom_review.tscn'].map(f=>engine.preloadFile(f,'/'+f)))
.then(()=>engine.startGame()).then(()=>window.gameReady=true).catch(e=>console.error(e));
</script></html>''')
print(site)
