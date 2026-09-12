"""Build the remaining authored church kit. Uses only Blender's bundled libraries."""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_candle_assets as base


def textures():
    """Original repeatable material swatches, not edits of reference artwork."""
    folder = base.ROOT / "game/assets/textures"
    folder.mkdir(exist_ok=True)
    y, x = np.mgrid[0:512, 0:512] / 512.0
    noise = np.random.default_rng(52).random((512, 512))
    grain = np.sin(x * math.tau * 67 + 3 * np.sin(y * math.tau * 3) + np.sin(y * math.tau * 11))
    fields = {
        "walnut": ((0.21, 0.115, 0.058), 0.75 + grain * 0.14 + noise * 0.16),
        "plaster": ((0.73, 0.66, 0.53), 0.97 + noise * 0.03),
        "limestone": ((0.49, 0.44, 0.35), 0.96 + noise * 0.04),
        "agedbrass": ((0.69, 0.47, 0.19), 0.90 + noise * 0.08 + np.sin(x * 51) * np.cos(y * 39) * 0.07),
        "roofslate": ((0.13, 0.18, 0.19), 0.80 + noise * 0.25),
    }
    for name, (color, field) in fields.items():
        pixels = np.ones((512, 512, 4), dtype=np.float32)
        pixels[:, :, :3] = np.clip(field[:, :, None] * np.array(color), 0, 1)
        image = bpy.data.images.new(name, 512, 512)
        image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw = str(folder / f"{name}_basecolor.png")
        image.file_format = "PNG"
        image.save()


def palette():
    return {
        "wood": base.material("Walnut", (0.15, 0.075, 0.032), 0, 0.62),
        "stone": base.material("Limestone", (0.49, 0.44, 0.35), 0, 0.84),
        "plaster": base.material("Plaster", (0.73, 0.66, 0.53), 0, 0.92),
        "brass": base.material("AgedBrass", (0.56, 0.34, 0.105), 0.94, 0.28),
        "iron": base.material("ForgedIron", (0.035, 0.032, 0.027), 0.8, 0.55),
        "slate": base.material("RoofSlate", (0.13, 0.18, 0.19), 0.2, 0.8),
    }


def uv_box(mesh):
    uv = mesh.uv_layers.active or mesh.uv_layers.new()
    for face in mesh.polygons:
        axis = max(range(3), key=lambda a: abs(face.normal[a]))
        axes = [(1, 2), (0, 2), (0, 1)][axis]
        for index in face.loop_indices:
            v = mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv = (v[axes[0]], v[axes[1]])


def box(name, size, location, mat, parent, bevel=0.006):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.parent = parent
    obj.data.materials.append(mat)
    uv_box(obj.data)
    if bevel:
        mod = obj.modifiers.new("EdgeWear", "BEVEL")
        mod.width = min(bevel, min(size) / 5)
        mod.segments = 2
        obj.modifiers.new("CornerNormals", "WEIGHTED_NORMAL")
    return obj


def extrude(name, outline, depth, mat, parent):
    """Extrude an X/Z outline along Y; the visible front faces Blender -Y."""
    n = len(outline)
    vertices = [(x, y, z) for y in [-depth / 2, depth / 2] for x, z in outline]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(mat)
    uv_box(mesh)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    return obj


def arch(name, radius, thickness, spring, depth, mat, parent, steps=32):
    outline = [(math.cos(t) * (radius + thickness), spring + math.sin(t) * (radius + thickness))
               for t in np.linspace(0, math.pi, steps + 1)]
    outline += [(math.cos(t) * radius, spring + math.sin(t) * radius)
                for t in np.linspace(math.pi, 0, steps + 1)]
    return extrude(name, outline, depth, mat, parent)


