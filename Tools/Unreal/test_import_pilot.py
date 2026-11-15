"""Real Play-in-Editor smoke test for the first house/tree imports.

Run in the full Unreal Editor with -ExecutePythonScript (not a commandlet).
Creates a new, uniquely named validation map; never changes project defaults.
Inputs: Saved/AssetImportPilot/latest.json with results.house/tree.asset paths.
Outputs: Saved/AssetImportPilot/pie_validation.json and a real 1920x1080 capture.
This tests the existing Third Person pawn with ordinary movement input and jump;
it does not automate keyboard/mouse input or claim a full manual playtest.
"""
import json
import math
import time
import traceback
import uuid
from pathlib import Path

import unreal
unreal.EditorPythonScripting.set_keep_python_script_alive(True)

OUT = Path(unreal.Paths.project_saved_dir()) / 'AssetImportPilot'
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / 'pie_validation.json'
RUN = time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]
MAP = '/Game/SakuraDays/Maps/Validation/L_AssetImportPilot_' + RUN
SCREENSHOT = OUT / ('AssetImportPilot_' + RUN + '.png')
STATE = {'run_id': RUN, 'map': MAP, 'status': 'preparing', 'passed': False,
         'checks': [], 'errors': [], 'samples': [], 'screenshot': str(SCREENSHOT),
         'test_scope': 'Genuine PIE using the existing possessed Third Person pawn; '
                       'programmatic movement input, jump, collision and screenshot. '
                       'No keyboard binding or packaged-build validation.'}
TICK_HANDLE = None
LEVEL = None
STARTED = time.monotonic()
PHASE_START = STARTED
PHASE = 'startup'
ROUTE_INDEX = 0
LAST_SAMPLE = 0.0
COLLISION_SAMPLES = []
JUMP_BASE = None
JUMP_MAX = None
PLAYER_SEEN = False

# All coordinates are centimeters. House front is +X after Force Front X import.
ROUTE = [
    ('movement_warmup', (800., 0.), 25., None),
    ('house_facade_blocks', (0., 0.), 4.5, 'house'),
    ('leave_house', (650., 0.), 8., None),
    ('walk_to_tree', (650., 1150.), 12., None),
    ('tree_trunk_blocks', (0., 1150.), 4.5, 'tree'),
    ('leave_tree', (230., 1150.), 8., None),
    ('canopy_walk_north', (230., 1450.), 8., None),
    ('canopy_walk_south', (230., 850.), 10., None),
    ('jump_start', (450., 850.), 8., None),
]


def write_report():
    STATE['elapsed_seconds'] = round(time.monotonic() - STARTED, 3)
    REPORT.write_text(json.dumps(STATE, indent=2), encoding='utf-8')


def check(name, passed, **details):
    STATE['checks'].append(dict(name=name, passed=bool(passed), **details))
    if not passed:
        STATE['errors'].append(name + ' failed')
    unreal.log('ASSET_PILOT_PIE_CHECK ' + name + ': ' + str(bool(passed)))
    write_report()


def stop(status, error=None):
    global TICK_HANDLE
    if error:
        STATE['errors'].append(str(error))
    STATE['status'] = status
    STATE['passed'] = status == 'complete' and not STATE['errors']
    write_report()
    if TICK_HANDLE is not None:
        unreal.unregister_slate_post_tick_callback(TICK_HANDLE)
        TICK_HANDLE = None
    if LEVEL and LEVEL.is_in_play_in_editor():
        LEVEL.editor_request_end_play()
    unreal.log('ASSET_PILOT_PIE_FINISHED ' + json.dumps({
        'passed': STATE['passed'], 'report': str(REPORT), 'errors': STATE['errors']}))
    # Leave the editor and validation map available for inspection. Never quit an
    # editor that might contain unrelated unsaved work; do not save a PIE world.


def spawn_mesh(actors, label, mesh, location, scale=(1., 1., 1.)):
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*location))
    actor.set_actor_label(label)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name('BlockAll')
    actor.set_actor_scale3d(unreal.Vector(*scale))
    return actor


