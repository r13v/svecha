"""Build the first candle/stand assets in an isolated Blender process.

Run: ./tools/blender --background --factory-startup --python-exit-code 1 \
     --python tools/build_candle_assets.py
Rebuilds only the three named assets and their studio previews.
"""

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
BLENDS = ROOT / "art/blender"
MODELS = ROOT / "game/assets/models"
PREVIEWS = ROOT / "docs/04_BLENDER_ENV/previews"
REPORTS = ROOT / "docs/04_BLENDER_ENV"
for path in (BLENDS, MODELS, PREVIEWS):
    path.mkdir(parents=True, exist_ok=True)


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj.empty_display_size = 0.012
    return obj


# CC0 source sets and their repeat dimensions in meters.
PBR_SETS = {
    "Walnut": ("wood_table_worn", (0.55, 0.55), 0.6),
    "WalnutBoards": ("wood_cabinet_worn_long", (1.0, 0.5), 0.55),
    "Plaster": ("white_plaster_02", (1.3, 1.3), 0.65),
    "WeatheredPlaster": ("worn_cracked_plaster", (1.8, 1.8), 0.4),
    "Limestone": ("old_sandstone_02", (1.8, 1.8), 0.7),
    "FloorStone": ("large_floor_tiles_02", (2.1, 2.7), 0.8),
    "RoofSlate": ("roof_slates_02", (3.0, 3.0), 0.7),
    "WoolSleeve": ("poly_wool_herringbone", (0.22, 0.22), 0.6),
    "GrassSoil": ("sparse_grass", (2.0, 2.0), 0.8),
}


