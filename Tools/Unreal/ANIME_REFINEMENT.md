# Prompt 13 Unreal Dream Loop workflow

This workflow runs the installed Dream Loop Plus loop against the existing
`/Game/SakuraDays/Maps/L_SakuraStreet`. It uses Unreal Python and genuine PIE
`HighResShot` captures. It does not use browser automation to control Unreal.

The locked visual target is `.dream-loop/target.png`, whose permanent copy is
`References/SakuraDays_First_Street_Target.png`. Style A and Style B remain the
primary art authorities. Preserve the target while comparing iterations.

## Capture or apply a pass

Save intentional editor work and close Unreal normally first. The runner refuses
to start another editor alongside an existing instance. From the project root:

```powershell
# Capture and test the unchanged saved scene.
& ./Tools/Unreal/Run-AnimeReview.ps1 -Review before

# Apply the named refinement, save its touched assets/map, then test and capture.
& ./Tools/Unreal/Run-AnimeReview.ps1 -Review pass1 -Apply
& ./Tools/Unreal/Run-AnimeReview.ps1 -Review pass2 -Apply
& ./Tools/Unreal/Run-AnimeReview.ps1 -Review pass3 -Apply
```

Omit `-Apply` to capture/test the currently saved map without reapplying a recipe.
The review label is an output location, not a command to restore an earlier map.
Rerunning a label replaces that label's local evidence, so retain important
captures before rerunning. `-EngineRoot` can override the local UE 5.8 installation.

Historical pass reproduction requires the pre-refinement scene in a separate
checkout plus these scripts, applied in order. The scripts are forward art
recipes, not rollback commands: higher-priority grade volumes from later passes
remain present if an earlier script is rerun over the finished map.

Each authoring script should be run only after reviewing its parameters. Recipes
own their lighting and material overrides; they do not merge subsequent manual
art changes. Source materials and original project assets remain intact. No
default-map, character/input or project plugin changes are needed.

## What is verified

- The normal saved map opens in a full rendering editor.
- The original Third Person pawn is possessed, traverses 17 route waypoints,
  jumps and lands using real movement input calls rather than teleportation.
- The approved fixed reference camera is preserved.
- Eight PNG files per run have actual 1920 × 1080 headers.
- Two samples read the live Niagara simulation: particle count, dimensions,
  height, downward velocity and matched-ID motion.
- The runner checks editor exit status and fresh completed validation evidence.
- `publish_anime_evidence.py` compares geometry, collision, camera and spawn
  snapshots across the baseline and all three passes, checks the final saved-map
  hash, and retains selected original PNG bytes and sanitized reports in `Docs`.

Capture output lives under ignored `.dream-loop/prompt13/<review>/` and authoring
readbacks/backups under ignored `Saved/AnimeRefinement/<pass>/`. The final evidence
copy is local; the script never publishes to GitHub or another service.

The tests do not establish physical keyboard bindings, every possible collision
approach, a packaged build, GPU frame time or a guaranteed 60 fps result. Compare
lighting and colors visually at identical cameras; animated clouds, wind and
particles mean pixel-perfect image differences are not a quality score.

Do not run earlier street assembly/Prompt 12 placement or lighting recipes over
the refined map unless intentionally restoring those parameter choices. A later
art pass should use new derived assets and a fresh local checkpoint.
