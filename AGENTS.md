# Working on SakuraDays

SakuraDays is a Blueprint-first Unreal Engine 5.8 project. The first milestone is a playable sakura-lined Japanese street with a café, one NPC, a short conversation, and falling petals. See [the roadmap](Docs/ROADMAP.md) and [the technical plan](Docs/TECHNICAL_PLAN.md).

## Project rules

- Preserve the existing Third Person map, templates, input assets, and shared content. Build the milestone in a separate map and keep it under `Content/SakuraDays/`.
- Use Unreal Editor for asset operations so references stay valid. Ask before destructive asset changes, broad moves, or changing the project’s default map.
- Prefer Blueprints and existing input, character, and camera behavior. Add a dependency or C++ only when a concrete requirement calls for it and the project owner agrees.
- Save only the assets touched by the task. Test changes in Play In Editor and report which map and interactions were exercised.
- Use Git LFS for `.uasset`, `.umap`, and `.blend`. Commit required external actor and object packages alongside their map changes. Keep generated caches, logs, and local Dream Loop output out of commits.
- Review `git status` before staging. Keep checkpoints focused and preserve unrelated work. Confirm before pushing or rewriting history.
