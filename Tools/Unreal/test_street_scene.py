"""Genuine PIE navigation and two-camera capture for L_SakuraStreet.

Run in the full Unreal Editor with Python enabled, outside PIE and with map
changes saved. This script never saves a level, teleports the pawn, replaces
input assets, or alters the fixed camera. Screenshots and results are local
generated evidence under Saved/StreetAssembly.
"""
import json
import math
import struct
import time
import traceback
from pathlib import Path

import unreal

unreal.EditorPythonScripting.set_keep_python_script_alive(True)
MAP = '/Game/SakuraDays/Maps/L_SakuraStreet'
OUT = (Path(unreal.Paths.project_saved_dir()) / 'StreetAssembly').resolve()
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / 'pie_validation.json'
STARTED = time.monotonic()
STATE = dict(map=MAP, status='preparing', passed=False, checks=[], errors=[],
             samples=[], distance_cm=0., screenshots={},
             test_scope='Genuine PIE; existing Third Person pawn, movement-input '
                        'API and jump. No keyboard-binding, NPC navigation, '
                        'packaging or performance validation.')
LEVEL = None
HANDLE = None
OWNS_PIE = False
PHASE = 'startup'
PHASE_START = STARTED
ROUTE_INDEX = 0
LAST_SAMPLE = 0.
LAST_POSITION = None
PLAYER_SEEN = False
JUMP_BASE = None
JUMP_MAX = None
CAPTURE_STARTED_NS = None
CAPTURE_BEFORE = None
REFERENCE = None

# +X follows the street. These lanes preserve the graybox walkable corridors.
# The final approach faces +X at spawn, matching the reference composition.
ROUTE = [
    ('movement_warmup', (140., -320.), 25.),
    ('cafe_approach', (350., -380.), 10.),
    ('left_near', (1000., -330.), 12.),
    ('left_middle', (2300., -330.), 12.),
    ('left_far', (4600., -330.), 15.),
    ('far_crossing', (4600., 600.), 12.),
    ('house03_frontage', (3300., 600.), 12.),
    ('right_middle', (2300., 600.), 12.),
    ('house02_frontage', (1100., 600.), 12.),
    ('right_near', (-500., 600.), 15.),
    ('near_road_crossing', (-500., 150.), 10.),
    ('road_middle', (2000., 150.), 18.),
    ('road_far', (4500., 150.), 18.),
    ('road_return', (-500., 150.), 25.),
    ('near_sidewalk_crossing', (-500., -330.), 10.),
    ('spawn_approach', (-160., -320.), 10.),
    ('return_spawn', (0., -320.), 10.),
]


def write_report():
    STATE['elapsed_seconds'] = round(time.monotonic() - STARTED, 3)
    REPORT.write_text(json.dumps(STATE, indent=2), encoding='utf-8')


def check(name, passed, **details):
    STATE['checks'].append(dict(name=name, passed=bool(passed), **details))
    if not passed:
        STATE['errors'].append(name + ' failed')
    unreal.log('STREET_PIE_CHECK ' + name + ': ' + str(bool(passed)))
    write_report()


def stop(status, error=None):
    global HANDLE
    if error:
        STATE['errors'].append(str(error))
    STATE['status'] = status
    STATE['passed'] = status == 'complete' and not STATE['errors']
    write_report()
    if HANDLE is not None:
        unreal.unregister_slate_post_tick_callback(HANDLE)
        HANDLE = None
    # Never terminate an unrelated existing PIE session when setup refuses.
    if OWNS_PIE and LEVEL and LEVEL.is_in_play_in_editor():
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if world:
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            if pawn and controller:
                pawn.character_movement.stop_movement_immediately()
                controller.set_view_target_with_blend(pawn, 0.)
        LEVEL.editor_request_end_play()
    unreal.log('STREET_PIE_FINISHED ' + json.dumps(dict(
        passed=STATE['passed'], report=str(REPORT), errors=STATE['errors'])))


