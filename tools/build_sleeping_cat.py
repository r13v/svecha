"""Создать кота-смотрителя в отдельном процессе Blender.

./tools/blender --background --factory-startup --python-exit-code 1 \
    --python tools/build_sleeping_cat.py
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_candle_assets as base
import build_church_assets as kit


def ellipsoid(name, at, size, mat, parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32)
    obj = bpy.context.object
    obj.name = name
    obj.location = at
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent = parent
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def join_meshes(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    return obj


def paint_fur(obj, region):
    # Цвета вершин экспортируются в GLB: Blender-only процедурных шейдеров нет.
    colors = obj.data.color_attributes.new(name="FurColor", type="FLOAT_COLOR", domain="POINT")
    for vertex, color in zip(obj.data.vertices, colors.data):
        x, y, z = obj.matrix_world @ vertex.co
        if region == "head":
            phase = (x + .135) * 190 + 2.0 * math.sin(z * 53) + y * 35
        elif region == "tail":
            phase = math.atan2(y + .015, x - .07) * 14
        else:
            phase = x * 130 + 2.8 * math.sin(y * 24 + z * 16) + z * 30
        stripe = max(0.0, (math.cos(phase) - .28) / .72) ** 0.65
        grain = math.sin(x * 1900 + y * 2310) * math.sin(z * 2410 - x * 930) * .025
        belly = max(0.0, min(1.0, (.07 - z) / .06)) if region == "body" else 0.0
        light = (.34, .25, .16)
        dark = (.085, .059, .038)
        color.color = tuple((a * (1 - stripe * .78) + b * stripe * .78) * (1 + grain) + belly * .11 for a, b in zip(light, dark)) + (1,)


def ear(name, side, fur, pink, root):
    x = -.135 + side * .045
    # Rounded triangular ear, with a thick fur rim and a recessed inner surface.
    verts = [(x - .026, -.071, .183), (x + .025, -.071, .183),
             (x + side * .013, -.031, .260), (x, -.007, .184),
             (x, -.047, .210)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 0, 4), (0, 3, 1), (1, 3, 2), (2, 3, 0)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(fur)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = root
    bevel = obj.modifiers.new("SoftEarEdges", "BEVEL")
    bevel.width = .005
    bevel.segments = 3
    for face in mesh.polygons:
        face.use_smooth = True
    inner_verts = [(x - .015, -.072, .190), (x + .014, -.072, .190),
                   (x + side * .010, -.039, .243), (x, -.059, .211)]
    inner = bpy.data.meshes.new(name + "Inner")
    inner.from_pydata(inner_verts, [], [(0, 1, 3), (1, 2, 3), (2, 0, 3)])
    inner.materials.append(pink)
    patch = bpy.data.objects.new(name + "Inner", inner)
    bpy.context.collection.objects.link(patch)
    patch.parent = root
    return [obj, patch]


def eye(root, dark, amber, pupil):
    # All surfaces share one pivot; Godot scales its vertical opening smoothly.
    center = Vector((-.106, -.123, .165))
    verts = [(0, -.002, 0)]
    for i in range(48):
        a = i * math.tau / 48
        x = math.cos(a) * .017
        verts.append((x, .006 * (x / .017) ** 2, math.sin(a) * .0075 * abs(math.sin(a)) ** .3))
    mesh = bpy.data.meshes.new("WatchfulEye")
    mesh.from_pydata(verts, [], [(0, i + 1, (i + 1) % 48 + 1) for i in range(48)])
    mesh.materials.append(dark)
    border = bpy.data.objects.new("WatchfulEye", mesh)
    bpy.context.collection.objects.link(border)
    border.parent = root
    border.location = center
    iris = ellipsoid("AmberIris", center + Vector((0, -.0015, 0)), (.0067, .002, .0065), amber, root)
    slit = ellipsoid("Pupil", center + Vector((0, -.0034, 0)), (.0018, .0008, .0058), pupil, root)
    result = join_meshes([border, iris, slit], "WatchfulEye")
    return result


def build():
    root = base.begin("SleepingCat")
    fur = base.material("CatTabbyFur", (1, 1, 1), 0, .94)
    color_node = fur.node_tree.nodes.new("ShaderNodeVertexColor")
    color_node.layer_name = "FurColor"
    fur.node_tree.links.new(color_node.outputs["Color"], fur.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    plain = base.material("CatWarmFur", (.28, .20, .13), 0, .94)
    cream = base.material("CatCreamFur", (.65, .58, .45), 0, .96)
    pink = base.material("CatEarSkin", (.27, .12, .10), 0, .88)
    nose_mat = base.material("CatNose", (.17, .075, .057), 0, .62)
    dark = base.material("CatEyelid", (.028, .020, .015), 0, .85)
    amber = base.material("CatAmberEye", (.42, .31, .095), 0, .32)
    pupil = base.material("CatPupil", (.008, .010, .006), 0, .24)
    whisker_mat = base.material("CatWhisker", (.47, .42, .32), 0, .85)

    body = join_meshes([
        ellipsoid("Ribcage", (.022, .025, .105), (.18, .112, .103), fur, root),
        ellipsoid("Haunch", (.125, .026, .10), (.105, .105, .098), fur, root),
        ellipsoid("Shoulder", (-.090, -.005, .098), (.10, .10, .096), fur, root),
        ellipsoid("TuckedForeleg", (-.166, -.050, .047), (.038, .070, .044), fur, root),
        ellipsoid("TuckedForeleg", (-.083, -.056, .046), (.035, .065, .042), fur, root),
    ], "Body")
    remesh = body.modifiers.new("JoinedAnatomy", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = .004
    remesh.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth = body.modifiers.new("SoftContours", "SMOOTH")
    smooth.factor = 1.5
    smooth.iterations = 5
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    bpy.context.view_layer.update()
    paint_fur(body, "body")

    head = ellipsoid("Head", (-.135, -.067, .145), (.072, .060, .061), fur, root)
    bpy.context.view_layer.update()
    paint_fur(head, "head")
    details = []
    for side in [-1, 1]:
        details += ear("EarLeft" if side < 0 else "EarRight", side, plain, pink, root)
        details.append(ellipsoid("Muzzle", (-.135 + side * .016, -.123, .131), (.025, .020, .017), cream, root))
        paw_x = -.128 + side * .045
        details.append(ellipsoid("FrontPaw", (paw_x, -.105, .021), (.037, .056, .021), cream, root))
        for offset in [-.009, .009]:
            details.append(kit.trim_curve("ToeCrease", [(paw_x + offset, -.159, .018), (paw_x + offset, -.155, .027), (paw_x + offset, -.147, .031)], .00065, plain, root))
        for i in range(3):
            points = []
            for step in range(12):
                t = step / 11
                points.append((-.135 + side * (.024 + .067 * t), -.139 - .010 * t + .023 * t * t, .127 + (i - 1) * .009 + (i - 1) * .012 * t + .005 * t * t))
            details.append(kit.trim_curve("Whisker", points, .00035, whisker_mat, root))
    details.append(ellipsoid("Nose", (-.135, -.145, .145), (.009, .0045, .0055), nose_mat, root))
    for side in [-1, 1]:
        details.append(kit.trim_curve("Mouth", [(-.135, -.146, .139), (-.135, -.145, .133), (-.135 + side * .010, -.143, .129)], .00065, dark, root))
    points = [(-.164 + .017 * math.cos(i * math.pi / 24), -.123 + .006 * math.cos(i * math.pi / 24) ** 2, .165 - .0025 * math.sin(i * math.pi / 24)) for i in range(25)]
    details.append(kit.trim_curve("SleepingEye", points, .0011, dark, root))
    join_meshes(details, "FaceAndPaws")
    lid_points = [(x + .058, y - .003, z) for x, y, z in points]
    lid = kit.trim_curve("RestingEyelid", lid_points, .0011, dark, root)
    bpy.ops.object.select_all(action="DESELECT")
    lid.select_set(True)
    bpy.context.view_layer.objects.active = lid
    bpy.ops.object.convert(target="MESH")

    # Tail curls around the flank and rests in front of the tucked paws.
    verts, faces = [], []
    for i in range(81):
        t = i / 80
        a = .6 - t * 3.6
        c = Vector((.060 + .184 * math.cos(a), -.004 + .145 * math.sin(a), .030))
        radius = .025 * (1 - .8 * t ** 6)
        normal = Vector((math.cos(a), math.sin(a), 0))
        for j in range(16):
            b = j * math.tau / 16
            verts.append(c + radius * (normal * math.cos(b) + Vector((0, 0, math.sin(b)))))
        if i:
            for j in range(16):
                k = i * 16 + j
                n = i * 16 + (j + 1) % 16
                faces.append((k - 16, n - 16, n, k))
    faces += [tuple(reversed(range(16))), tuple(range(80 * 16, 81 * 16))]
    mesh = bpy.data.meshes.new("CurledTail")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(fur)
    tail = bpy.data.objects.new("CurledTail", mesh)
    bpy.context.collection.objects.link(tail)
    tail.parent = root
    for face in mesh.polygons:
        face.use_smooth = True
    bpy.context.view_layer.update()
    paint_fur(tail, "tail")
    eye(root, dark, amber, pupil)
    return root


if __name__ == "__main__":
    report = base.save_asset("sleeping_cat", build(), (0, 0, .12), .65, .62, render_preview=False)
    # Studio preview records the same closed-eye pose as the game.
    bpy.data.objects["WatchfulEye"].scale.z = .025
    bpy.data.objects["WatchfulEye"].hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=str(base.BLENDS / "sleeping_cat.blend"))
    bpy.ops.render.render(write_still=True)
    (base.REPORTS / "fidelity/cat_build.json").write_text(json.dumps(report, indent=2) + "\n")
    print("SLEEPING_CAT_READY", report["triangles"], flush=True)
