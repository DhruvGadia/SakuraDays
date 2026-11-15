# SakuraDays — HANA café exterior

One original modular café exterior and one small street-prop set for inspection. The kit follows the [SakuraDays art direction](../../../Docs/ART_DIRECTION.md): cream walls, dark plum framing, muted blue-gray roofs and glazing, matte wood, simple green foliage and a restrained rose awning. The Local Café reference informs the frontage and furnishings; Style A and Style B control the simplified anime treatment.

The original sign design reads **HANA — COFFEE + TEA** and uses a simple five-petal emblem. The menu board reads **HANA / COFFEE / TEA / CAKE**. All lettering is deliberate Latin text; no unreviewed Japanese text is included. The signs are fictional environment art, not a trademark-clearance claim.

This is an exterior art kit. Windows use opaque blue-gray panels with graphic reflection strips. The door is a static mesh, with no opening animation or interaction. There is no playable interior, café gameplay, authored collision or LOD chain yet. No additional prop design variations were generated; two chairs and two potted plants in the assembly reuse the same source meshes.

## Files

| File | Purpose |
|---|---|
| [Cafe01.blend](Cafe01.blend) | Editable module library, linked café assembly, source lettering, materials and preview setup |
| [build_cafe.py](build_cafe.py) | Procedural café construction, UV preparation, assembly, FBX export and preview rendering |
| [prop_build.py](prop_build.py) | Original procedural chair, table, bench, lamp, potted plant, rectangular planter and AC unit |
| [Exports](Exports) | Individual `SM_Cafe_*` module/prop FBXs and `SM_Cafe01_Assembled.fbx` |
| [Previews](Previews) | Three-quarter, front, entrance and prop-set renders |
| [build_manifest.json](build_manifest.json) | Exact geometry counts, dimensions, material names and assembled UV1 grid |
| [validate_cafe.py](validate_cafe.py) | Source and Blender FBX roundtrip checks |
| [validate_unreal.py](validate_unreal.py) | Fresh imports into an isolated Unreal test project |

The four preview filenames are `Cafe01_ThreeQuarter.png`, `Cafe01_Front.png`, `Cafe01_Entrance.png` and `Cafe01_PropSet.png`. They are actual Blender renders of the supplied geometry, not Unreal gameplay captures or generated concept images. The prop sheet presents the same props separately for inspection.

## Modular construction and scale

The building shell is **6 m wide × 5 m deep**, organized into three 2 m frontage bays. Ground-floor wall modules are 3.2 m high; upper modules are 2.7 m high, above a 0.18 m foundation. The roof ridge reaches approximately 7.07 m. The storefront door mesh is 1.3 × 2.6 m; display windows are 1.68 × 2.05 m and upper windows are 1.2 × 1.35 m. A repeated 2 m awning projects approximately 1.2 m from the wall.

Reusable pieces include window/door/solid wall bays, upper walls, two window sizes, the door, scalloped awning, story and corner trims, foundation, roof slopes, ridge, gable, gutter and downpipe. The fascia sign, projecting round sign and menu board are independent meshes. Street props comprise one chair, table, bench, street lamp, potted plant, rectangular planter and outdoor AC unit.

The final manifest records **28 prototypes**, **83 placed instances** and **10,526 triangles** in the combined scene export, including furnishings and signs. There are **29 FBXs**: the 28 reusable pieces plus the assembled café. Combined bounds are approximately **7.944 × 7.510 × 7.070 m**, including props extending beyond the building footprint. The combined mesh uses 16 material sections; individual pieces use only their required slots. Consult the manifest again after a rebuild, as review corrections may change these numbers. The seven procedural props together use 3,484 triangles.

Blender uses meters: **1 unit = 1 m**, **+Z up**, designated façade front **-Y**. Library objects have identity transforms. Pivots are intentional construction anchors:

- Wall, foundation and trim modules: local construction origin, generally bottom-left at the wall plane.
- Window and door units: lower-left insertion point in the corresponding opening.
- Awning: upper rear-left wall attachment; fabric and brackets extend forward and downward.
- Ground props: base center; small geometric protrusions around a pivot are checked during integration.
- Fascia sign: centered along X at its lower mounting edge. The round sign uses its wall attachment plane; the menu board uses its ground construction origin.
- Combined café: building-footprint center at ground origin. Its bounds center differs because the street props extend toward the front and right.

One-meter end wall pieces and 0.2 m roof end extensions are mesh-scaled copies of the 2 m modules in this assembly, with object scale retained at one. Dark bargeboards finish the roof ends. The supplied combined FBX already contains the props shown around the café: do not place it together with those same individual props unless duplicate furnishings are intended.

## Editing and rebuilding

The source collections are:

- `01_MODULE_LIBRARY`: hidden named prototypes at their construction pivots. Unhide and isolate one at a time.
- `02_CAFE_ASSEMBLY`: the café and its furnishings. Most meshes share library data; the 1 m side-wall fillers use mesh copies.
- `03_PREVIEW_ONLY`: ground, camera and lighting, excluded from exports.
- `04_EDITABLE_SIGN_TEXT`: hidden original text curves before mesh conversion.

