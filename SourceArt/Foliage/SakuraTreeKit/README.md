# SakuraDays sakura tree kit

Three original cherry blossom trees authored with Blender Python for the SakuraDays street. Style A and Style B set the appearance: grouped blush-pink blossom masses, dark tapered branches, asymmetric crowns, matte shading and a distinct weeping form. Main Street supplies environmental context rather than a different rendering style. See the project's [art direction](../../../Docs/ART_DIRECTION.md).

The kit contains a spreading hero, a smaller street tree and a weeping variation. Each has three separately exported geometry LODs. The previews are renders of these actual meshes in Blender; they are not Unreal gameplay captures. Final Unreal materials, street placement, moving-camera LOD review and performance profiling remain integration work.

## Deliverables

| File | Contents |
|---|---|
| `SakuraTreeKit.blend` | Editable sources for all three trees and all nine LOD meshes, collision hulls, packed blossom atlas, linked preview instances, lights and camera |
| `build_tree_kit.py` | Deterministic Blender generation, FBX export and preview-render script |
| `Exports/SM_Sakura_Hero_LOD0.fbx` through `LOD2.fbx` | Spreading hero at three detail levels |
| `Exports/SM_Sakura_Spread_LOD0.fbx` through `LOD2.fbx` | Smaller street variation at three detail levels |
| `Exports/SM_Sakura_Weeping_LOD0.fbx` through `LOD2.fbx` | Hanging branch variation at three detail levels |
| `Textures/T_Sakura_Blossom_Atlas.png` | Shared original 1024 × 1024 RGBA atlas with four five-petal blossom sprays |
| `Previews/SakuraTreeKit_Lineup.png` | Three-tree comparison render |
| `Previews/Sakura_Hero_ThreeQuarter.png`, `Sakura_Spread_ThreeQuarter.png`, `Sakura_Weeping_ThreeQuarter.png` | Individual inspection renders |
| `preview_lods.py`, `Previews/Sakura_Hero_LODs.png`, `Sakura_Spread_LODs.png`, `Sakura_Weeping_LODs.png` | Same-camera comparisons of LOD0, LOD1 and LOD2 for each tree; the script reads the saved kit without resaving it |
| `build_manifest.json` | Exact bounds, geometry counts, material slots, collision counts and export settings |
| `validate_tree_kit.py`, `validation_blender.json` | Source checks and fresh Blender FBX roundtrip validation |
| `validate_unreal.py`, `validation_unreal.json` | Fresh imports into a separate temporary Unreal project; see the report for results |

Keep the `Textures` folder with `Exports`: the FBXs use relative texture paths. The `.blend` also packs the atlas so it remains editable when opened on another machine. The project's existing Git LFS rule covers `.blend` sources.

## Dimensions and geometry budget

The mesh origin is at the trunk base on ground level. Blender uses meters, +Z up and a designated -Y display front. Object location and rotation are zero and scale is one. Tree crowns are asymmetric, so their bounding-box center is intentionally offset from the trunk pivot.

The table reports Blender X × Y × Z bounds. Geometry counts exclude the three simple collision hulls accompanying each FBX. `build_manifest.json` is the authoritative record if the kit is rebuilt.

| Tree | LOD | Triangles | Blossom cards | Bounds, meters |
|---|---:|---:|---:|---|
| Hero | 0 | 11,964 | 2,268 | 9.613 × 9.179 × 7.679 |
| Hero | 1 | 5,604 | 1,260 | 9.649 × 9.348 × 7.736 |
| Hero | 2 | 1,908 | 630 | 9.710 × 9.356 × 7.832 |
| Street | 0 | 9,572 | 1,800 | 6.278 × 5.906 × 5.951 |
| Street | 1 | 4,484 | 1,000 | 6.421 × 6.008 × 5.997 |
| Street | 2 | 1,556 | 500 | 6.457 × 6.213 × 6.113 |
| Weeping | 0 | 19,792 | 4,306 | 7.494 × 8.823 × 7.388 |
| Weeping | 1 | 9,588 | 2,506 | 7.580 × 8.812 × 7.456 |
| Weeping | 2 | 3,108 | 1,253 | 7.779 × 8.965 × 7.532 |

