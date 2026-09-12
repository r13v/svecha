# Blender asset brief — Candle and burnt residue

Create two separate original game assets for «Свеча», following the candle group in `docs/03_OBJECT_SHEETS/generated_images/01_interactive_church_props_v3.png` and the interaction concepts. Use meters, unit scale 1.0, natural honey-yellow beeswax and a dark short wick. Keep geometry simple enough for first-person real-time rendering.

## Candle

- Wax body: 0.25 m tall and 0.007 m in diameter. Origin at the base, local Blender Z is up.
- Separate nodes: `Candle` root, `Wax`, `WickAnchor` at the top, `Wick` below that anchor, and `FlameAnchor` near the wick tip.
- The runtime can shorten `Wax` only along its vertical axis while leaving its base and diameter fixed. The wick anchor must move with the current top; it must not be embedded in the same mesh as the whole body.
- No flame mesh, emissive glow or baked lighting in the exported model. Godot will own the finite burn-time simulation and flame effects.
- Use a supported Principled BSDF material. Start with metallic 0 and roughness 0.42; surface detail can be added after gameplay scale is verified.

Save `art/blender/candle.blend`; export selected asset nodes to `game/assets/models/candle.glb`.

## Burnt residue

- A separate small irregular cooled wax remnant and charred wick, with no intact candle shaft, fire or glow.
- For this first model, fit the residue within a 9 mm socket bore, with a total height below 5 mm. Origin at its base.
- Name the root `CandleRemnant`; keep wax and wick separately inspectable.

Save `art/blender/candle_remnant.blend`; export `game/assets/models/candle_remnant.glb`.

## Acceptance

GLB, +Y up, selected asset only, no studio cameras/lights. In Godot verify the 25 cm wax height and 7 mm diameter, base anchoring at intermediate heights, a wick that follows the moving top, and replacement by the small non-burning residue at zero. A static comparison of three candle sizes does not implement continuous consumption. The visual inspector does not calibrate burn duration.
