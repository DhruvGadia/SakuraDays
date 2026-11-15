"""Read-only saved-level verification for the assembled SakuraDays street.

Run using UnrealEditor-Cmd -run=pythonscript -script=... . No assets or levels
are modified or saved. The sole output is Saved/StreetAssembly/saved_validation.json.
"""
import json
import math
import traceback
from collections import Counter
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
assert Path(unreal.Paths.project_dir()).resolve() == ROOT, 'Unexpected project'
OUT = ROOT / 'Saved/StreetAssembly'
OUT.mkdir(parents=True, exist_ok=True)
MAP = '/Game/SakuraDays/Maps/L_SakuraStreet'
REPORT = dict(map=MAP, passed=False, errors=[], checks=[], protected={},
              physical_surfaces={}, imported_actors={}, tree_meshes={})
SM = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()


def check(name, passed, **details):
    REPORT['checks'].append(dict(name=name, passed=bool(passed), **details))
    if not passed:
        REPORT['errors'].append(name)


def xyz(v):
    return [v.x, v.y, v.z]


def transform(actor):
    p, r, s = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]


def near(actual, expected, tolerance=.001):
    return (len(actual) == len(expected)
            and all(math.isfinite(a) and abs(a-e) <= tolerance for a,e in zip(actual,expected)))


def physical(actor):
    comp = actor.static_mesh_component
    mesh = comp.static_mesh
    origin, extent = actor.get_actor_bounds(False)
    return dict(transform=transform(actor), mesh=mesh.get_path_name() if mesh else None,
                collision_profile=str(comp.get_collision_profile_name()),
                collision_enabled=str(comp.get_collision_enabled()),
                collision_object_type=str(comp.get_collision_object_type()),
                pawn_response=str(comp.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)),
                query_collision=comp.is_query_collision_enabled(),
                actor_collision=actor.get_actor_enable_collision(),
                world_bounds_origin_cm=xyz(origin), world_bounds_extent_cm=xyz(extent),
                bounds_min_cm=[o-e for o,e in zip(xyz(origin),xyz(extent))],
                bounds_max_cm=[o+e for o,e in zip(xyz(origin),xyz(extent))],
                simple_collision_shapes=SM.get_simple_collision_count(mesh) if mesh else 0,
                convex_hulls=SM.get_convex_collision_count(mesh) if mesh else 0,
                materials=[comp.get_material(i).get_path_name() if comp.get_material(i) else None
                           for i in range(comp.get_num_materials())])