def ring(name, center, radius, minor, mat, parent):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=minor,
                                   major_segments=24, minor_segments=8)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler.x = math.pi / 2
    obj.location = center
    obj.parent = parent
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def picture(name, filename, width, height, location, parent):
    mat = base.material(name, (1, 1, 1), 0, 0.75)
    nodes = mat.node_tree.nodes
    image = nodes.new("ShaderNodeTexImage")
    image.image = bpy.data.images.load(str(base.ROOT / "game/assets/icons" / filename), check_existing=True)
    mat.node_tree.links.new(image.outputs["Color"], nodes.get("Principled BSDF").inputs["Base Color"])
    ratio = image.image.size[0] / image.image.size[1]
    width = min(width, height * ratio)
    height = min(height, width / ratio)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-width / 2, 0, 0), (width / 2, 0, 0), (width / 2, 0, height), (-width / 2, 0, height)], [], [(0, 1, 2, 3)])
    mesh.materials.append(mat)
    layer = mesh.uv_layers.new()
    for i, uv in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        layer.data[i].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.parent = parent
    return obj


def frame(name, width, height, location, p, parent):
    root = base.empty(name, parent, location)
    for x in [-width / 2 - 0.035, width / 2 + 0.035]:
        box("FramePost", (0.07, 0.10, height + 0.12), (x, 0, height / 2), p["wood"], root)
    for z in [-0.025, height + 0.025]:
        box("FrameRail", (width + 0.12, 0.10, 0.05), (0, 0, z), p["wood"], root)
    for x in [-width / 2, width / 2]:
        box("GiltEdge", (0.012, 0.012, height), (x, -0.055, height / 2), p["brass"], root, 0.002)
    return root


def door():
    root = base.begin("ChurchDoor"); p = palette()
    for x in [-0.775, 0.775]:
        box("Jamb", (0.15, 0.22, 2.0), (x, 0, 1.0), p["wood"], root)
    arch("ArchedFrame", 0.70, 0.15, 2.0, 0.22, p["wood"], root)
    for side, label in [(-1, "Left"), (1, "Right")]:
        hinge = base.empty(f"{label}Hinge", root, (side * 0.70, 0, 0))
        world_outline = [(0, 0), (0.694, 0), (0.694, 2.0)]
        world_outline += [(0.694 * math.cos(t), 2 + 0.694 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 18)]
        outline = [(side * (x - 0.70), z) for x, z in world_outline]
        if side < 0:
            outline.reverse()
        extrude(f"{label}Leaf", outline, 0.07, p["wood"], hinge)
        for z in [0.40, 1.10, 1.76]:
            box("InsetPanel", (0.53, 0.032, 0.51), (-side * 0.35, -0.045, z), p["wood"], hinge, 0.012)
        for z in [0.72, 1.45, 1.98]:
            box("CrossRail", (0.66, 0.05, 0.045), (-side * 0.35, -0.058, z), p["wood"], hinge)
        handle = base.empty(f"{label}Handle", hinge, (-side * 0.59, -0.083, 1.02))
        box("HandlePlate", (0.075, 0.018, 0.23), (0, 0, 0), p["iron"], handle)
        ring("RingPull", (0, -0.028, -0.02), 0.039, 0.007, p["iron"], handle)
        for z in [0.38, 1.75]:
            pin = base.lathe("HingePin", [(0.012, 0), (0.012, 0.17)], p["iron"], hinge, 16)
            pin.location = (0, 0, z)
    return root


def table():
    root = base.begin("CandleTable"); p = palette()
    box("Top", (0.95, 0.5, 0.055), (0, 0, 0.825), p["wood"], root, 0.012)
    for x in [-0.39, 0.39]:
        for y in [-0.18, 0.18]:
            box("Leg", (0.065, 0.065, 0.8), (x, y, 0.4), p["wood"], root)
        box("Stretcher", (0.06, 0.4, 0.055), (x, 0, 0.17), p["wood"], root)
    box("CrossStretcher", (0.8, 0.05, 0.065), (0, 0, 0.17), p["wood"], root)
    for y in [-0.205, 0.205]:
        box("Apron", (0.82, 0.035, 0.13), (0, y, 0.73), p["wood"], root)
    base.empty("TrayAnchor", root, (0, 0, 0.8525))
    return root


