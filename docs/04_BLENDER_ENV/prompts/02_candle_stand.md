# Blender asset brief — Brass candle stand

Create the compact round brass candle stand from the object sheet and concept frame 06. Use an authored lathed pedestal profile, a stable stepped circular foot and a broad shallow tray with a low rim. Preserve the restrained turned silhouette; this first pass establishes construction and scale before patina and fine surface detail.

## Model contract

- Root: `CandleStand`, at ground level and centered on the pedestal.
- Total height: 1.0 m; tray diameter: 0.56 m; base diameter: 0.30 m.
- Nineteen hollow sockets: 12 on a ring of radius 0.228 m, 6 on a ring of radius 0.132 m, one central socket. Reuse the same socket mesh.
- Each bore is 0.009 m wide and accepts the 0.007 m candle. The cup begins at Blender Z=0.970 m; its interior floor is at Z=0.974 m. Socket tops reach 1.0 m.
- Add exported empty attachment nodes `Seat00`–`Seat18` at the interior floors. `Seat00` lies toward the visitor: Blender `(0, -0.228, 0.974)` becomes Godot `(0, 0.974, 0.228)`.
- Keep all sockets empty in the reusable GLB. The game places independent candles into their seat nodes and consumes each candle's finite fuel.
- Use a shared Principled BSDF brass material with metallic 0.94 and roughness 0.28. No procedural-only materials in the GLB, no embedded light or environment geometry.
- Keep the first-pass total under 35,000 rendered triangles; use smooth shading on curved sides and clean tray rim normals.

Save `art/blender/candle_stand.blend`; export selected asset hierarchy to `game/assets/models/candle_stand.glb` as GLB with +Y up, no cameras or lights.

## Acceptance

Import into Godot. Check total bounds and grounded base, nineteen distinct seat nodes, player-facing `Seat00`, physical fit of the candle/residue, preserved PBR parameters, and a visual view in the actual renderer. Studio rendering alone is insufficient. Exact antique surface finish and the final level composition are later work.
