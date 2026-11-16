# JapaneseTown01

Original procedural exterior kit for SakuraDays Prompt 12. Its warm plaster, blue-gray glazing and roofs, dark structural trim, and restrained red shop accents follow `Docs/ART_DIRECTION.md`. It supplements the existing HANA café and residential kit; it does not replace their source files.

`JapaneseTown01.blend` contains reusable modules, an assembled ramen shop, editable Japanese text, and a separate preview stage. `build_town_kit.py` builds the kit in Blender 5.2.3 LTS. Preserve hand edits before running the builder: it recreates this folder's generated Blender file, FBXs and manifest. `preview.py` opens the existing Blender scene and produces previews without saving the scene or touching FBXs.

## Contents and scale

All dimensions below are exported mesh bounds in meters, in Blender width X × depth Y × height Z order. Numbers are rounded; `build_manifest.json` contains full bounds, material slots and triangle counts for all 25 exports.

| Export | Dimensions (m) | Triangles | Purpose |
|---|---:|---:|---|
| `SM_RamenShop_Assembled` | 6.816 × 5.845 × 6.445 | 7,332 | Exterior-only shop, including its signs, curtains, lanterns, gutters and AC |
| `SM_VendingMachine` | 1.000 × 0.891 × 1.855 | 1,248 | Generic drinks machine, no copied brand or invented labels |
| `SM_CityBicycle` | 1.810 × 0.540 × 1.129 | 2,232 | City bicycle with basket, rear rack and kickstand |
| `SM_PublicNoticeboard` | 1.880 × 0.370 × 2.150 | 2,076 | Neighborhood noticeboard with ruled blank notices |
| `SM_RoadsideMirror` | 0.640 × 0.132 × 3.170 | 322 | Orange roadside mirror with authored reflection colors |
| `SM_ResidentialMailbox` | 0.540 × 0.360 × 1.255 | 60 | Post-mounted residential mailbox |
| `SM_AC_Outdoor` | 0.840 × 0.436 × 0.630 | 436 | Outdoor air-conditioning condenser |
| `SM_SmallTorii` | 3.600 × 0.360 × 3.182 | 224 | Optional compact shrine entrance |
| `SM_Balcony_Compact_320` | 3.260 × 0.900 × 1.087 | 392 | Residential balcony module |
| `SM_Shutter_76x140` | 0.760 × 0.105 × 1.400 | 156 | Residential shutter module |
| `SM_Gutter_3m` | 3.000 × 0.145 × 0.130 | 24 | Reusable roof gutter |
| `SM_Downpipe_3m` | 0.110 × 0.343 × 3.000 | 144 | Reusable downpipe with brackets |

The remaining exports are shop shell, roof, canopy, glazing, upper window, noren, lantern and standalone signs. The shop body is approximately 6 m wide and 4.6 m deep; the full export bounds include roof overhangs, the canopy and exterior equipment.

## Japanese lettering

Text is deterministic Unicode converted to mesh outlines, not generated image lettering. The builder reads the installed `C:/Windows/Fonts/YuGothB.ttc` (Yu Gothic Bold), checks every requested non-whitespace character against its Unicode `cmap`, and fails if a glyph is missing. The manifest records nonzero glyph IDs. No font binary is copied or packed into the project. Editable text objects retain a reference to the host font path; rebuilding or editing their typography on another machine requires an appropriately licensed Japanese font.

| Mesh | Authored text | Meaning / intended placement |
|---|---|---|
| `SM_Sign_Hana_Japanese` | 喫茶 花 | HANA café's supplemental Japanese fascia; preserve the original HANA identity |
| `SM_Sign_Ramen_Fascia` | ラーメン | Horizontal ramen shop fascia |
| `SM_Sign_Ramen_Vertical` | ラーメン | Vertical projecting shop sign; the prolonged-vowel mark is rotated for vertical writing |
| `SM_Ramen_Noren` | ラーメン | Ramen shop entrance curtain |
| `SM_Sign_Open` | 営業中 | “Open for business,” used only at a shop entrance |
| `SM_Sign_SakuraStreet` | さくら通り | Sakura Street name sign |
| `SM_PublicNoticeboard` | 掲示板 | “Noticeboard” heading; paper notices contain only simple ruled graphics |
| `SM_Road_StopSign` | 止まれ | “Stop,” on an inverted triangular sign; place only where a meaningful stopping point exists |