def material(name, color, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if name == "FloorStone":
        mat["tile_m"] = (2.8, 3.2)
        for channel, socket in [("albedo", "Base Color"), ("normal", "Normal")]:
            node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = bpy.data.images.load(str(ROOT / "game/assets/textures/limestone" / ("floor_" + channel + ".png")), check_existing=True)
            output = node.outputs["Color"]
            if channel == "normal":
                node.image.colorspace_settings.name = "Non-Color"
                normal = mat.node_tree.nodes.new("ShaderNodeNormalMap")
                normal.inputs["Strength"].default_value = 0.55
                mat.node_tree.links.new(output, normal.inputs["Color"])
                output = normal.outputs["Normal"]
            mat.node_tree.links.new(output, shader.inputs[socket])
    elif name in PBR_SETS:
        slug, scale, normal_strength = PBR_SETS[name]
        mat["tile_m"] = scale
        folder = ROOT / "art/textures/pbr" / slug
        for channel, socket in [("Diffuse", "Base Color"), ("Rough", "Roughness"), ("nor_gl", "Normal")]:
            texture_path = folder / (channel + ".jpg")
            if not texture_path.exists(): texture_path = folder / (channel + ".png")
            if not texture_path.exists(): raise FileNotFoundError(texture_path)
            node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = bpy.data.images.load(str(texture_path), check_existing=True)
            if channel != "Diffuse": node.image.colorspace_settings.name = "Non-Color"
            output = node.outputs["Color"]
            if channel == "nor_gl":
                normal = mat.node_tree.nodes.new("ShaderNodeNormalMap")
                normal.inputs["Strength"].default_value = normal_strength
                mat.node_tree.links.new(output, normal.inputs["Color"])
                output = normal.outputs["Normal"]
            mat.node_tree.links.new(output, shader.inputs[socket])
    else:
        texture_path = ROOT / "game/assets/textures" / f"{name.lower()}_basecolor.png"
        if texture_path.exists():
            image_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            image_node.image = bpy.data.images.load(str(texture_path), check_existing=True)
            mat.node_tree.links.new(image_node.outputs["Color"], shader.inputs["Base Color"])
    return mat


def lathe(name, profile, mat, parent, segments=64, closed=False, wobble=0):
    """Revolve an authored radius/height profile; retain metric UV scale."""
    vertices = []
    for radius, height in profile:
        for j in range(segments):
            angle = math.tau * j / segments
            r = radius * (1 + wobble * math.sin(5 * angle) + wobble / 2 * math.cos(9 * angle))
            vertices.append((r * math.cos(angle), r * math.sin(angle), height))
    faces = []
    count = len(profile)
    for i in range(count if closed else count - 1):
        next_i = (i + 1) % count
        for j in range(segments):
            k = (j + 1) % segments
            faces.append((i * segments + j, i * segments + k,
                          next_i * segments + k, next_i * segments + j))
    if not closed:
        faces.extend([tuple(range(segments - 1, -1, -1)),
                      tuple((count - 1) * segments + j for j in range(segments))])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
        for loop_index in polygon.loop_indices:
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (math.atan2(vertex.y, vertex.x) / math.tau + 0.5, vertex.z)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    return obj


def begin(name):
    # This script runs in its own --factory-startup process, never the user's editor.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1
    return empty(name)


def studio(target, camera_distance, ortho_size):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.view_settings.exposure = -1.5
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("StudioWorld")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.15, 0.18, 0.22, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    bpy.ops.mesh.primitive_plane_add(size=200)
    floor = bpy.context.object
    floor.name = "StudioFloor"
    floor.location.z = -0.0001
    floor.data.materials.append(material("StudioStone", (0.13, 0.145, 0.16), 0, 0.7))
    for name, offset, power, size, color in [
        ("Key", (-1.4, -1.2, 1.8), 650, 1.6, (1.0, 0.88, 0.67)),
        ("Fill", (1.3, -0.6, 0.6), 350, 1.2, (0.70, 0.82, 1.0)),
        ("Rim", (0.2, 1.2, 1.4), 750, 1.2, (1.0, 0.92, 0.76)),
    ]:
        light = bpy.data.lights.new(name, "AREA")
        light.energy = power
        light.shape = "DISK"
        light.size = size
        light.color = color
        obj = bpy.data.objects.new(name, light)
        bpy.context.collection.objects.link(obj)
        obj.location = Vector(target) + Vector(offset)
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("StudioCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_size
    camera = bpy.data.objects.new("StudioCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = Vector(target) + Vector((camera_distance, -camera_distance * 1.8, camera_distance * 0.8))
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera


def merge_static_surfaces(root):
    """Keep attachment nodes, but draw stationary carving/leaves once per material."""
    groups = {}
    for obj in list(root.children_recursive):
        if obj.type not in {"MESH", "CURVE"}:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        obj = bpy.context.object
        key = tuple(mat.name for mat in obj.data.materials)
        groups.setdefault(key, []).append(obj)
    for materials, objects in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        if len(objects) > 1:
            bpy.ops.object.join()
        obj = bpy.context.object
        transform = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = transform
        obj.name = (materials[0] if materials else "Geometry") + "Surface"


def save_asset(slug, root, camera_target, camera_distance, ortho_size, render_preview=True):
    if slug in {"iconostasis", "icon_case", "church_shell", "church_vault", "church_roof",
                "window_bay", "candle_table", "candle_tray", "wall_bench", "side_table",
                "flower_vase", "chandelier", "hanging_lamp", "chancel_steps", "chancel_carpet",
                "wall_icon", "hanging_banner", "wall_sconce", "stone_facade", "entry_steps",
                "garden_wall", "entrance_lantern", "stone_approach"}:
        merge_static_surfaces(root)
    bpy.context.view_layer.update()
    objects = [root, *root.children_recursive]
    bpy.ops.object.select_all(action="DESELECT")
    points = []
    triangles = 0
    for obj in objects:
        obj.select_set(True)
        if obj.type in {"MESH", "CURVE"}:
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
            points.extend(obj.matrix_world @ vertex.co for vertex in mesh.vertices)
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
            evaluated.to_mesh_clear()
    bounds = [[min(v[axis] for v in points), max(v[axis] for v in points)] for axis in range(3)]
    if slug != "hand_grip":
        assert abs(bounds[2][0]) < 0.0001, "Asset base must stay on the floor/seat"
    assert triangles < 200000, "Inspect asset density before exporting more than 200k triangles"
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(MODELS / f"{slug}.glb"), export_format="GLB",
                             use_selection=True, export_yup=True, export_cameras=False,
                             export_lights=False, export_animations=False, export_extras=True, export_apply=True)
    studio(camera_target, camera_distance, ortho_size)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLENDS / f"{slug}.blend"))
    bpy.context.scene.render.filepath = str(PREVIEWS / f"{slug}_blender.png")
    if render_preview:
        bpy.ops.render.render(write_still=True)
    return {"asset": slug, "source": f"art/blender/{slug}.blend",
            "model": f"game/assets/models/{slug}.glb", "triangles": triangles,
            "blender_bounds_m": bounds, "nodes": [obj.name for obj in objects]}



