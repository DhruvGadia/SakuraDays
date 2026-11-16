"""Prompt 13: real PIE traversal and fixed-camera evidence, without browser control.

Run with SAKURA_ANIME_REVIEW=before/pass1/pass2/pass3/references. Optionally set
SAKURA_ANIME_APPLY to the matching refine_anime_*.py entrypoint before validation.
Capture output stays in ignored .dream-loop/prompt13/<review>/.
"""
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'Tools/Unreal'
sys.path.insert(0, str(HERE))
LABEL = os.environ.get('SAKURA_ANIME_REVIEW', 'before')
if LABEL not in ('before', 'pass1', 'pass2', 'pass3', 'references'):
    raise ValueError('Unknown review label: ' + LABEL)
OUT = ROOT / '.dream-loop/prompt13' / LABEL
OUT.mkdir(parents=True, exist_ok=True)

apply_script = os.environ.get('SAKURA_ANIME_APPLY', '')
if apply_script:
    if apply_script not in tuple('refine_anime_pass%d.py' % n for n in (1, 2, 3)) + ('refine_anime_references.py',):
        raise ValueError('Only explicit Prompt 13 pass entrypoints are supported.')
    runpy.run_path(str(HERE / apply_script), run_name='__main__')

if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Unsaved map preserved; capture must validate the saved scene.')
MAP = '/Game/SakuraDays/Maps/L_SakuraStreet'
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    raise RuntimeError('Existing PIE session preserved.')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_path_name().split('.')[0] != MAP:
    assert level.load_level(MAP)

snapshot = {}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    p, r, s = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    item = {'class': actor.get_class().get_path_name(),
            'position': [p.x,p.y,p.z], 'rotation': [r.pitch,r.yaw,r.roll],
            'scale': [s.x,s.y,s.z]}
    if isinstance(actor, unreal.StaticMeshActor):
        component = actor.static_mesh_component
        item.update(mesh=component.static_mesh.get_path_name() if component.static_mesh else None,
                    collision_profile=str(component.get_collision_profile_name()),
                    collision_enabled=str(component.get_collision_enabled()),
                    materials=[m.get_path_name() if m else None for m in component.get_materials()])
    snapshot[actor.get_actor_label()] = item
map_file = ROOT / 'Content/SakuraDays/Maps/L_SakuraStreet.umap'
(OUT / 'scene_snapshot.json').write_text(json.dumps({
    'review': LABEL, 'map': MAP, 'actors': snapshot,
    'saved_map_sha256': hashlib.sha256(map_file.read_bytes()).hexdigest(),
    'target_sha256': hashlib.sha256((ROOT/'.dream-loop/target.png').read_bytes()).hexdigest(),
}, indent=2), encoding='utf-8')

# Keep the proven traversal and the eight review cameras identical across passes.
# Only redirect its output folder; do not edit the earlier validation harness.
source = (HERE / 'test_town_stage.py').read_text(encoding='utf-8')
old = "OUT=ROOT/'Saved/TownRefinement'/('PIE_'+STAGE);OUT.mkdir(parents=True,exist_ok=True)"
assert source.count(old) == 1, 'Town test adapter changed; inspect before use.'
source = source.replace(old, 'OUT=Path(' + repr(str(OUT)) + ');OUT.mkdir(parents=True,exist_ok=True)')
os.environ['SAKURA_TOWN_TEST_STAGE'] = 'final'
os.environ['SAKURA_TOWN_TEST_EXIT'] = '1'
exec(compile(source, str(HERE / 'test_town_stage.py'), 'exec'),
     {'__name__': '__main__', '__file__': str(HERE / 'test_town_stage.py')})
