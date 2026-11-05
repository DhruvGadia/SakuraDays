# SakuraDays technical plan

## Starting point

The project uses Unreal Engine 5.8.4 and the Third Person template. `/Game/ThirdPerson/Lvl_ThirdPerson` is the current editor and game default. Open the new milestone map explicitly during development so the existing startup flow is available as a fallback.

## Folder structure

| Path | Purpose |
|---|---|
| `sakuradays.uproject`, `Config/` | Project descriptor and shared Unreal settings. Track both. |
| `Content/ThirdPerson/`, `Content/Characters/`, `Content/Input/`, `Content/LevelPrototyping/` | Existing template, shared assets, and prototype content. |
| `Content/__ExternalActors__/`, `Content/__ExternalObjects__/` | Unreal-managed map packages. Track required files with the corresponding maps. |
| `Content/SakuraDays/Maps/` | Planned home for the milestone map `L_SakuraStreet`. |
| `Content/SakuraDays/Environment/`, `NPC/`, `UI/`, `VFX/` | Planned project-owned street and café assets, NPC Blueprint, dialogue widget, and petal effects. The latter three folders are also under `Content/SakuraDays/`. |
| `Docs/`, `.agents/skills/` | Development plans and project-scoped agent tooling. |
| `Binaries/`, `DerivedDataCache/`, `Intermediate/`, `Saved/` | Generated output and local editor state excluded from Git. |

Create planned content folders in the Unreal Content Browser as assets are added.

## Implementation

1. Create the milestone map and reuse the template’s player controller, character, camera, and movement mappings. Place the player start, route boundaries, café blockout, and NPC interaction point. Verify navigation and collision before adding art.
2. Add an NPC Blueprint with an interaction range. Reuse the project’s Enhanced Input setup where practical. Show the prompt within range and route the interact action to the nearby NPC.
3. Use a UMG widget with speaker name and text. Store a short ordered sequence of lines on the NPC for this milestone. Prevent concurrent conversations, support advance and close, and restore input and prompt state when dialogue ends.
4. Add sakura meshes and a Niagara emitter for drifting petals. Use a bounded effect around the playable route. Tune spawn rate, lifetime, and bounds from the player camera during Play In Editor.
5. Run a fresh Play In Editor test. Spawn, reach the café, enter and leave interaction range, complete and repeat dialogue, and confirm the street and petals read clearly during play.

## Source control

Install Git LFS on each development machine and run `git lfs pull` after cloning from an LFS-capable remote. Verify asset rules with `git lfs track` and check the assets in a checkpoint with `git lfs fsck`. Coordinate edits to shared binary assets before making changes on separate branches.
