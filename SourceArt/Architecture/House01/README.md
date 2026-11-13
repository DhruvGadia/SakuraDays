# SakuraDays — House 01 inspection candidate

One original modular residential house, created with Blender Python on 14 November 2026. This is an exterior art asset for review, not a second street level or a finished interactive building.

## Files

| File | Purpose |
|---|---|
| `SakuraHouse01.blend` | Editable source, module library, assembled house, preview camera and lights |
| `build_house.py` | Rebuilds this one house, exports its kit, and renders the three views |
| `Exports/SM_SakuraHouse01_Assembled.fbx` | Complete house; import with Combine Meshes enabled |
| Other 23 `Exports/SM_*.fbx` files | Individual reusable modules at local pivots; these are components, not additional houses |
| `Previews/House01_ThreeQuarter.png` | Primary 1600×1200 inspection render |
| `Previews/House01_Front.png`, `Previews/House01_Rear.png` | Additional views of the same house |
| `build_manifest.json` | Dimensions, module inventory, triangle counts, material names and export settings |
| `validation_blender.json` | Source UV tests and final FBX round-trip results |
| `validation_unreal.json` | Real UE 5.8.4 import checks in an isolated temporary project |
| `validate_house.py`, `validate_unreal.py` | Reproducible validation scripts |

The source is kept outside `Content` because it is a Blender source asset. Nothing has been imported into SakuraDays' main Content folder, and its maps, character controls, inputs and existing assets are untouched by this task. The temporary Unreal import lives under ignored `Saved/House01UEValidation/`.

## Art decisions

Style A and Style B remain the primary authorities: broad cream plaster, pale blue-gray siding, slate roof planes, dark plum trim, matte surfaces, and simple graphic window reflections. The residential alley supplies the compact house and eave vocabulary. Main Street remains a composition reference; its dense decorative timber and luminous shop windows do not set this house's finish.

The house uses geometry for window recesses, sliding frames, eaves, shallow roof courses, gutters, drainpipes, an entry canopy, balcony railings and one outdoor air-conditioning unit. Surface detail is restrained. There are no image textures or external texture dependencies. The opaque blue windows have simple diagonal reflection meshes, keeping their appearance legible without real-time transparency or expensive reflections.

The Blender preview uses ordinary lit matte materials with modeled dark trim. It is not proof of an Unreal toon shader or a final in-game lighting match. No global outline effect is baked into the mesh.

## Dimensions and orientation

| Measurement | Value |
|---|---|
| Wall footprint | 8.0 m wide × 6.0 m deep |
| Foundation | 0.30 m high |
| Repeated façade bay | 2.0 m wide × 2.8 m high, nominal wall thickness 0.18 m |
| Stories | Two; wall top at 5.9 m |
| Door opening / leaf assembly | 1.10 m × 2.20 m; outer frame 1.22 m × 2.26 m |
| Standard window opening | 1.40 m × 1.40 m |
| Balcony window opening | 1.40 m × 2.20 m |
| Balcony | Two 2 m sections, approximately 1 m projection |
| Roof | 2 m repeat along ridge, 3.6 m slope run, 1.35 m rise; 0.4 m end filler variants |
| Entire asset bounds | 8.940 m wide × 7.705 m deep × 7.165 m high, including eaves, trims and balcony |
| Blender units | Metric, 1 unit = 1 m; front -Y, up +Z |
| Assembled pivot | Ground-level center of the wall footprint, (0,0,0) |
| Unreal verified bounds | X 770.5 cm × Y 894.0 cm × Z 716.5 cm with Force Front X enabled |
| Unreal facing | Front +X, width along Y, up +Z; import scale 1.0 |

Module pivots are at their local construction origin, generally bottom-left-front. Negative protrusions for a sill, roof overhang, or frame are intentional. Each module exports independently at the origin. All object scales are positive and equal to one; façade rotations in the assembled file are intentional placement transforms. The assembled mesh has 9,496 triangles across 141 named source objects. No cameras, lights, ground plane or library duplicates are in the FBX.

## Module editing

The Blender collections are:

- `01_MODULE_LIBRARY`: 23 reusable prototypes, hidden from viewport and render by default. Unhide only a prototype being inspected and isolate it to avoid overlapping all origin-centered modules.
- `02_HOUSE01_ASSEMBLY`: the single composed house. Most instances share prototype mesh data. Roof length fillers use mesh copies.
- `03_PREVIEW_ONLY`: ground, camera and sunlight. Never export this collection as game geometry.

Select a wall prototype and edit its mesh to update linked instances. The `module` custom property on an assembly object records its source module. Use 2 m increments along a façade and 2.8 m per story. Keep the 0.3 m foundation offset. Window/door modules fit the matching wall openings; they are not animated Blueprints.

