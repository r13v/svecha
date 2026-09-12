#!/usr/bin/env python3
"""Verify metric dimensions and PBR values through Blender -> GLB -> Godot."""

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / ".tools/checks/pipeline.log"

BLENDER_SCRIPT = '''import bpy, sys
from pathlib import Path
target = Path(sys.argv[sys.argv.index("--") + 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.ops.mesh.primitive_cube_add(size=1)
obj = bpy.context.object
obj.name = 'PipelineBox'
obj.dimensions = (1.0, 2.0, 3.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
mat = bpy.data.materials.new('PipelineBrass')
shader = mat.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (0.8, 0.55, 0.12, 1.0)
shader.inputs['Metallic'].default_value = 0.7
shader.inputs['Roughness'].default_value = 0.4
obj.data.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=str(target / 'pipeline.blend'))
bpy.ops.export_scene.gltf(filepath=str(target / 'pipeline.glb'),
    export_format='GLB', use_selection=True, export_yup=True,
    export_cameras=False, export_lights=False, export_animations=False)
print('BLENDER_EXPORT_OK')
'''

GODOT_SCRIPT = '''extends SceneTree

func _initialize() -> void:
	call_deferred("_check")

func _check() -> void:
	var packed := load("res://pipeline.glb") as PackedScene
	if packed == null:
		push_error("GLB must import as a PackedScene")
		quit(1)
		return
	var model := packed.instantiate()
	root.add_child(model)
	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	if meshes.size() != 1:
		push_error("Expected exactly one exported mesh")
		quit(1)
		return
	var mesh := meshes[0] as MeshInstance3D
	var bounds: AABB = mesh.global_transform * mesh.get_aabb()
	if not bounds.size.is_equal_approx(Vector3(1.0, 3.0, 2.0)):
		push_error("Metric dimensions or Z-up to Y-up conversion changed: " + str(bounds.size))
		quit(1)
		return
	var material := mesh.get_active_material(0) as StandardMaterial3D
	if material == null or not is_equal_approx(material.metallic, 0.7) or not is_equal_approx(material.roughness, 0.4):
		push_error("PBR metallic/roughness did not survive export")
		quit(1)
		return
	print("PIPELINE_OK dimensions=", bounds.size, " metallic=", material.metallic, " roughness=", material.roughness)
	model.queue_free()
	quit(0)
'''


def run(args, expected=None):
    result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=120)
    with LOG.open("a") as log:
        log.write(result.stdout + "\n")
    if result.returncode or "ERROR:" in result.stdout or (expected and expected not in result.stdout):
        raise RuntimeError(f"Check failed; inspect {LOG}\n{result.stdout[-3000:]}")


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("")
    with tempfile.TemporaryDirectory(prefix="candle-pipeline-") as folder:
        target = Path(folder)
        (target / "export.py").write_text(BLENDER_SCRIPT)
        (target / "project.godot").write_text(
            '[application]\nconfig/name="Candle pipeline check"\n'
            '[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        (target / "check.gd").write_text(GODOT_SCRIPT)
        run([str(ROOT / "tools/blender"), "--background", "--factory-startup",
             "--python-exit-code", "1", "--python", str(target / "export.py"), "--", folder],
            "BLENDER_EXPORT_OK")
        # Keep the Blender source outside Godot's import scope after proving it saved.
        if not (target / "pipeline.blend").is_file() or not (target / "pipeline.glb").is_file():
            raise RuntimeError("Blender source or GLB missing")
        sources = target / "source"
        sources.mkdir()
        (sources / ".gdignore").touch()
        (target / "pipeline.blend").rename(sources / "pipeline.blend")
        run([str(ROOT / "tools/godot"), "--headless", "--path", folder, "--import"])
        run([str(ROOT / "tools/godot"), "--headless", "--path", folder,
             "--script", "res://check.gd"], "PIPELINE_OK")
    print(f"PASS: Blender -> GLB -> Godot; dimensions and PBR values preserved. Log: {LOG}")


if __name__ == "__main__":
    main()
