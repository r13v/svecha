#!/usr/bin/env python3
"""Apply the Web texture profile to the export copy, never to game/."""

from pathlib import Path
import re
import sys


def prepare(project: Path) -> None:
    icons = [path.stem for path in (project / "assets/icons").glob("*.jpg")]
    for path in project.rglob("*.import"):
        text = path.read_text()
        if 'importer="texture"' in text:
            name = path.name.lower()
            # Keep icon faces and the first-person hand sharp. The remaining
            # materials tile across surfaces and can use smaller images.
            close_up = "young_lightskinned" in name or any(icon in name for icon in icons)
            limit = 1024 if close_up else 512
            text = re.sub(r"^process/size_limit=\d+", f"process/size_limit={limit}", text, flags=re.M)
            if not name.endswith(".hdr.import"):
                # Source images and their GLB copies must use the same mip chain;
                # otherwise identical art is stored twice in different formats.
                text = re.sub(r"^mipmaps/generate=\w+", "mipmaps/generate=true", text, flags=re.M)
                normal = "nor_gl" in name or "normal" in name
                # Keep normal maps in VRAM compression; colors/roughness use
                # small lossy WebP files. Do not let 3D detection change the mode.
                mode = 2 if normal else 1
                text = re.sub(r"^compress/mode=\d+", f"compress/mode={mode}", text, flags=re.M)
                text = re.sub(r"^compress/lossy_quality=[\d.]+", "compress/lossy_quality=0.8", text, flags=re.M)
                text = re.sub(r"^detect_3d/compress_to=\d+", "detect_3d/compress_to=0", text, flags=re.M)
            path.write_text(text)
        elif path.name == "nave_shadow.png.import":
            # WebGL lacks RGTC. Preserve the full-size, lossless shadow mask.
            text = re.sub(r"^compress/mode=\d+", "compress/mode=0", text, flags=re.M)
            path.write_text(text)
    settings = project / "project.godot"
    settings.write_text(settings.read_text().replace("import_etc2_astc=true", "import_etc2_astc=false"))


if __name__ == "__main__":
    project = Path(sys.argv[1]).resolve()
    expected = Path(__file__).resolve().parent.parent / ".tools/web-project"
    if project != expected:
        raise SystemExit("Web preparation is only allowed in .tools/web-project")
    prepare(project)
