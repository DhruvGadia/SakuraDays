# HouseTownVariants

Two contemporary Japanese residential silhouettes derived from the approved [House01](../House01/README.md) modules for the SakuraDays town-refinement pass. The original `House01/SakuraHouse01.blend`, its modular exports and Unreal assets are preserved. These variants reuse the established windows, walls, entrance, balconies and material palette.

`HouseTownVariants.blend` contains the retained source scene and two new assembled editable meshes in the `UrbanFlat` and `HipRoof` collections. Generated meshes are hidden at save time; unhide the desired collection/object for inspection. `build_variants.py` opens the original House01 source, builds both variants and saves only this folder's generated Blender file, FBXs and manifest. **Copy intentional hand edits before rerunning it:** the builder regenerates these outputs rather than merging edits.

## Geometry and scale

| Variant | Design | Blender X × Y × Z bounds (m) | Unreal X × Y × Z bounds (cm) | Triangles |
|---|---|---:|---:|---:|
| UrbanFlat | Three-storey façade with a flat roof and parapet | 8.80 × 7.44 × 9.205 | 744 × 880 × 920.5 | 10,520 |
| HipRoof | Two-storey house with four roof slopes and a short ridge | 9.00 × 7.54 × 7.285 | 754 × 900 × 728.5 | 8,048 |

These are full exported bounds, including overhangs and entrance details. The principal closed house body is approximately 8 m wide by 6 m deep; its collision height is 8.7 m for UrbanFlat and 5.9 m for HipRoof. The houses are exterior scenery, not traversable interior shells.

- Blender uses meters, Z up and a façade facing -Y. The ground pivot is `(0, 0, 0)` with applied rotation and scale.
- FBX uses `FBX_SCALE_UNITS`, forward -Y, up Z, triangulated mesh geometry and no animation.
- The SakuraDays Unreal importer converts to centimeters and forces front X. The façade becomes +X and the width/depth dimension order swaps accordingly. No extra scale factor is needed at placement.
- Each export is one assembled mesh; these are not new independent modular kits or new families of every wall/window piece. No additional LOD chain is included.

## UVs and material slots

The builder recalculates face normals and deliberately creates exactly two UV channels on each new derived mesh: `UV0_Surface` and `UV1_Lightmap`. UV0 is smart-projected with an island margin of 0.004; UV1 copies that layout. The current scene uses dynamic lighting. A future baked-lighting workflow should inspect lightmap padding at its chosen resolution before baking.

Both variants retain the same eight named material slots in this order:

1. `M_Plaster_Cream`
2. `M_Siding_BlueGray`
3. `M_Trim_Plum`
4. `M_Roof_Slate`
5. `M_Timber_Warm`
6. `M_Glass_Blue`
7. `M_Glass_Reflection`
8. `M_Concrete`

The importer assigns existing House01 materials by slot name. The town material stage then adds actor-local façade/roof color variation, preserving the original mesh materials and source palette. Glazing is opaque stylized geometry with broad authored reflection shapes; it does not provide a café/house interior view.

## Unreal integration and collision

[`Tools/Unreal/import_house_variants.py`](../../../Tools/Unreal/import_house_variants.py) imports the FBXs into fingerprinted folders below `/Game/SakuraDays/Environment/JapaneseTown/Prompt12/Architecture/`. It validates imported dimensions against the source manifest, requires two UV channels and records triangle/collision counts. Original house assets are retained.

Each imported variant receives three deliberately simple box collision shapes: one closed exterior body and two entrance-step boxes. Decorative roof overhangs and individual window/balcony pieces do not receive complex collision. This keeps exterior navigation predictable but does not make balconies or rooms playable. The town pass places UrbanFlat on `SD_House02` and HipRoof on `SD_House04` and `SD_House05`, retaining the saved actors' placement and collision profiles.

The current import report passed for both variants with the dimensions and triangle counts above, two UV channels and three collision boxes each. Final scene/PIE evidence belongs to the [town refinement report](../../../Docs/TOWN_REFINEMENT.md); the Blender source alone does not validate gameplay.

## Rebuild

From the project root in PowerShell:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python SourceArt/Architecture/HouseTownVariants/build_variants.py
```

`build_manifest.json` is the authoritative source-bounds, slot and triangle record for these exports. Preserve the original House01 source and save manual variant edits separately before regeneration.