def tray():
    root = base.begin("CandleTray"); p = palette()
    box("Bottom", (0.39, 0.29, 0.015), (0, 0, 0.0075), p["wood"], root)
    for x in [-0.2, 0.2]:
        box("Side", (0.02, 0.32, 0.055), (x, 0, 0.0275), p["wood"], root)
    for y in [-0.15, 0.15]:
        box("End", (0.39, 0.02, 0.055), (0, y, 0.0275), p["wood"], root)
    base.empty("PickupAnchor", root, (0, 0, 0.025))
    return root


def window_bay():
    root = base.begin("WindowBay"); p = palette()
    # A 3 m wide wall bay with a real arched opening, not a bright decal.
    for x in [-0.925, 0.925]:
        box("WallSide", (1.15, 0.38, 3.4), (x, 0, 1.7), p["plaster"], root)
    box("WallBelow", (0.70, 0.38, 1.55), (0, 0, 0.775), p["plaster"], root)
    box("WallAbove", (0.70, 0.38, 0.65), (0, 0, 3.075), p["plaster"], root)
    arch("OpeningArch", 0.35, 0.20, 2.40, 0.38, p["plaster"], root)
    box("WindowSill", (0.98, 0.61, 0.10), (0, -0.015, 1.55), p["stone"], root)
    for x in [-0.345, 0.345]:
        box("WindowFrame", (0.035, 0.065, 0.86), (x, 0, 1.99), p["wood"], root)
    arch("WindowFrameArch", 0.315, 0.035, 2.40, 0.065, p["wood"], root)
    box("Mullion", (0.025, 0.03, 1.12), (0, 0, 2.12), p["wood"], root)
    box("MullionHorizontal", (0.69, 0.03, 0.025), (0, 0, 2.12), p["wood"], root)
    return root


def shell():
    root = base.begin("ChurchShell"); p = palette()
    box("Floor", (7.4, 11.4, 0.16), (0, 0, 0.08), p["stone"], root, 0.005)
    # In Blender the entrance is -Y; in Godot it becomes +Z.
    for x in [-2.2, 2.2]:
        box("EntrySide", (2.6, 0.38, 3.4), (x, -5.5, 1.86), p["plaster"], root)
    box("EntryTop", (1.8, 0.38, 0.65), (0, -5.5, 3.235), p["plaster"], root)
    entry_arch = arch("EntryArch", 0.85, 0.25, 2.16, 0.38, p["stone"], root)
    entry_arch.location.y = -5.54
    for x in [-0.975, 0.975]:
        box("EntryStoneJamb", (0.25, 0.46, 2.0), (x, -5.52, 1.16), p["stone"], root)
    box("RearWall", (7.4, 0.38, 3.4), (0, 5.5, 1.86), p["plaster"], root)
    for x in [-3.5, 3.5]:
        for y in [-5, 5]:
            box("SideEnd", (0.38, 1, 3.4), (x, y, 1.86), p["plaster"], root)
        box("Cornice", (0.49, 11.3, 0.12), (x, 0, 3.53), p["stone"], root)
        box("Plinth", (0.48, 11.3, 0.17), (x, 0, 0.245), p["stone"], root)
    for i in range(8):
        for j in range(12):
            # Deliberate sparse seams: a compact authored floor, not scatter generation.
            box("Flagstone", (0.9, 0.92, 0.012), (-3.18 + i * 0.91, -5.07 + j * 0.93, 0.166), p["stone"], root, 0.003)
    for y in [-5.5, 5.5]:
        outline = [(-3.5, 3.55), (3.5, 3.55)]
        outline += [(3.5 * math.cos(a), 3.56 + 1.7 * math.sin(a) ** 2) for a in np.linspace(0, math.pi, 49)]
        gable = extrude("VaultEndWall", outline, 0.38, p["plaster"], root)
        gable.location.y = y
    return root


def vault():
    root = base.begin("ChurchVault"); p = palette()
    # Elliptical vault, split from walls for manual placement and roof access.
    vertices = []
    for y in [-5.6, 5.6]:
        for angle in np.linspace(0, math.pi, 49):
            vertices.append((3.5 * math.cos(angle), y, 1.7 * math.sin(angle) ** 2))
    faces = [(i + 1, i + 50, i + 49, i) for i in range(48)]
    mesh = bpy.data.meshes.new("VaultInterior")
    mesh.from_pydata(vertices, [], faces); mesh.update(); mesh.materials.append(p["plaster"])
    uv_box(mesh)
    obj = bpy.data.objects.new("VaultInterior", mesh); bpy.context.collection.objects.link(obj); obj.parent = root
    for poly in mesh.polygons: poly.use_smooth = True
    # The vault's interior faces point inward; a roof is a separate asset.
    return root


