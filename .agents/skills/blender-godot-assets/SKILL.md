---
name: blender-godot-assets
description: Create, inspect, and export Blender assets for this Godot game. Use for Blender Python or MCP modeling, pivots, PBR materials, GLB export, and verifying imported scale and materials in Godot.
---

# Blender assets for «Свеча»

Read `docs/04_BLENDER_ENV/ASSET_PIPELINE_RU.md` for the asset contract and `docs/07_PRODUCTION/TOOLING_RU.md` for commands. Current verified applications: Blender 5.2.1 LTS and Godot 4.7.2. Check installed APIs before using version-sensitive operators.

## Choose the execution path

- Use the project Blender MCP for inspecting and iterating on an open scene: `get_scene_info`, `get_object_info`, `get_viewport_screenshot`, `execute_blender_code`. Discover the actual tool schema first; do not substitute tool names from another Blender server.
- Use `./tools/blender --background <file.blend> --python <script.py>` for repeatable exports or work that exceeds an interactive tool timeout. A headless process cannot host this MCP addon's GUI event loop.
- If tools are not connected, run the documented connection check once. Native Blender CLI remains available; do not pretend a command-line check proves the MCP tools loaded into the current task.

## Work on the requested asset

Inspect scene contents, active file, dimensions, collections, and materials before editing. Operate on named target objects. The project launcher opens a separate scene; preserve unrelated user work. Save intended source files under `art/blender/` and exported models under `game/assets/models/` when those assets are created.

Use meters, unit scale 1.0. Preserve the door hinge pivot and separate movable parts. Prefer direct `bpy.data` access; use operators with the required selection/mode/context. Measure evaluated geometry after modifiers rather than counting only the original mesh.

## Export contract

- GLB, selected asset only, +Y up; exclude Blender cameras and lights. Let the exporter convert axes once.
- Verify final dimensions and pivots. Apply scale/rotation only when appropriate for the asset's rig and hierarchy. Do not apply every modifier indiscriminately; confirm the exported silhouette.
- Use Principled BSDF PBR values and supported image textures. Procedural Blender textures need baking or a deliberate Godot material. Inspect actual pixels/material parameters if appearance changes.
- Keep game logic, triggers, flame effects, and collisions in a Godot wrapper scene. Imported GLB files are replaceable assets.
- For prototype collisions prefer explicit `CollisionShape3D`. Godot's optional import suffixes include `-colonly` and `-convcolonly`; Unreal's `UCX_` is not the convention here.

## Verify the result

Import into Godot and check scale, orientation, materials, origin, and any animation. Compare a Godot view with the Blender view for visible changes. An attractive Blender render does not validate the in-game result.

`./tools/check_pipeline.py` checks a temporary asymmetric box through Blender → GLB → Godot, including dimensions and material values. It is a tooling check, not acceptance of the requested asset. Then test the asset's actual interaction in the game and report the files and evidence.
