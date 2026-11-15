# SakuraDays asset import pilot

The allowlist contains exactly the approved assembled House01 FBX and the hero sakura LOD0 FBX. The café, other trees, house modules and tree LOD1/2 are deliberately not processed.

The completed pilot, real Unreal screenshot, measured dimensions and PIE results are recorded in [Docs/ASSET_IMPORT_VALIDATION.md](../../Docs/ASSET_IMPORT_VALIDATION.md).

Run PowerShell from the project root, with Unreal Editor closed for commandlet operations:

```powershell
./Tools/Unreal/Run-AssetPilot.ps1 -Mode plan
./Tools/Unreal/Run-AssetPilot.ps1 -Mode import
./Tools/Unreal/Run-AssetPilot.ps1 -Mode validate
./Tools/Unreal/Run-AssetPilot.ps1 -Mode reimport -Revision review02
./Tools/Unreal/Run-AssetPilot.ps1 -Mode pie
```

The launcher temporarily enables installed PythonScriptPlugin and EditorScriptingUtilities for that process. It does not change the project descriptor, default map, character or input assets. Set `-EngineRoot` if Unreal moves. In an already-running editor with those plugins enabled, execute `import_pilot.py` through Tools > Execute Python Script; its default is import. Close any unsaved edits to imported assets first.

## Non-destructive behavior

Imported packages live under `/Game/SakuraDays/Environment/Architecture/House01/Revisions/r_<fingerprint>` and `/Game/SakuraDays/Environment/Foliage/Sakura/Hero/Revisions/r_<fingerprint>`. Each revision contains its own named materials; the tree also contains the original blossom texture. Fingerprints include the FBX, texture when applicable and recipe version.

Unchanged owned assets are loaded and checked without being saved. Unknown existing packages cause a refusal. Changed sources or explicit `reimport` create a separate revision, leaving existing packages, edits and map references intact. This is a staged replacement workflow, not an in-place overwrite. Promote a reviewed revision into a production map separately. If a run fails after writing some new packages, those packages are preserved; use a fresh revision label to retry. Update the recipe version when changing import/material rules. No automatic deletion, asset moves, redirector cleanup or bulk processing occurs.

## Import and material rules

Static FBX import uses scene/unit conversion, Force Front X, scale 1, authored normals and generated MikkTSpace tangents. Blender -Y front becomes Unreal +X; +Z remains up. Existing UVs and vertex colors are preserved. Camera/light objects and Blender shader graphs are not imported.

House materials use eight matching named matte colors; window panels remain stylized opaque surfaces. The tree uses opaque vertex-tinted bark and a Masked, Two Sided Foliage blossom material. Atlas RGB is multiplied by vertex RGB, atlas alpha alone drives the mask at 0.4, and restrained pink subsurface color supports backlighting. Vertex alpha is reserved for future wind, not transparency. No wind or additional LOD import is included.

The house receives three simple boxes: a 600 × 800 × 590 cm closed exterior body and two entry steps. This is an exterior-only collision proxy; the balcony and roof are not tested walkable surfaces and no interior is accessible. The tree retains three authored UCX trunk hulls; blossoms do not block the player.

## Validation

`Saved/AssetImportPilot/latest.json` records actual package paths, source hashes, dimensions, ground pivot, triangle counts, render-normal checks, UV/material slots and collision counts. A failed check stops the pilot. Validate mode does not repair or overwrite existing assets.

`test_import_pilot.py` creates a uniquely named map under `/Game/SakuraDays/Maps/Validation/`, reuses the Third Person GameMode and tests genuine PIE with programmatic movement input and jumping. It checks the closed house facade, tree trunk and walkable space below the canopy. It writes `Saved/AssetImportPilot/pie_validation.json` and a real Unreal screenshot. The editor remains open afterward. This does not test keyboard bindings, packaging, all-angle normals, final art matching or performance. Inspect the screenshot and actual report before continuing with other assets.

The PIE script requires a passed import/validation report and refuses to switch maps while map packages have unsaved changes. Save or close those changes normally first; the script does not save unrelated work.

Sources: [Epic FBX import options](https://dev.epicgames.com/documentation/unreal-engine/fbx-import-options-reference-in-unreal-engine) and [shading models](https://dev.epicgames.com/documentation/unreal-engine/shading-models-in-unreal-engine). Actual compatibility is established with the installed UE 5.8.4, rather than assuming Blender FBX version numbers match Epic's exporter recommendation.