def main():
    reports = []
    root = begin("Candle")
    root["wax_height_m"] = 0.25
    root["wax_diameter_m"] = 0.010
    wax = material("Beeswax", (0.72, 0.40, 0.065), 0, 0.42)
    charcoal = material("CharredWick", (0.018, 0.012, 0.008), 0, 0.94)
    body = lathe("Wax", [(0.0048, 0), (0.005, 0.0005), (0.005, 0.247),
                  (0.0047, 0.249), (0.0034, 0.25)], wax, root, segments=48)
    drips = empty("WaxDrips", body)
    for i, length in enumerate([0.017, 0.033, 0.010]):
        angle = i * 2.37
        drip = lathe("WaxTrail", [(0.00002, 0), (0.00085, 0.0012), (0.00058, 0.003),
                    (0.00045, length), (0.0002, length+0.004)], wax, drips, segments=16)
        drip.location = (math.cos(angle)*0.00475, math.sin(angle)*0.00475, 0.247-length)
    tip = empty("WickAnchor", root, (0, 0, 0.25))
    lathe("Wick", [(0.00038, 0), (0.00042, 0.002), (0.00030, 0.004)], charcoal, tip, segments=12)
    empty("FlameAnchor", tip, (0, 0, 0.003))
    reports.append(save_asset("candle", root, (0, 0, 0.128), 0.35, 0.29))

    root = begin("CandleRemnant")
    wax = material("Beeswax", (0.72, 0.40, 0.065), 0, 0.42)
    charcoal = material("CharredWick", (0.018, 0.012, 0.008), 0, 0.94)
    lathe("WaxResidue", [(0.0036, 0), (0.0038, 0.0004), (0.0032, 0.001),
                         (0.0022, 0.0013), (0.0015, 0.003), (0.00065, 0.0034)],
          wax, root, segments=32, wobble=0.035)
    lathe("WickRemnant", [(0.00035, 0.0032), (0.00030, 0.0045)], charcoal, root, segments=12)
    reports.append(save_asset("candle_remnant", root, (0, 0, 0.002), 0.04, 0.017))

    root = begin("CandleStand")
    root["socket_count"] = 19
    root["socket_bore_m"] = 0.011
    root["player_socket"] = "Seat00"
    brass = material("AgedBrass", (0.56, 0.34, 0.105), 0.94, 0.28)
    lathe("Pedestal", [
        (0.145, 0), (0.15, 0.006), (0.15, 0.016), (0.142, 0.024),
        (0.138, 0.03), (0.138, 0.043), (0.12, 0.05), (0.11, 0.063),
        (0.102, 0.08), (0.078, 0.10), (0.066, 0.117), (0.065, 0.127),
        (0.074, 0.133), (0.074, 0.142), (0.059, 0.15), (0.043, 0.17),
        (0.035, 0.21), (0.032, 0.235), (0.043, 0.242), (0.043, 0.255),
        (0.034, 0.264), (0.033, 0.305), (0.052, 0.322), (0.062, 0.343),
        (0.064, 0.363), (0.055, 0.382), (0.038, 0.398), (0.031, 0.414),
        (0.027, 0.45), (0.022, 0.72), (0.032, 0.75), (0.041, 0.77),
        (0.047, 0.785), (0.047, 0.799), (0.035, 0.817), (0.039, 0.833),
        (0.049, 0.839), (0.049, 0.85), (0.038, 0.86), (0.035, 0.899),
    ], brass, root)
    lathe("Tray", [(0.034, 0.835), (0.07, 0.844), (0.13, 0.873),
                   (0.21, 0.919), (0.271, 0.956), (0.28, 0.962),
                   (0.28, 0.991), (0.276, 0.995), (0.271, 0.991),
                   (0.271, 0.974), (0.265, 0.970), (0.0001, 0.970)], brass, root)
    socket_profile = [(0.015, 0), (0.016, 0.003), (0.016, 0.007), (0.012, 0.012),
                      (0.012, 0.032), (0.018, 0.039), (0.018, 0.045),
                      (0.0055, 0.045), (0.0055, 0.004), (0.0001, 0.004), (0.0001, 0)]
    seats = []
    for count, radius in [(12, 0.228), (6, 0.132), (1, 0.0)]:
        for i in range(count):
            angle = -math.pi / 2 + math.tau * i / count
            seats.append((radius * math.cos(angle), radius * math.sin(angle), 0.974))
    socket = lathe("Socket00", socket_profile, brass, root, segments=32, closed=True)
    for index, position in enumerate(seats):
        obj = socket if index == 0 else bpy.data.objects.new(f"Socket{index:02}", socket.data)
        if index:
            bpy.context.collection.objects.link(obj)
            obj.parent = root
        obj.location = (position[0], position[1], 0.970)
        empty(f"Seat{index:02}", root, position)
    assert len(seats) == 19 and len(set(seats)) == 19
    assert 0.010 < root["socket_bore_m"], "A candle must physically fit inside the socket"
    # Wider tray and sturdier turned foot, while the bores retain their actual candle fit.
    for obj in root.children:
        if obj.name in {"Pedestal", "Tray"}:
            for vertex in obj.data.vertices:
                vertex.co.x *= 0.68 / 0.56
                vertex.co.y *= 0.68 / 0.56
                vertex.co.z *= 1.135
        elif obj.name.startswith(("Seat", "Socket")):
            obj.location.x *= 0.68 / 0.56
            obj.location.y *= 0.68 / 0.56
            obj.location.z = 0.970 * 1.135 + (0.004 if obj.name.startswith("Seat") else 0)
    root["tray_diameter_m"] = 0.68
    root["socket_floor_m"] = 0.970 * 1.135 + 0.004
    reports.append(save_asset("candle_stand", root, (0, 0, 0.52), 1.0, 1.22))
    (REPORTS / "asset_build.json").write_text(json.dumps({"blender_version": bpy.app.version_string,
        "status": "exported", "assets": reports}, indent=2) + "\n")
    print("CANDLE_ASSETS_EXPORTED", len(reports))


if __name__ == "__main__":
    main()
