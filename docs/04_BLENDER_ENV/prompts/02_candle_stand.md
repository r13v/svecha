# Blender asset brief — Brass candle stand

Create the compact round brass candle stand from the object sheet and concept frame 06. Use an authored lathed pedestal profile, a stable stepped circular foot and a broad shallow tray with a low rim. Preserve the restrained turned silhouette; this first pass establishes construction and scale before patina and fine surface detail.

## Model contract

- Root: `CandleStand`, at ground level and centered on the pedestal.
- Total height: 1.14595 m; tray diameter: 0.68 m; base diameter: 0.3643 m.
- Nineteen hollow sockets: 12 on a ring of radius 0.276857 m, 6 on a ring of radius 0.160286 m, one central socket. Reuse the same socket mesh.
- Each bore is 0.011 m wide and accepts the 0.010 m candle. The cup begins at Blender Z=1.10095 m; its interior floor is at Z=1.10495 m. Socket tops reach 1.14595 m.
- Add exported empty attachment nodes `Seat00`–`Seat18` at the interior floors. `Seat00` lies toward the visitor: Blender `(0, -0.276857, 1.10495)` becomes Godot `(0, 1.10495, 0.276857)`.
- Keep all sockets empty in the reusable GLB. The game places independent candles into their seat nodes and consumes each candle's finite fuel.
- Use a shared Principled BSDF brass material with metallic 0.94 and roughness 0.28. No procedural-only materials in the GLB, no embedded light or environment geometry.
- Keep the first-pass total under 35,000 rendered triangles; use smooth shading on curved sides and clean tray rim normals.

Save `art/blender/candle_stand.blend`; export selected asset hierarchy to `game/assets/models/candle_stand.glb` as GLB with +Y up, no cameras or lights.

## Acceptance

Import into Godot. Check total bounds and grounded base, nineteen distinct seat nodes, player-facing `Seat00`, physical fit of the candle/residue, preserved PBR parameters, and a visual view in the actual renderer. Studio rendering alone is insufficient. Exact antique surface finish and the final level composition are later work.
