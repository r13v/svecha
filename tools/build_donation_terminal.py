"""Оригинальный настенный терминал; отдельный процесс Blender."""
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_candle_assets as base
import build_church_assets as kit


def main():
    root = base.begin("DonationTerminal")
    shell = base.material("TerminalIvory", (.52, .50, .43), 0, .60)
    bezel = base.material("TerminalGraphite", (.026, .029, .027), .12, .52)
    metal = base.material("TerminalMount", (.11, .12, .11), .65, .55)
    # Front is Blender -Y, exported to Godot +Z. Origin is the lowest point of the short cable.
    kit.box("WallMount", (.24, .055, .20), (0, .050, 0), metal, root, .009)
    kit.box("Housing", (.40, .073, .335), (0, 0, 0), shell, root, .013)
    kit.box("GlassBezel", (.355, .006, .276), (0, -.038, .009), bezel, root, .006)
    base.empty("ScreenAnchor", root, (0, -.042, .009))
    for x in [-.176, .176]:
        kit.box("ServiceScrew", (.006, .002, .006), (x, -.037, -.143), metal, root, .002)
    for x in [-.026, -.013, 0, .013, .026]:
        kit.box("SpeakerSlot", (.006, .002, .003), (x, -.037, -.146), bezel, root, .001)
    # A short visible cable enters the wall, without an unsupported hanging prop.
    kit.box("Cable", (.008, .012, .13), (.125, .035, -.205), bezel, root, .003)
    for child in root.children:
        child.location.z += .27
    base.merge_static_surfaces(root)
    report = base.save_asset("donation_terminal", root, (0, 0, .22), 1, .65, render_preview=False)
    print(report)


if __name__ == "__main__":
    main()