def setup():
    global LEVEL, HANDLE, PHASE, PHASE_START
    LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if LEVEL is None or LEVEL.is_in_play_in_editor():
        raise RuntimeError('Run in a full editor outside PIE.')
    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty:
        raise RuntimeError('Unsaved map changes preserved; save/close normally first: '
                           + ', '.join(p.get_path_name() for p in dirty))
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP):
        raise RuntimeError('Expected street map does not exist: ' + MAP)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0] != MAP:
        if not LEVEL.load_level(MAP):
            raise RuntimeError('Unable to load the saved street map.')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    cameras = [a for a in actors if isinstance(a, unreal.CameraActor)
               and a.get_actor_label() == 'CAM_SakuraStreet_Reference']
    if len(cameras) != 1:
        raise RuntimeError('Expected exactly one CAM_SakuraStreet_Reference.')
    cam = cameras[0]
    p, r = cam.get_actor_location(), cam.get_actor_rotation()
    fov = cam.camera_component.get_editor_property('field_of_view')
    aspect = cam.camera_component.get_editor_property('aspect_ratio')
    fixed_ok = (max(abs(a-b) for a,b in zip((p.x,p.y,p.z),(-480.,-180.,210.))) < .1
                and max(abs(a-b) for a,b in zip((r.pitch,r.yaw,r.roll),(-4.,-7.,0.))) < .01
                and abs(fov-75.) < .01 and abs(aspect-16/9) < .001)
    check('reference_camera_preserved', fixed_ok,
          position_cm=[p.x,p.y,p.z], rotation_degrees=[r.pitch,r.yaw,r.roll],
          horizontal_fov=fov, aspect_ratio=aspect)
    if not fixed_ok:
        raise RuntimeError('Reference camera differs from the approved graybox transform.')
    STATE['reference_actor_name'] = cam.get_name()
    STATE['status'] = 'waiting_for_viewport'
    PHASE = 'request_pie'
    PHASE_START = time.monotonic()
    write_report()
    HANDLE = unreal.register_slate_post_tick_callback(tick)


def capture(world, name):
    global CAPTURE_STARTED_NS, CAPTURE_BEFORE
    path = OUT / (name + '.png')
    CAPTURE_BEFORE = (path.stat().st_mtime_ns, path.stat().st_size) if path.exists() else None
    CAPTURE_STARTED_NS = time.time_ns()
    unreal.SystemLibrary.execute_console_command(
        world, 'HighResShot 1920x1080 filename="' + path.as_posix() + '"')
    STATE['screenshots'][name.lower()] = str(path)
    write_report()


def capture_finished(name):
    path = OUT / (name + '.png')
    if not path.exists() or path.stat().st_size < 1000:
        return False
    st = path.stat()
    if CAPTURE_BEFORE == (st.st_mtime_ns, st.st_size):
        return False
    # Inspect the actual PNG IHDR rather than assuming HighResShot succeeded.
    with path.open('rb') as handle:
        header = handle.read(24)
    return (header[:8] == b'\x89PNG\r\n\x1a\n'
            and struct.unpack('>II', header[16:24]) == (1920,1080))