Edit a shared prototype mesh to update its linked assembly instances. Each placed object's `module` property identifies its source. Editing a text curve does **not** automatically update the converted sign mesh already used by the assembly. Change the strings/layout in `build_cafe.py` and rebuild, or explicitly reconvert and replace the sign lettering while retaining its anchor and material names.

Run from the SakuraDays project root:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python '.\SourceArt\Architecture\Cafe01\build_cafe.py'
```

Add `-- --draft` for quick reduced-resolution renders or `-- --no-render` to regenerate geometry and exports without rendering. The builder replaces this kit's named generated outputs. Save hand-edited versions separately before rebuilding. The `.blend` is covered by the project's existing Git LFS rule.

## Materials and UVs

Materials are named `M_Cafe_*`. The palette and exact names are recorded in the manifest; assign by name because slot count and ordering differ by module. Most surfaces use opaque Default Lit materials, metallic 0, roughness near 0.82 and restrained specular. The lamp has a small warm emission contribution in the Blender preview. It contains no working Unreal light component.

There are no image-texture dependencies. Lettering, the blossom emblem and reflection strips are geometry. Plants use simple opaque foliage meshes, avoiding opacity-mask overdraw. Surface detail is deliberately quiet; no photoreal bark, wood-grain or dirt texture is required for this inspection asset.

Each prototype has `UV0_Surface` and `UV1_Lightmap`, packed within 0–1. Repeated instances intentionally reuse UV0. For the combined export, the builder remaps UV1 into unique per-instance grid cells before joining temporary export copies. The source meshes remain linked and unmodified by that export remap. Use the provided exporter to preserve the combined UV1 arrangement. Small cells may require repacking or a suitable lightmap resolution for a later baked-lighting workflow; this is not a light-build quality result.

## Unreal import

Import through Unreal Editor into an approved `Content/SakuraDays/` location. Use the individual modules for reusable placement or the assembled FBX for an initial visual inspection.

1. Import as **Static Mesh**, with Convert Scene and Convert Scene Unit enabled, Force Front X Axis enabled, uniform scale **1.0**, and zero extra translation/rotation.
2. Preserve the supplied UV channels: Generate Lightmap UVs off. Set lightmap coordinate index 1 if later using baked lighting, and inspect resolution/padding.
3. Use Combine Meshes on for the combined FBX; each supplied file already represents one mesh. Reuse/create the named materials. Inspect imported shader values rather than assuming Blender nodes translate exactly.
4. Check centimeter dimensions: Unreal X corresponds to Blender Y × 100, Unreal Y to Blender X × 100, and height remains Z × 100. Do not repair a unit error by scaling a placed actor by 100.
5. Auto Generate Collision is off in the validation workflow. Add deliberate simple collision for walls and blocking furniture during integration. Keep the entrance accessible; a single convex hull around the whole assembled café would also enclose the terrace and props.

There is no authored LOD chain. Assess actual draw calls, visible repetition and performance before adding mesh merging or LODs. The assembled export's 16 material sections trade convenience for batching efficiency; modular placement and shared materials offer more control during production.

Epic describes supported geometry, UVs, material slots, collision and LOD behavior in the [FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine) and [FBX Import Options](https://dev.epicgames.com/documentation/unreal-engine/fbx-import-options-reference-in-unreal-engine). For Interchange imports, verify equivalent settings and measured bounds rather than relying on identical option labels.

## Validation and remaining review

Final checks passed in **Blender 5.2.3** and **Unreal Engine 5.8.4**. Blender validated 28 source prototypes and all 29 FBX roundtrips: no degenerate geometry or UV triangles, correct material slots and pivots, metric/Z-up dimensions, and no detected overlaps in the tested prototype and assembled lightmap UVs. Unreal successfully imported all 29 files in the isolated test project and checked centimeter dimensions, triangle counts, material slots and both UV channels.

The four final renders were visually inspected. The hanging sign was raised clear of the awning, the bench/menu board were moved away from the doorway, and the gables were lowered under the roof surface to eliminate visible intersections. Three-quarter and front renders are 1600 × 1200; the entrance is 1600 × 1000 and the prop sheet is 1600 × 1100. The editable file opens with the matching three-quarter camera aspect ratio. These offline placement checks do not replace collision/navigation testing after integration.

Read `validation_blender.json` and `validation_unreal.json` when present for the latest completed checks. The scripts inspect geometry, transforms, UVs, named materials, dimensions and FBX import results. The Unreal validator is restricted to an isolated temporary project under ignored `Saved/Cafe01UEValidation/`; it does not import into the SakuraDays game project.

Review the four renders before requesting additional prop variants. Remaining integration work includes façade placement, final in-engine material/lighting review, collision, a moving-camera navigation check, LOD/performance decisions, and any future interior or door interaction. No existing maps, controls, gameplay files or Unreal assets are changed by this source-art task. No Play In Editor or packaged-game result is claimed here.

The kit is saved locally and has not been committed or pushed. The previously created sakura tree kit remains untouched.