def roof():
    root = base.begin("ChurchRoof"); p = palette()
    roof_obj = extrude("RoofBody", [(-3.85, 0), (3.85, 0), (0, 2.65)], 11.9, p["slate"], root)
    # Keep the slopes and gables, remove the flat underside above the vault.
    import bmesh
    bm = bmesh.new(); bm.from_mesh(roof_obj.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[2]], context="FACES_ONLY")
    bm.to_mesh(roof_obj.data); bm.free()
    roof_obj.data.materials.append(p["plaster"])
    for face in roof_obj.data.polygons:
        if abs(face.normal.y) > 0.9: face.material_index = 1
    for x in [-3.82, 3.82]:
        box("Eave", (0.10, 12, 0.10), (x, 0, 0.05), p["wood"], root)
    dome = base.empty("Cupola", root, (0, -4.0, 2.4))
    base.lathe("Drum", [(0.45, 0), (0.45, 1.05), (0.48, 1.10)], p["plaster"], dome)
    base.lathe("CopperDome", [(0.48, 1.07), (0.59, 1.18), (0.62, 1.36), (0.52, 1.60), (0.32, 1.78), (0.07, 2.04), (0.03, 2.12)], p["brass"], dome)
    box("CrossUpright", (0.035, 0.035, 0.62), (0, 0, 2.39), p["brass"], dome, 0.003)
    for z, width in [(2.58, 0.20), (2.43, 0.34), (2.24, 0.18)]:
        bar = box("CrossBar", (width, 0.035, 0.028), (0, 0, z), p["brass"], dome, 0.003)
        if z < 2.3: bar.rotation_euler.y = -0.22
    return root


def icon_case():
    root = base.begin("IconCase"); p = palette()
    box("Base", (0.94, 0.29, 0.10), (0, 0, 0.05), p["wood"], root)
    box("Cabinet", (0.82, 0.22, 0.91), (0, 0, 0.55), p["wood"], root)
    box("Back", (0.88, 0.16, 1.45), (0, 0, 1.65), p["wood"], root)
    holder = frame("IconFrame", 0.66, 1.0, (0, -0.11, 1.04), p, root)
    picture("TheotokosIcon", "theotokos_vladimir.jpg", 0.66, 1.0, (0, -0.056, 0), holder)
    arch("Crown", 0.45, 0.09, 2.20, 0.20, p["wood"], root)
    box("Cornice", (1.03, 0.30, 0.06), (0, 0, 2.17), p["wood"], root)
    return root


def iconostasis():
    root = base.begin("Iconostasis"); p = palette()
    box("Base", (6.4, 0.25, 0.16), (0, 0, 0.08), p["wood"], root)
    for x in [-2.9, -1.8, -0.65, 0.65, 1.8, 2.9]:
        box("Post", (0.15, 0.32, 2.8), (x, 0, 1.4), p["wood"], root)
    for z in [0.78, 2.3, 2.8]:
        box("Rail", (6.4, 0.28, 0.10), (0, 0, z), p["wood"], root)
    for x in [-2.35, -1.2, 1.2, 2.35]:
        box("LowerPanel", (1.02, 0.10, 0.61), (x, 0, 0.43), p["wood"], root)
        holder = frame("IconPanel", 0.86, 1.44, (x, -0.10, 0.84), p, root)
        filename = {-2.35: "nicholas_sinai.jpg", -1.2: "theotokos_vladimir.jpg", 1.2: "christ_sinai.jpg", 2.35: "john_baptist.jpg"}[x]
        picture("Icon", filename, 0.86, 1.44, (0, -0.056, 0), holder)
    box("ClosedRoyalDoors", (1.16, 0.15, 2.42), (0, 0, 1.21), p["wood"], root)
    arch("RoyalDoorCrown", 0.61, 0.10, 2.10, 0.25, p["wood"], root)
    for x in [-0.29, 0.29]:
        box("DoorCross", (0.025, 0.025, 0.32), (x, -0.10, 1.47), p["brass"], root)
        box("DoorCrossbar", (0.17, 0.025, 0.025), (x, -0.10, 1.53), p["brass"], root)
    box("TopCross", (0.05, 0.05, 0.62), (0, 0, 3.06), p["wood"], root)
    box("TopCrossbar", (0.35, 0.05, 0.05), (0, 0, 3.15), p["wood"], root)
    return root