def tick(delta):
    global PHASE, PHASE_START, OWNS_PIE, PLAYER_SEEN, LAST_SAMPLE, LAST_POSITION
    global ROUTE_INDEX, JUMP_BASE, JUMP_MAX, REFERENCE
    try:
        now = time.monotonic()
        age = now - PHASE_START
        if now - STARTED > 300:
            stop('failed', 'Timed out waiting for editor/PIE progress.')
            return
        if PHASE == 'request_pie':
            if age > 3:
                LEVEL.editor_request_begin_play()
                OWNS_PIE = True
                PHASE = 'wait_for_pawn'
                PHASE_START = now
                STATE['status'] = 'starting_pie'
                write_report()
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn:
            if PLAYER_SEEN:
                stop('failed', 'PIE ended before validation completed.')
            elif age > 45:
                stop('failed', 'No possessed player; ensure the editor viewport is visible.')
            return
        PLAYER_SEEN = True
        p = pawn.get_actor_location()
        if p.z < 40:
            stop('failed', 'Player fell below the preserved street surfaces.')
            return
        if now - LAST_SAMPLE > .15:
            STATE['samples'].append([round(p.x,2),round(p.y,2),round(p.z,2),
                                     bool(pawn.character_movement.is_falling())])
            if LAST_POSITION is not None:
                STATE['distance_cm'] += math.hypot(p.x-LAST_POSITION[0],p.y-LAST_POSITION[1])
            LAST_POSITION = (p.x,p.y)
            LAST_SAMPLE = now
        if PHASE == 'wait_for_pawn':
            if age > 2 and not pawn.character_movement.is_falling():
                pawn_class = pawn.get_class().get_path_name()
                ok = LEVEL.is_in_play_in_editor() and pawn.is_player_controlled() and \
                     pawn_class == '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter.BP_ThirdPersonCharacter_C'
                check('existing_player_possessed', ok, pawn_class=pawn_class,
                      world=world.get_path_name())
                if not ok:
                    stop('failed')
                    return
                cams = unreal.GameplayStatics.get_all_actors_of_class(world,unreal.CameraActor)
                REFERENCE = next(a for a in cams if a.get_name() == STATE['reference_actor_name'])
                PHASE='route'
                PHASE_START=now
                STATE['status']='running_pie'
            return
        if PHASE == 'route':
            name, goal, limit = ROUTE[ROUTE_INDEX]
            dx,dy=goal[0]-p.x,goal[1]-p.y
            distance=math.hypot(dx,dy)
            if distance < 25 or age > limit:
                ok = distance < 25 and not pawn.character_movement.is_falling()
                check(name,ok,position_cm=[p.x,p.y,p.z],distance_to_goal_cm=distance,
                      duration_seconds=age)
                pawn.character_movement.stop_movement_immediately()
                if not ok:
                    stop('failed','Route obstructed at '+name)
                    return
                ROUTE_INDEX+=1
                PHASE_START=now
                if ROUTE_INDEX == len(ROUTE):
                    PHASE='jump'
                    JUMP_BASE=p.z
                    JUMP_MAX=p.z
                    pawn.jump()
                return
            pawn.add_movement_input(unreal.Vector(dx/distance,dy/distance,0),min(1.,distance/100))
        elif PHASE == 'jump':
            JUMP_MAX=max(JUMP_MAX,p.z)
            if age>.25:
                pawn.stop_jumping()
            if age>1.5 and not pawn.character_movement.is_falling():
                check('jump_and_land',JUMP_MAX-JUMP_BASE>40 and abs(p.z-JUMP_BASE)<8,
                      jump_height_cm=JUMP_MAX-JUMP_BASE,landing_error_cm=abs(p.z-JUMP_BASE))
                # Reference staging only: face down the street after the return
                # route without changing character assets, movement or location.
                pawn.set_actor_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0),False)
                STATE['capture_pose']='PIE pawn faces +X; location reached by movement, no teleport'
                PHASE='settle_gameplay'
                PHASE_START=now
            elif age>7:
                stop('failed','Player did not land after jumping.')
        elif PHASE == 'settle_gameplay' and age>5:
            controller=unreal.GameplayStatics.get_player_controller(world,0)
            check('normal_gameplay_camera',controller.get_view_target()==pawn)
            capture(world,'Gameplay')
            PHASE='capture_gameplay'
            PHASE_START=now
        elif PHASE == 'capture_gameplay' and age>4:
            captured=capture_finished('Gameplay')
            if captured or age>20:
                check('gameplay_screenshot_1920x1080',captured,file=str(OUT/'Gameplay.png'))
                controller=unreal.GameplayStatics.get_player_controller(world,0)
                controller.set_view_target_with_blend(REFERENCE,0.)
                PHASE='settle_reference'
                PHASE_START=now
        elif PHASE == 'settle_reference' and age>5:
            capture(world,'Reference')
            PHASE='capture_reference'
            PHASE_START=now
        elif PHASE == 'capture_reference' and age>4:
            captured=capture_finished('Reference')
            if captured or age>20:
                check('reference_screenshot_1920x1080',captured,file=str(OUT/'Reference.png'))
                stop('complete')
    except Exception:
        stop('failed',traceback.format_exc())


try:
    setup()
except Exception:
    stop('failed',traceback.format_exc())
