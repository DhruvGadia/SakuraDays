# SakuraDays street assembly

This workflow replaces the known building and tree placeholders in `/Game/SakuraDays/Maps/L_SakuraStreet` with the approved source-art kits. It preserves the existing road, sidewalks, boundaries, player spawn, Third Person controls and fixed reference camera. It does not change the project default map.

See [the completed scene and visual comparison](../../Docs/STREET_ASSEMBLY.md) for permanent screenshots and validation evidence.

## Run the workflow

Run PowerShell from the SakuraDays project root. Close Unreal Editor normally first, saving any unrelated work. The launcher refuses to start while an `UnrealEditor` or `UnrealEditor-Cmd` process is already running. All commandlet modes check exit code, report freshness and the report's `passed` field.

```powershell
# Default: inspect existing imported revisions; no asset repairs or replacements.
./Tools/Unreal/Run-StreetScene.ps1

# Preview the import destinations without creating assets.
./Tools/Unreal/Run-StreetScene.ps1 -Mode plan

# Import missing approved assets, or reuse matching owned revisions.
./Tools/Unreal/Run-StreetScene.ps1 -Mode import

# Update and save L_SakuraStreet with the repeatable placement recipe.
./Tools/Unreal/Run-StreetScene.ps1 -Mode assemble

# Launch the full editor, exercise PIE, then capture both cameras.
./Tools/Unreal/Run-StreetScene.ps1 -Mode test
```

Use `-EngineRoot 'C:\Program Files\Epic Games\UE_5.8'` if needed. The launcher temporarily enables the installed Python and Editor Scripting Utilities plugins for the process; it does not edit the project descriptor.

The `test` mode is asynchronous and leaves the editor open. A launched editor is not a passed test. Keep the viewport available and wait for a fresh `Saved/StreetAssembly/pie_validation.json` with `status: complete`, `passed: true` and an empty `errors` list. The test refuses unsaved map changes and an already-running PIE session. It does not save a level.

## Approved imports

[import_street_assets.py](import_street_assets.py) supplies 13 placement keys:

| Keys | Assets |
| --- | --- |
| `house`, `tree_hero` | Existing reviewed pilot house and hero sakura; packages are reused without writes |
| `cafe` | HANA assembled café exterior, including its original furniture and signage |
| `chair`, `table`, `bench`, `lamp`, `pot`, `planter`, `ac`, `menu` | Individual approved café-kit props for additional street dressing |
| `tree_spread`, `tree_weeping` | Two additional sakura forms, LOD0 |

Do not duplicate the independent furnishings at the exact locations already present in the assembled café. Its street-facing furniture extends beyond the building shell and is included in its bounds and collision setup.

New assets are organized under `Content/SakuraDays/Environment/Architecture/Cafe01`, `Environment/Props/Cafe01` and `Environment/Foliage/Sakura`. Every mesh revision has a source/recipe fingerprint. Café materials use their source names and palette, while tree variations reuse the reviewed hero's bark/blossom materials.

Identical imports are checked without saving the existing packages. Changed source hashes or an explicit new revision label create sibling packages. Existing packages, manual edits and references remain intact. Unknown destination assets cause a refusal. A failed run may leave newly created packages; it does not delete them.

```powershell
# Create a separate review revision, then inspect its import report.
./Tools/Unreal/Run-StreetScene.ps1 -Mode import -Revision review02
./Tools/Unreal/Run-StreetScene.ps1 -Mode validate -Revision review02
```

The scene recipe consumes the asset paths in the latest successful `Saved/StreetAssembly/imports.json`. To place a new review revision, run its import/validation first, then assemble. A `plan` report is deliberately rejected by assembly; run `import` or `validate` after planning. The PIE script tests the level currently saved on disk, so finish assembly before using it as evidence of the dressed scene.

## Repeatable scene placement and backup

[assemble_street_scene.py](assemble_street_scene.py) updates the existing `L_SakuraStreet` map through Unreal Editor APIs. Before editing, it preserves the map file under:

```text
Saved/StreetAssembly/Backups/L_SakuraStreet_<pre-edit SHA256 prefix>.umap
```

The exact backup path is recorded in `Saved/StreetAssembly/assembly.json`. Backups are retained, not automatically restored or deleted. They are local recovery copies under ignored `Saved`; keep normal Git/LFS checkpoints for durable history. The recipe does not reset Git or overwrite the Third Person map.

The recipe recognizes only the earlier named graybox placeholders for removal. New scene actors have labels beginning `SD_`, the tag `SakuraDaysStreetAssembly`, and Outliner folders beneath `SakuraDays/`. Re-running updates matching tagged actors, creates missing ones, and removes obsolete actors bearing that same tag. Untagged actors with conflicting names cause a refusal rather than being adopted or overwritten. Do not manually edit generated actors expecting a later recipe run to preserve those edits; update the script's placement recipe instead. Keep separately authored content untagged and uniquely named.

Road, sidewalk, spawn and camera transforms are recorded before and after assembly and checked for equality. Road and sidewalk material dressing can change while their playable geometry remains in place. The fixed `CAM_SakuraStreet_Reference` keeps its approved transform, 75-degree horizontal field of view and constrained 16:9 framing. Ordinary PIE continues to use the existing Third Person camera.

## Collision and test coverage

The café has a closed building proxy plus ten local furnishing/container proxies, leaving terrace gaps open. It has no playable interior or opening door. Independent plants block their containers instead of their foliage. The lamp blocks its pole/base. House collision remains the pilot's exterior/entry-step proxy. All three trees use three UCX trunk hulls and nonblocking blossoms.

[test_street_scene.py](test_street_scene.py) runs genuine PIE with the existing Third Person pawn. It supplies normal pawn movement input through the Python API, navigates both sidewalks and the road, approaches the café and house frontages, crosses at both ends, returns to spawn, and jumps. It captures gameplay first and then changes only the PIE view target to the fixed reference camera. It restores the pawn view when stopping. It does not replace input assets, teleport the pawn or save a PIE world.

Local reports and captures:

```text
Saved/StreetAssembly/imports.json
Saved/StreetAssembly/assembly.json
Saved/StreetAssembly/pie_validation.json
Saved/StreetAssembly/Gameplay.png
Saved/StreetAssembly/Reference.png
```

Both captures are real Unreal renders requested at 1920 × 1080. Inspect fresh files and report results before claiming success. These checks do not establish keyboard bindings, NPC pathfinding, interiors, all-angle shading, packaging or performance. Tree LOD chains and wind remain separate integration work.

No workflow mode commits or pushes. Before a checkpoint, review `git status` and include the touched map and required asset packages under the existing Git LFS rules. Keep `Saved`, logs, caches and unrelated work out of the checkpoint.