def setup():
    global LEVEL, PHASE, PHASE_START, TICK_HANDLE
    report = json.loads((OUT / 'latest.json').read_text(encoding='utf-8'))
    if not report.get('passed') or report.get('errors') or report.get('mode') == 'plan':
        raise RuntimeError('A passed import/validation report is required; refusing to run PIE')
    imported = report['results']
    house_path = imported['house']['asset']
    tree_path = imported['tree']['asset']
    for path in (house_path, tree_path):
        if not path.startswith('/Game/SakuraDays/'):
            raise RuntimeError('Unexpected asset destination: ' + path)
    house = unreal.load_asset(house_path)
    tree = unreal.load_asset(tree_path)
    if not isinstance(house, unreal.StaticMesh) or not isinstance(tree, unreal.StaticMesh):
        raise RuntimeError('House/tree import must resolve to StaticMesh assets')
    LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if LEVEL is None or LEVEL.is_in_play_in_editor():
        raise RuntimeError('Full editor must be available and outside PIE')
    dirty_maps = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty_maps:
        raise RuntimeError('Unsaved map changes preserved. Save or close them normally before '
                           'running the pilot: ' + ', '.join(p.get_path_name() for p in dirty_maps))
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError('Validation map already exists; refusing to replace it')
    if not unreal.EditorLevelLibrary.new_level_from_template(MAP, '/Engine/Maps/Templates/Template_Default'):
        raise RuntimeError('Could not create new isolated validation map')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # These actors are freshly copied into our unique new map, not existing game
    # actors. Keep the template daylight/sky and replace only its test geometry.
    for actor in actors.get_all_level_actors():
        if isinstance(actor, (unreal.StaticMeshActor, unreal.PlayerStart)):
            actors.destroy_actor(actor)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    game_mode = unreal.load_class(None, '/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C')
    if game_mode is None:
        raise RuntimeError('Existing Third Person GameMode is unavailable')
    world.get_world_settings().set_editor_property('default_game_mode', game_mode)
    cube = unreal.load_asset('/Engine/BasicShapes/Cube')
    spawn_mesh(actors, 'PILOT_Ground', cube, (0, 550, -25), (45, 38, .5))
    house_actor = spawn_mesh(actors, 'PILOT_House', house, (0, 0, 0))
    tree_actor = spawn_mesh(actors, 'PILOT_SakuraHero', tree, (0, 1150, 0))
    start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(650, 0, 110),
                                         unreal.Rotator(pitch=0, yaw=180, roll=0))
    start.set_actor_label('PILOT_PlayerStart')
    camera = actors.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(1900, 2100, 1050))
    camera.set_actor_label('PILOT_ReferenceCamera')
    camera.set_editor_property('tags', ['SakuraDaysImportPilotCamera'])
    camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
        camera.get_actor_location(), unreal.Vector(0, 550, 330)), False)
    camera.camera_component.set_editor_property('field_of_view', 58.)
    camera.camera_component.set_editor_property('aspect_ratio', 1920 / 1080)
    camera.camera_component.set_editor_property('constrain_aspect_ratio', True)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(), camera.get_actor_rotation())
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError('Could not save the new validation map')
    STATE['assets'] = {'house': house_path, 'tree': tree_path}
    STATE['placements_cm'] = {'house': [0, 0, 0], 'tree': [0, 1150, 0], 'player_start': [650, 0, 110]}
    house_scale = house_actor.get_actor_scale3d()
    tree_scale = tree_actor.get_actor_scale3d()
    STATE['actor_scale'] = {'house': [house_scale.x, house_scale.y, house_scale.z],
                            'tree': [tree_scale.x, tree_scale.y, tree_scale.z]}
    STATE['status'] = 'waiting_for_viewport'
    PHASE = 'request_pie'
    PHASE_START = time.monotonic()
    write_report()
    TICK_HANDLE = unreal.register_slate_post_tick_callback(tick)