Lower LODs retain fewer blossom cards with slightly larger coverage to preserve the crown. Their bounds therefore differ modestly. Review silhouette changes and transitions at the actual camera distance before fixing LOD thresholds. These are alternate LODs of the same three trees, not additional tree designs.

## Editing the source

The Blender collections separate editable game geometry from presentation:

- `01_EXPORT_MESHES_at_ground_origin`: all nine named source meshes. They are hidden initially because they share the ground origin. Unhide one source at a time to inspect or edit it.
- `02_TRUNK_COLLISION_export_only`: three tapered convex hulls per tree LOD, named `UCX_<exact mesh name>_00` through `_02`. They cover the main trunk, not the canopy or all roots and branches.
- `03_PREVIEW_ONLY_never_export`: linked LOD0 display instances, studio floor, labels, lighting and camera. This collection is excluded from the supplied exports.

The preview objects share mesh data with the corresponding LOD0 sources. Editing that mesh changes both. LOD1 and LOD2 are separate meshes; manual LOD0 edits do not regenerate them automatically. Change the named variant parameters and deterministic seeds in the script to rebuild a coordinated kit, then validate again.

Branches use tapered tube geometry with smooth shading and restrained vertex-color variation. Blossom volume comes from irregularly oriented masked cards. The procedural atlas contains authored flower silhouettes and color variation; it uses no downloaded plant images. There is no skeleton, physics simulation or baked animation.

To regenerate with the installed Blender:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python '.\SourceArt\Foliage\SakuraTreeKit\build_tree_kit.py'
```

Run from the SakuraDays project root. Add `-- --draft` for lower-resolution preview renders or `-- --no-render` to build sources and exports without renders. Regeneration replaces this kit's named generated products. Save manual edits as a separate file before rebuilding. The script does not alter existing Unreal maps or gameplay assets.

## Materials, vertex colors and UVs

Every tree has the same two material slots:

| Slot | Name | Intended Unreal treatment |
|---|---|---|
| 0 | `M_Sakura_Bark` | Opaque Default Lit; base sRGB color `#51414F` multiplied by vertex Color RGB; metallic 0, roughness around 0.9, restrained specular |
| 1 | `M_Sakura_Blossom` | Masked and Two Sided; atlas RGB multiplied by vertex Color RGB; atlas alpha into Opacity Mask; clip value 0.4; metallic 0, roughness around 0.9 |

Import the atlas as an sRGB color texture and retain its alpha channel. Use the texture's RGB and alpha outputs separately. Start with Default Lit or evaluate Two Sided Foliage with a restrained pink Subsurface Color under the street's daylight. Choose the shading model during the material study rather than assuming Blender shading nodes translate exactly. Blender's preview has a small blossom fill contribution; it is not a required emissive Unreal material.

The `Color` vertex attribute carries linear tint in RGB. Its alpha is a separate optional wind weight: zero on bark and approximately 0.4–1.0 on blossoms. Do **not** multiply that alpha into opacity. No wind animation is included; a later World Position Offset setup can use the weight after checking motion, shadows and bounds. Keep whole-tree movement subtle and preserve trunk anchoring.

`UV0_Surface` contains reusable blossom atlas islands and cylindrical bark UVs. Islands intentionally overlap because many flowers share the same four atlas tiles. They are not unique lightmap UVs. No UV1 is supplied. The initial use is dynamic lighting; baked lighting would need a deliberate secondary UV/lightmap workflow and validation.

The FBX preserves material slot names, UVs and vertex colors. Recreate or assign the two Unreal materials explicitly. Automatic FBX material import is not a substitute for the masked, two-sided foliage setup. A tree displayed as opaque rectangular cards normally indicates missing opacity-mask wiring or the wrong blend mode.

## Unreal import and LOD setup

Use Unreal Editor for imports. Keep future approved assets under `Content/SakuraDays/`, following the project rules. The validation scripts import only into an isolated temporary project under ignored `Saved/SakuraTreeUEValidation/`.