The builder's font coverage list also checks HANA, P and COFFEE + TEA for compatibility, but those strings are not added to new signs in this kit. There are no random kanji, false business addresses or fictional brands.

The separate `Previews/Japanese_Signage.png` is a typography inspection sheet. Actual gameplay legibility still depends on Unreal placement, scale, lighting and capture distance; use genuine Unreal screenshots for final scene approval.

## Materials and UVs

Each export has named material slots and two UV channels: `UV0_Surface` and `UV1_Lightmap`. Module UVs are smart-projected into 0–1. The assembled shop uses separate UV1 cells for its individual components. UV0 may reuse space between assembled instances because these surfaces use solid palette materials. The underlying geometry and normals are authored for flat, crisp architectural forms.

`build_manifest.json.materials` maps every exact `M_Town_*` slot name to its sRGB hex color. The main palette is:

| Slot | sRGB | Use |
|---|---|---|
| `M_Town_Plaster` | `#D9C8AD` | Warm cream walls |
| `M_Town_Siding` | `#8D9DAB` | Muted blue-gray residential panels |
| `M_Town_Timber` | `#705447` | Shop framing and wood |
| `M_Town_Trim` | `#393344` | Dark plum structural borders |
| `M_Town_Roof` | `#535B6D` | Roofs and gutters |
| `M_Town_Glass` | `#6F8EA4` | Simplified opaque blue glazing |
| `M_Town_Reflection` | `#B6CCD8` | Broad authored reflection shapes |
| `M_Town_Paper` | `#F0E3CC` | Sign faces, lettering and notices |
| `M_Town_RamenRed` | `#B74A44` | Restrained ramen and neighborhood accents |
| `M_Town_Noren` | `#963C3F` | Entrance curtain |
| `M_Town_VendingRed` | `#BD504E` | Drinks machine |
| `M_Town_Sage` | `#6F9581` | Noticeboard and mailbox |

Preview materials use roughness 0.82 and restrained specular. Glazing and roadside mirror are opaque stylized colors, not physical transparent glass or live reflections. The street import workflow creates Unreal materials explicitly from this palette; Blender shader graphs are not expected to transfer through FBX.

## Unreal import conventions

- Blender: metric, one unit = one meter, Z up, visible façade faces -Y.
- FBX: `apply_unit_scale=True`, `FBX_SCALE_UNITS`, global scale 1, forward -Y, up Z, triangulated, no animation.
- Existing SakuraDays import workflow: centimeters, force front X; the visible façade becomes +X. The X/Y dimension order swaps after this conversion.
- Building and prop pivots are at the local ground origin. Signs use their lower-center wall anchor, and architectural modules retain construction anchors for repeatable assembly. The shop's source modular shell/roof/glazing use assembly coordinates; use the assembled export for whole-building placement.
- No complex collision is baked into these FBXs. Add deliberate simple collision at integration: a shop-body box, machine-body box and minimal necessary prop collision. Decorative letters, gutters and wall-mounted equipment should not block the walking route. `recommended_collision_cm` contains starting box dimensions in Unreal orientation, not an automatically applied guarantee.
- LOD chains are not included. Triangle counts are modest, but material sections remain a performance consideration (the assembled shop has 12). Profile street draw calls and use instancing or consolidation where repeated placement warrants it.

## Preview commands

Run from a PowerShell prompt, adjusting the project path if necessary:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background 'C:/Users/HP/Documents/Unreal Projects/sakuradays/SourceArt/Environment/JapaneseTown01/JapaneseTown01.blend' --threads 4 --python 'C:/Users/HP/Documents/Unreal Projects/sakuradays/SourceArt/Environment/JapaneseTown01/preview.py'
```

The previews are genuine Blender renders using Cycles CPU, 16 samples, denoising and a 1000-pixel width. They show source geometry, not a claimed Unreal result. `Previews/preview_manifest.json` records the render files. The preview stage, camera and lighting are excluded from every FBX.