def hand():
    root = base.begin("HandGrip")
    skin = base.material("Skin", (0.50, 0.28, 0.16), 0, 0.76)
    cloth = base.material("WoolSleeve", (0.09, 0.075, 0.045), 0, 0.97)
    parts = []
    def ellipsoid(name, location, scale):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, location=location)
        obj = bpy.context.object; obj.name = name; obj.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        parts.append(obj)
    ellipsoid("Palm", (0, 0, 0.225), (0.037, 0.023, 0.051))
    ellipsoid("Wrist", (0, 0, 0.172), (0.025, 0.020, 0.041))
    for x, length in [(-0.023, 0.030), (-0.008, 0.039), (0.008, 0.036), (0.023, 0.027)]:
        for y, z, scale in [(0, 0.262, (0.009, 0.015, 0.013)), (-0.018, 0.267, (0.009, 0.021, 0.012)), (-0.039, 0.244, (0.009, 0.014, 0.023))]:
            ellipsoid("Finger", (x, y, z), scale)
    ellipsoid("ThumbBase", (-0.035, -0.015, 0.22), (0.022, 0.018, 0.025))
    ellipsoid("Thumb", (-0.025, -0.047, 0.235), (0.025, 0.012, 0.012))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts: obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join(); obj = bpy.context.object; obj.name = "HandSkin"
    obj.data.remesh_voxel_size = 0.0025
    bpy.ops.object.voxel_remesh()
    smooth = obj.modifiers.new("SkinSmooth", "SMOOTH"); smooth.factor = 1.1; smooth.iterations = 5
    mod = obj.modifiers.new("Simplify", "DECIMATE"); mod.ratio = 0.45
    obj.parent = root; obj.data.materials.append(skin)
    for poly in obj.data.polygons: poly.use_smooth = True
    base.lathe("Sleeve", [(0.036, 0), (0.034, 0.13), (0.029, 0.17)], cloth, root, segments=24)
    base.empty("GripAnchor", root, (-0.017, -0.027, 0.247))
    return root



def main():
    textures()
    reports = []
    for slug, builder, target, distance, size in [
        ("church_door", door, (0, 0, 1.4), 2.5, 3.2),
        ("candle_table", table, (0, 0, 0.43), 1.0, 1.25),
        ("candle_tray", tray, (0, 0, 0.04), 0.4, 0.55),
        ("window_bay", window_bay, (0, 0, 1.7), 4, 4.0),
        ("church_shell", shell, (0, 0, 1.8), 10, 15),
        ("church_vault", vault, (0, 0, 0.8), 10, 13),
        ("church_roof", roof, (0, 0, 1.5), 10, 14),
        ("icon_case", icon_case, (0, 0, 1.25), 2, 3.0),
        ("iconostasis", iconostasis, (0, 0, 1.5), 5, 7.2),
        ("hand_grip", hand, (0, 0, 0.15), 0.4, 0.36),
    ]:
        root = builder()
        reports.append(base.save_asset(slug, root, target, distance, size, render_preview=slug in {"church_door", "candle_table", "icon_case", "hand_grip"}))
    (base.REPORTS / "church_asset_build.json").write_text(json.dumps({"blender_version": bpy.app.version_string, "assets": reports}, indent=2) + "\n")
    base.main()  # Re-export the first set with the same original patina texture.
    print("CHURCH_ASSETS_EXPORTED", len(reports))


if __name__ == "__main__":
    main()