def tick(delta):
    global PHASE, PHASE_START, ROUTE_INDEX, LAST_SAMPLE, COLLISION_SAMPLES
    global JUMP_BASE, JUMP_MAX, PLAYER_SEEN
    try:
        now = time.monotonic()
        age = now - PHASE_START
        if now - STARTED > 180:
            stop('failed', 'Timed out waiting for editor/PIE progress')
            return
        if PHASE == 'request_pie':
            if age > 3:
                LEVEL.editor_request_begin_play()
                PHASE = 'wait_for_pawn'
                PHASE_START = now
                STATE['status'] = 'starting_pie'
                write_report()
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn:
            if PLAYER_SEEN:
                stop('failed', 'PIE ended before validation completed')
            elif age > 35:
                stop('failed', 'PIE did not spawn a possessed player; ensure a visible editor viewport')
            return
        PLAYER_SEEN = True
        p = pawn.get_actor_location()
        if now - LAST_SAMPLE > .15:
            STATE['samples'].append([round(p.x, 2), round(p.y, 2), round(p.z, 2),
                                     bool(pawn.character_movement.is_falling())])
            LAST_SAMPLE = now
        if PHASE == 'wait_for_pawn':
            if age > 2 and not pawn.character_movement.is_falling():
                check('existing_player_possessed', LEVEL.is_in_play_in_editor() and pawn.is_player_controlled(),
                      pawn_class=pawn.get_class().get_path_name(), world=world.get_path_name())
                PHASE = 'route'
                PHASE_START = now
                STATE['status'] = 'running_pie'
            return
        if PHASE == 'route':
            name, goal, limit, collision = ROUTE[ROUTE_INDEX]
            dx, dy = goal[0] - p.x, goal[1] - p.y
            distance = math.hypot(dx, dy)
            if collision and age > 2.5:
                COLLISION_SAMPLES.append((p.x, p.y))
            done = (collision is None and distance < 25) or age > limit
            if done:
                if collision:
                    drift = math.dist(COLLISION_SAMPLES[0], COLLISION_SAMPLES[-1]) if len(COLLISION_SAMPLES) > 2 else 9999
                    if collision == 'house':
                        passed = 300 < p.x < 510 and abs(p.y) < 50 and drift < 12
                    else:
                        passed = 30 < distance < 130 and drift < 12
                    check(name, passed, position_cm=[p.x, p.y, p.z], distance_to_goal_cm=distance,
                          final_position_drift_cm=drift, duration_seconds=age)
                else:
                    check(name, distance < 25, position_cm=[p.x, p.y, p.z],
                          distance_to_goal_cm=distance, duration_seconds=age)
                pawn.character_movement.stop_movement_immediately()
                ROUTE_INDEX += 1
                COLLISION_SAMPLES = []
                PHASE_START = now
                if ROUTE_INDEX >= len(ROUTE):
                    PHASE = 'jump'
                    JUMP_BASE = p.z
                    JUMP_MAX = p.z
                    pawn.jump()
                return
            if distance > .1:
                pawn.add_movement_input(unreal.Vector(dx / distance, dy / distance, 0), min(1., distance / 100))
        elif PHASE == 'jump':
            JUMP_MAX = max(JUMP_MAX, p.z)
            if age > .25:
                pawn.stop_jumping()
            if age > 1.5 and not pawn.character_movement.is_falling():
                check('jump_and_land', JUMP_MAX - JUMP_BASE > 40 and abs(p.z - JUMP_BASE) < 8,
                      jump_height_cm=JUMP_MAX - JUMP_BASE, landing_error_cm=abs(p.z - JUMP_BASE))
                controller = unreal.GameplayStatics.get_player_controller(world, 0)
                cameras = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor)
                cam = next(a for a in cameras if a.actor_has_tag('SakuraDaysImportPilotCamera'))
                controller.set_view_target_with_blend(cam, 0.)
                PHASE = 'settle_capture'
                PHASE_START = now
            elif age > 6:
                check('jump_and_land', False, detail='Did not land within six seconds')
                stop('failed')
        elif PHASE == 'settle_capture' and age > 4:
            unreal.SystemLibrary.execute_console_command(world, 'HighResShot 1920x1080 filename="' + str(SCREENSHOT).replace('\\', '/') + '"')
            PHASE = 'capture'
            PHASE_START = now
        elif PHASE == 'capture' and age > 4:
            captured = SCREENSHOT.exists() and SCREENSHOT.stat().st_size > 1000
            check('real_unreal_screenshot', captured, file=str(SCREENSHOT))
            stop('complete')
    except Exception:
        stop('failed', traceback.format_exc())


try:
    setup()
except Exception:
    stop('failed', traceback.format_exc())