Source meshes are composed of closed prism components except for deliberate single-sided window reflection faces. Hard planar normals preserve the simplified architectural shading. Hidden/internal junction faces remain for modularity; this is not a single watertight architectural solid. Do not apply a blanket weld or smooth operation across the whole kit.

## Materials and UVs

The source uses the following stable named material slots. Values below are sRGB swatches; the script converts them to linear values for Blender's shader inputs.

| Slot | Material | Color | Roughness |
|---|---|---|---|
| 0 | `M_Plaster_Cream` | `#DDC9AD` | 0.88 |
| 1 | `M_Siding_BlueGray` | `#A7B5C0` | 0.85 |
| 2 | `M_Trim_Plum` | `#393344` | 0.78 |
| 3 | `M_Roof_Slate` | `#555B70` | 0.85 |
| 4 | `M_Timber_Warm` | `#725548` | 0.80 |
| 5 | `M_Glass_Blue` | `#6E93AF` | 0.48 |
| 6 | `M_Glass_Reflection` | `#BDD0DD` | 0.60 |
| 7 | `M_Concrete` | `#B8B1A9` | 0.90 |

Every source module has `UV0_Surface` and `UV1_Lightmap`, packed within 0–1. The module tests check every triangulated UV0 face for nonzero area and every candidate triangle pair for overlap; UV1 is copied from that validated layout. The kit has no detected overlapping or collapsed UV triangles within a module. Repeated instances intentionally share UV0 coordinates.

For the assembled FBX only, the exporter remaps UV1 into a unique 12×12 per-object atlas. The round-trip validator checks that all 141 object atlas bounds are disjoint and within 0–1. This prevents the combined house's lightmap UVs from stacking. The editable linked Blender assembly retains each module's local UV1; use the supplied export function rather than a plain manual export if importing the complete house as one mesh. Small lightmap islands may need a higher resolution or repacking for future baked-lighting production; this is not a light-build quality test.

Unreal imported eight material slots on the combined house and retained both source UV channels. Individual module imports may discard unused slots; assign by material name, not a presumed identical slot index across all imported modules.

## Unreal import recipe

The isolated validation used the legacy FBX importer (`FbxFactory`) with:

- Static Mesh; Combine Meshes **on** for `SM_SakuraHouse01_Assembled.fbx`.
- Convert Scene **on**, Convert Scene Unit **on**, Force Front X Axis **on**.
- Import Uniform Scale **1.0**, no additional translation or rotation.
- Generate Lightmap UVs **off**, preserving the supplied two channels. If using baked lighting later, set lightmap coordinate index 1 and validate resolution in-engine.
- Material and texture import **off** for the validation; it verified mesh slots, not final Unreal material appearance. Create/reuse eight matching Default Lit materials from the table, or inspect the FBX-imported materials before using them.
- Auto Generate Collision **off** during validation. Add intentional simple exterior collision after this house is approved; do not use an automatically generated whole-house convex hull for an eventual playable interior.

If using Unreal's newer Interchange UI, use equivalent axis/unit settings and check the reported dimensions rather than assuming identical option labels or defaults. Do not apply an additional 100× import scale.

Reimport caveat: one automated replacement-import test unexpectedly used unconverted axes and meter-sized numerical bounds in Unreal. A fresh asset import with the settings above passed. The validator now always uses a fresh temporary asset path to avoid stale import state. For later reimports, explicitly check the stored conversion settings and verify the 770.5 × 894.0 × 716.5 cm bounds; do not compensate by scaling the placed actor.

The FBX is Blender's binary 7.4 export. Epic documents an FBX 2020.2 pipeline; compatibility here was established by an actual import with the installed engine, not by treating the version numbers as equivalent. See [Epic's FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine?lang=en-US) and [Blender's FBX export documentation](https://docs.blender.org/manual/en/5.3/files/import_export/fbx_legacy.html).

## Validation and remaining review

Source UV and material-index checks passed. Reimporting the assembled FBX into Blender retained all 141 objects, orientation and dimensions, with maximum bound error below 0.000001 m. Unreal import confirmed centimeter scale, axis conversion, two readable source UV channels and eight combined material slots. Validation reports contain the exact measurements.

The front, rear and three-quarter previews were rendered from this asset and inspected. Roof/gable surface intersections found in the initial preview were corrected. Preview renders are not generated concept images.

This remains an exterior-only inspection candidate: no interior floors/stairs, opening doors, gameplay collision, LOD chain, street placement or PIE integration test is included. The balcony and roof are visual exterior geometry. Review window repetition, trim thickness, roof pitch and palette before authorizing additional houses. No second house or variant has been generated.

To rebuild, run Blender in background with `--python build_house.py` using an absolute script path. This regenerates this folder's named house deliverables, so save approved/manual edits elsewhere before rebuilding. The source `.blend` is covered by the project's existing Git LFS rule. Nothing was committed or pushed during this task.