try:
    assembly = json.loads((OUT/'assembly.json').read_text(encoding='utf-8'))
    if not assembly.get('passed') or assembly.get('errors'):
        raise RuntimeError('A passed assembly report is required.')
    headless = '-run=' in unreal.SystemLibrary.get_command_line().lower()
    level = None if headless else unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('Refusing to load a level during PIE.')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Unsaved map changes preserved; run in a clean commandlet.')
    loaded = level.load_level(MAP) if level else unreal.EditorLevelLibrary.load_level(MAP)
    if not loaded:
        raise RuntimeError('Unable to load saved street map.')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    check('correct_loaded_map', world.get_path_name().split('.')[0] == MAP,
          loaded_world=world.get_path_name())
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    counts = Counter(a.get_actor_label() for a in actors)
    duplicates = sorted(label for label,count in counts.items() if label.startswith('SD_') and count>1)
    check('no_duplicate_assembly_labels', not duplicates, duplicate_labels=duplicates)
    by_label = {a.get_actor_label():a for a in actors}
    REPORT['actor_count'] = len(actors)
    placeholders = sorted(n for n in by_label
                          if n.startswith(('GB_Cafe_','GB_Tree'))
                          or (n.startswith('GB_House') and not n.endswith('_Plot')))
    check('graybox_building_tree_placeholders_replaced', not placeholders, remaining=placeholders)
    for label, expected in assembly['protected_before'].items():
        actor = by_label.get(label)
        actual = transform(actor) if actor else []
        REPORT['protected'][label] = actual
        check('protected_transform_'+label, near(actual,expected), expected=expected, actual=actual)

    camera = by_label.get('CAM_SakuraStreet_Reference')
    if not isinstance(camera,unreal.CameraActor):
        raise RuntimeError('Fixed reference camera is missing.')
    c = camera.camera_component
    REPORT['reference_camera'] = dict(transform=transform(camera),
        projection_mode=str(c.get_editor_property('projection_mode')),
        horizontal_fov=c.get_editor_property('field_of_view'),
        aspect_ratio=c.get_editor_property('aspect_ratio'),
        constrain_aspect_ratio=c.get_editor_property('constrain_aspect_ratio'),
        auto_activate_for_player=str(camera.get_editor_property('auto_activate_for_player')))
    cam = REPORT['reference_camera']
    check('exact_reference_camera', near(cam['transform'],[-480,-180,210,-4,-7,0,1,1,1],.001)
          and abs(cam['horizontal_fov']-75)<.001 and abs(cam['aspect_ratio']-16/9)<.001
          and cam['constrain_aspect_ratio'])

    surfaces = ['Prototype_Ground','Prototype_Road','Prototype_LeftSidewalk','Prototype_RightSidewalk',
                'Prototype_LeftBoundary','Prototype_RightBoundary','Prototype_FarBoundary','Prototype_NearBoundary']
    before_file = OUT/'before.json'
    original = {a['label']:a for a in json.loads(before_file.read_text(encoding='utf-8'))} if before_file.exists() else {}
    for label in surfaces:
        actor = by_label.get(label)
        if not isinstance(actor,unreal.StaticMeshActor):
            check('surface_present_'+label,False)
            continue
        data = physical(actor)
        REPORT['physical_surfaces'][label] = data
        comp = actor.static_mesh_component
        blocking = (data['collision_profile']=='BlockAll' and data['query_collision']
                    and data['actor_collision'] and comp.get_collision_response_to_channel(
                     unreal.CollisionChannel.ECC_PAWN)==unreal.CollisionResponseType.ECR_BLOCK
                    and data['simple_collision_shapes']+data['convex_hulls']>0)
        check('blocking_surface_'+label,blocking)
        if label in original:
            old = original[label]
            check('original_surface_transform_'+label,near(data['transform'],old['pos']+old['rot']+old['scale']))
    for label, expected_height in [('Prototype_Road',0),('Prototype_LeftSidewalk',15),('Prototype_RightSidewalk',15)]:
        data = REPORT['physical_surfaces'].get(label)
        check('surface_height_'+label,bool(data) and abs(data['bounds_max_cm'][2]-expected_height)<.1)

    for placed in assembly['placed']:
        label = placed['label']
        actor = by_label.get(label)
        actual_path = actor.static_mesh_component.static_mesh.get_path_name() if isinstance(actor,unreal.StaticMeshActor) and actor.static_mesh_component.static_mesh else None
        check('placed_asset_'+label,actual_path==placed['asset'],expected=placed['asset'],actual=actual_path)
        if actual_path and actual_path.startswith('/Game/SakuraDays/'):
            comp = actor.static_mesh_component
            REPORT['imported_actors'][label] = dict(asset=actual_path,transform=transform(actor),
                                                   collision_profile=str(comp.get_collision_profile_name()))
            check('imported_placement_'+label,near(xyz(actor.get_actor_location()),placed['position_cm'])
                  and near(xyz(actor.get_actor_scale3d()),placed['scale'])
                  and abs((actor.get_actor_rotation().yaw-placed['yaw']+180)%360-180)<.001)
        if label.startswith('SD_Sakura_') and actual_path:
            mesh = actor.static_mesh_component.static_mesh
            if actual_path not in REPORT['tree_meshes']:
                count = SM.get_convex_collision_count(mesh)
                mats = list(mesh.static_materials)
                blossom = next((m.material_interface for m in mats if str(m.material_slot_name)=='M_Sakura_Blossom'),None)
                info = dict(convex_trunk_hulls=count,material_slots=[str(m.material_slot_name) for m in mats])
                check('tree_ucx_'+mesh.get_name(),count>0)
                if isinstance(blossom,unreal.Material):
                    info.update(blossom_two_sided=blossom.get_editor_property('two_sided'),
                                blossom_blend_mode=str(blossom.get_editor_property('blend_mode')),
                                blossom_shading_model=str(blossom.get_editor_property('shading_model')))
                    check('tree_masked_material_'+mesh.get_name(),info['blossom_two_sided']
                          and blossom.get_editor_property('blend_mode')==unreal.BlendMode.BLEND_MASKED)
                else:
                    check('tree_blossom_material_'+mesh.get_name(),False)
                REPORT['tree_meshes'][actual_path] = info
    REPORT['passed'] = not REPORT['errors']
except Exception:
    REPORT['errors'].append(traceback.format_exc())
    REPORT['passed'] = False

(OUT/'saved_validation.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
unreal.log('STREET_SAVED_VALIDATION '+json.dumps(dict(passed=REPORT['passed'],errors=REPORT['errors'])))
if not REPORT['passed']:
    raise RuntimeError('Saved street verification failed; inspect Saved/StreetAssembly/saved_validation.json')