1. Import one tree's `LOD0.fbx` as a Static Mesh. Use Convert Scene **on**, Convert Scene Unit **on**, Force Front X Axis **on**, uniform scale **1.0**, and zero added rotation/translation. The supplied FBXs were exported using Blender's `FBX_SCALE_UNITS`, global scale 1, -Y forward and +Z up.
2. For the validation's legacy FBX path, Combine Meshes is **on**, Auto Generate Collision is **off**, One Convex Hull Per UCX is **on**, Generate Lightmap UVs is **off**, and Vertex Color Import Option is **Replace**. Import materials/textures is **off** in the geometry validator; import the shared texture and create the two materials separately.
3. Check the actual centimeter bounds. With Force Front X, Blender X/Y dimensions swap: Unreal X is Blender Y × 100, Unreal Y is Blender X × 100, and Z is height × 100. Do not compensate for an incorrect import with an actor scale of 100.
4. Confirm two material slots, the `Color` attribute's effect, one UV channel and three convex trunk collision hulls. Keep canopy cards nonblocking. The small trunk hulls are a starting collision proxy; check the player's capsule around the base after placement.
5. Open the LOD0 Static Mesh and use its LOD import controls to import the matching `LOD1.fbx` and `LOD2.fbx` as LOD levels 1 and 2. Each supplied FBX contains one detail level; importing all nine files into the Content Browser does **not** automatically assemble three LOD chains.
6. Use the same two materials at every LOD. Screen sizes `1.0`, `0.28`, `0.10` are suggested starting values, not validated gameplay thresholds. Compare transitions from the real third-person and reference cameras, then tune them.

If using Interchange rather than the legacy FBX importer, verify equivalent unit, axis, vertex-color, collision and material settings and compare the measured result. Reimports should retain those settings; always recheck bounds and appearance after a workflow change.

Epic documents vertex colors, custom collision naming and LOD support in the [FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine) and the detailed settings in [FBX Import Options](https://dev.epicgames.com/documentation/unreal-engine/fbx-import-options-reference-in-unreal-engine). Blender's binary FBX export is not described here as an FBX 2020.2 exporter; compatibility is assessed using real imports with the installed engine.

## Validation and performance review

The final source and all nine FBX roundtrips passed Blender validation with no asset errors or warnings. The report includes source/export hashes. Separate `preview_lods.py` renders the three `Previews/Sakura_*_LODs.png` comparison sheets without saving or changing the editable source. Individual previews are 1600 × 1200, the lineup is 1920 × 1080, and LOD comparisons are 1600 × 900. These are actual Blender renders of the supplied meshes.

All nine final FBXs also passed fresh import validation in Unreal Engine **5.8.4** in the isolated project. Each retained its triangle count, two material slots, one UV channel and three convex trunk hulls. Maximum centimeter bounds error was below **0.00004 cm**. The headless validator explicitly instantiates its read-only mesh-query subsystem because commandlets do not register that editor subsystem automatically. The final report contains no validation errors.

LOD2 visibly thins blossom coverage and small branches; reserve it for distant trees. Final distance thresholds still need a moving-camera review. No existing SakuraDays content or project configuration was changed, and this task does not commit or push the new source-art files.

`validate_tree_kit.py` checks all nine source meshes and fresh Blender FBX roundtrips: metric scale, ground-origin transforms, finite nondegenerate UV0 triangles, named material slots, vertex colors, Z-up bounds, decreasing LOD triangle counts and closed convex named collision hulls. Overlapping UVs are intentional and are not treated as a failure. Read `validation_blender.json` for the actual result of the latest run.

`validate_unreal.py` is guarded to the isolated test project. It checks fresh imports for centimeter bounds, material slots, UV count, triangle counts and custom collision hull count. Its JSON report records the engine version and each imported asset. This geometry test does not validate the final foliage shader, connected LOD transitions, street collision, PIE or packaged performance.

The kit limits texture memory to one shared 1024 atlas and uses two material sections per tree. Conventional static-mesh LODs are supplied; Nanite and hardware ray tracing are not prerequisites. Masked two-sided cards can still be fill-rate and shadow intensive, especially the weeping tree. Triangle count alone cannot establish frame rate.

For the first street integration, inspect shader complexity/overdraw, foliage shadows, mip behavior and edge shimmer on the development laptop. Compare the same visible tree count at the intended output resolution. Tune shadow distance, LOD transitions and distant culling using those measurements. Check that low hanging sprays preserve the player's route and keep café/NPC sightlines readable. No FPS target or final platform budget is claimed by these offline renders.
