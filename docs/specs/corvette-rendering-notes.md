# Corvette Rendering — Community Techniques

## Module Morphing via Directional Vector Scaling

The NMS modding community uses Blender to create custom corvette designs beyond what the in-game builder offers. The technique:

1. Import meshes into Blender — not just corvette modules but **any NMS model part** (ship components, freighter parts, base building pieces, etc.).
2. Scale the **directional vectors** (local X/Y/Z axes) non-uniformly to morph parts into new shapes while preserving correct proportions along each axis.
3. Assemble the morphed parts into complex ship forms by aligning attachment points.

This means accurate corvette rendering must account for **per-axis scale transforms** on each module — not just uniform scaling. The scene node `Transform` already carries a full TRS (translate/rotate/scale) matrix, but fidelity requires applying these transforms exactly as Blender and the game engine do: local scale applied before parent rotation and translation.

## Implications for the 3D View

- Module meshes must be rendered with their full local scale, not normalized.
- Non-uniform scale on parent nodes propagates to children (multiplicative, not additive).
- Preview fidelity depends on matching the game's transform application order: Scale -> Rotate -> Translate, composed bottom-up through the scene hierarchy.
- The mesh pipeline should support loading arbitrary NMS model parts, not only corvette-specific modules.
