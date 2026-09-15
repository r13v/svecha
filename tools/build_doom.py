#!/usr/bin/env python3
"""Собрать порт Cloudflare для 3D-экрана. Требуется Emscripten 3.1.64.

EMCC=/path/to/emcc python3 tools/build_doom.py
Исходники зафиксированы; патчи, лицензии и исходный архив поставляются с WASM.
"""
import os
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
REVISION = "65e0d3ae2ffa604155eebd96ed40da6567bd08f4"
WORK = ROOT / ".tools/doom-build"
OUT = ROOT / "game/web/doom"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    archive = OUT / "upstream-source.tar.gz"
    if not archive.exists():
        urllib.request.urlretrieve(f"https://codeload.github.com/cloudflare/doom-wasm/tar.gz/{REVISION}", archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != "9be6e02bb1f4f4b00f73d21b0c1ba4f2b8087e3c6cb1f477435baa390b3aa482":
        raise ValueError("Unexpected upstream source archive")
    WORK.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as source:
        source.extractall(WORK, filter="data")
    source = WORK / f"doom-wasm-{REVISION}"
    shutil.copyfile(ROOT / "tools/doom/config.h", source / "config.h")
    types = source / "src/doomtype.h"
    # Doom uses -1 sentinels in boolean fields and assumes their original
    # enum-sized layout. Emscripten's stdbool inclusion must not change this.
    types.write_text(re.sub(
        r"#if defined\(__cplusplus\) \|\| defined\(__bool_true_false_are_defined\).*?\n#endif",
        "typedef enum { DOOM_FALSE, DOOM_TRUE } boolean;",
        types.read_text(), count=1, flags=re.S))
    video = source / "src/i_video.c"
    text = video.read_text()
    text = text.replace("void I_FinishUpdate (void)", "extern void svecha_frame(unsigned char *, SDL_Color *);\nvoid I_FinishUpdate (void)")
    text = text.replace("    UpdateGrab();\n", "    svecha_frame(I_VideoBuffer, palette);\n    return;\n    UpdateGrab();\n", 1)
    video.write_text(text)
    loop = source / "src/doom/d_main.c"
    text = loop.read_text().replace("void D_RunFrame()", "extern int svecha_is_active(void);\nvoid D_RunFrame()")
    text = text.replace("    if (wipe) {", "    if (!svecha_is_active()) return;\n    screenvisible = true;\n    if (wipe) {")
    loop.write_text(text)
    timer = source / "src/i_timer.c"
    text = timer.read_text().replace("static Uint32 basetime = 0;", "extern Uint32 svecha_ticks(void);\nstatic Uint32 basetime = 0;")
    timer.write_text(text.replace("ticks = SDL_GetTicks();", "ticks = svecha_ticks();"))
    opl = source / "opl/opl.c"
    # SDL's software OPL3 is known, not physical hardware to probe. The upstream
    # probe waits for an audio callback using SDL_CondWait, deadlocking a browser
    # main thread (and explaining the demo's -nomusic option).
    text = opl.read_text().replace("result1 = OPL_Detect();\n    result2 = OPL_Detect();",
                                  "result1 = OPL_INIT_OPL3;\n    result2 = OPL_INIT_OPL3;")
    opl.write_text(text)
    system = source / "src/i_system.c"
    system.write_text(system.read_text().replace("exit(-1);", "emscripten_force_exit(1);"))

    # Use upstream's curated source lists; omit platform examples and test mains.
    files = []
    for directory, names in {
        "src": ["COMMON_SOURCE_FILES", "GAME_SOURCE_FILES", "DEHACKED_SOURCE_FILES"],
        "src/doom": ["libdoom_a_SOURCES"], "opl": ["libopl_a_SOURCES"],
        "pcsound": ["libpcsound_a_SOURCES"], "textscreen": ["libtextscreen_a_SOURCES"],
    }.items():
        makefile = (source / directory / "Makefile.am").read_text().replace("\\\n", " ")
        for name in names:
            row = re.search(rf"^{name}\s*=([^\n]+)", makefile, re.M).group(1)
            files += [str(source / directory / filename) for filename in row.split() if filename.endswith(".c")]
    emcc = os.environ.get("EMCC", str(ROOT / ".tools/emsdk/upstream/emscripten/emcc"))
    version = subprocess.check_output([emcc, "--version"], text=True).splitlines()[0]
    if "3.1.64" not in version:
        raise ValueError("This adapter is verified with Emscripten 3.1.64: " + version)
    # Supply true/false consistently; doomtype.h retains enum-sized boolean.
    flags = ["-O2", "-include", "stdbool.h",
             "-sUSE_SDL=2", "-sUSE_SDL_MIXER=2", "-sSDL2_MIXER_FORMATS=[]", "-sUSE_SDL_NET=2",
             "-sASYNCIFY", "-sALLOW_MEMORY_GROWTH=1", "-sINITIAL_MEMORY=67108864",
             "-sFORCE_FILESYSTEM=1", "-sEXPORTED_RUNTIME_METHODS=['FS','callMain']",
             "-sEXPORTED_FUNCTIONS=['_main','_svecha_key','_svecha_mouse','_svecha_set_active']",
             "-sINVOKE_RUN=0", "-sEXIT_RUNTIME=0", "-lwebsocket.js"]
    includes = [f"-I{source / path}" for path in [".", "src", "src/doom", "opl", "pcsound", "textscreen"]]
    subprocess.run([emcc, *files, str(ROOT / "tools/doom/bridge.c"), *includes, *flags, "-o", str(OUT / "doom.js")], check=True)
    shutil.copyfile(source / "COPYING.md", OUT / "ENGINE_LICENSE.txt")
    # Corresponding adapter/build source travels alongside the binary.
    with tarfile.open(OUT / "svecha-adapter-source.tar.gz", "w:gz") as archive:
        for path in [ROOT / "tools/build_doom.py", *sorted((ROOT / "tools/doom").iterdir())]:
            archive.add(path, arcname=str(path.relative_to(ROOT)))
    manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "manifest.json"}
    manifest.update(upstream_revision=REVISION, emscripten="3.1.64")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("DOOM_BUILD: PASS", flush=True)


if __name__ == "__main__":
    main()
