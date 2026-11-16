"""Read actual Niagara petal simulation data during PIE, without changing it.

Usage from a PIE tick callback after the map has run for at least one second::

    import verify_petals_runtime
    result = verify_petals_runtime.sample(pie_world)

The returned dictionary is JSON serializable. Call a second time on a later
frame for optional position-delta evidence where Niagara retained UniqueID.
No asset, actor, material, simulation state, or map is saved or modified.
Only transient one-frame simulation caches are allocated. Core Niagara is the
only plugin needed at runtime; the authoring converter/toolset is not used.

APIs verified against the installed UE 5.8 NiagaraSimCache.h and
NiagaraSimCacheFunctionLibrary.h. This module does not run on import.
"""
import math
import traceback

import unreal

EXPECTED_LABELS = tuple('JP_PetalDrift%d' % i for i in range(3))
EXPECTED_EMITTER = 'GentleFallingPetals'
EXPECTED_ASSET_FOLDER = '/Game/SakuraDays/Effects/Petals/Prompt12/'
_PREVIOUS = {}


def _xyz(vector):
    return [float(vector.x), float(vector.y), float(vector.z)]


def _stats(values):
    if not values:
        return None
    return {'min': min(values), 'max': max(values),
            'mean': sum(values) / len(values)}


def _capture(actor, world_path):
    label = actor.get_actor_label()
    row = {'actor': label, 'passed': False, 'errors': []}
    component = actor.get_component_by_class(unreal.NiagaraComponent)
    if component is None:
        raise RuntimeError('Actor has no NiagaraComponent')
    system = component.get_asset()
    row['system'] = system.get_path_name() if system else None
    row['active'] = bool(component.is_active())
    row['paused'] = bool(component.is_paused())
    if not system or not row['system'].startswith(EXPECTED_ASSET_FOLDER):
        row['errors'].append('Wrong or missing Prompt12 Niagara system')
    if not row['active'] or row['paused']:
        row['errors'].append('Niagara component is inactive or paused')

    params = unreal.NiagaraSimCacheCreateParameters()
    params.set_editor_property('attribute_capture_mode',
                               unreal.NiagaraSimCacheAttributeCaptureMode.ALL)
    params.set_editor_property('allow_data_interface_caching', False)
    params.set_editor_property('allow_rebasing', False)
    cache = unreal.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(actor)
    if cache is None:
        raise RuntimeError('Cannot create transient simulation cache')
    # OutSimCache is a Python return value. AdvanceSimulation=False is crucial:
    # this samples the frame that the game produced, not a manually stepped one.
    captured = unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(
        cache, params, component, False, 1.0 / 60.0)
    # UE Python folds the bool success return into the sole out-object:
    # a successful capture returns NiagaraSimCache, failure returns None.
    if isinstance(captured, unreal.NiagaraSimCache):
        success, cache = True, captured
    elif isinstance(captured, tuple) and len(captured)==2:
        success, cache = captured
    elif captured is None:
        success, cache = False, None
    else:
        raise RuntimeError('Unexpected CaptureNiagaraSimCacheImmediate return: ' + repr(captured))
    row['capture_success'] = bool(success)
    if not success or cache is None:
        raise RuntimeError('Live Niagara simulation could not be captured')
    row['frames_captured'] = int(cache.get_num_frames())
    row['simulation_age_seconds'] = float(cache.get_start_seconds())
    row['emitter_names'] = [str(name) for name in cache.get_emitter_names()]
    if row['frames_captured'] != 1:
        raise RuntimeError('Expected one genuine simulation frame')
    if EXPECTED_EMITTER not in row['emitter_names']:
        raise RuntimeError('Expected GentleFallingPetals emitter is missing')

    positions = list(cache.read_position_attribute(
        'Position', EXPECTED_EMITTER, True, 0))
    velocities = list(cache.read_vector_attribute(
        'Velocity', EXPECTED_EMITTER, 0))
    sizes=list(cache.read_vector2_attribute('SpriteSize',EXPECTED_EMITTER,0))
    row['sprite_size_cm']=[[float(v.x),float(v.y)] for v in sizes[:3]]
    if len(sizes)!=len(positions) or any(abs(v.x-5.)>.01 or abs(v.y-7.)>.01 for v in sizes):
        row['errors'].append('Actual petal sprite sizes differ from 5 x 7cm')
    row['particle_count'] = len(positions)
    row['velocity_count'] = len(velocities)
    row['world_z_cm'] = _stats([float(p.z) for p in positions])
    row['above_sidewalk_count'] = sum(float(p.z)>20.0 for p in positions)
    row['visible_height_fraction'] = row['above_sidewalk_count']/len(positions) if positions else 0.0
    # A running emitter can still be invisible if Initialize overwrites its
    # spawn position. Require real petals above the ground and near the canopy.
    if row['visible_height_fraction']<.8 or not positions or max(p.z for p in positions)<250.0:
        row['errors'].append('Petals are not occupying the visible above-ground volume')
    row['simulation_velocity_z_cm_s'] = _stats([float(v.z) for v in velocities])
    row['sample_world_positions_cm'] = [_xyz(p) for p in positions[:5]]
    row['sample_simulation_velocities_cm_s'] = [_xyz(v) for v in velocities[:5]]
    row['all_values_finite'] = all(
        math.isfinite(value) for vector in positions + velocities for value in _xyz(vector))
    rotation = actor.get_actor_rotation()
    row['actor_rotation_degrees'] = [float(rotation.pitch), float(rotation.yaw), float(rotation.roll)]
    # This authored emitter is local space. Its actors only rotate around Z, so
    # simulation Z is world Z. Refuse to mislabel tilted local velocities.
    vertical_axes_match = abs(rotation.pitch) < .001 and abs(rotation.roll) < .001
    row['simulation_z_matches_world_z'] = vertical_axes_match
    row['downward_velocity_verified'] = bool(
        positions and len(positions) == len(velocities)
        and row['all_values_finite'] and vertical_axes_match
        and all(float(v.z) < -0.5 for v in velocities))

    if not positions:
        row['errors'].append('No live petals in the captured frame')
    if len(positions) != len(velocities):
        row['errors'].append('Velocity attribute missing or does not match particle count')
    if not row['all_values_finite']:
        row['errors'].append('Particle data contains non-finite values')
    if not row['downward_velocity_verified']:
        row['errors'].append('Actual downward particle velocity was not verified')
    # Four particles/sec * 12 sec lifetime is nominally 48 per zone. Leave a
    # few frames of tolerance while catching runaway/mistyped spawn rates.
    if len(positions) > 56:
        row['errors'].append('Particle count exceeds the sparse effect budget (56 per zone)')

    # UniqueID is useful when retained by the compiled emitter. Its absence is
    # not an error: verified runtime velocities already provide direct motion
    # data. Never compare arbitrary buffer indices across deaths/spawns.
    ids = list(cache.read_int_attribute('UniqueID', EXPECTED_EMITTER, 0))
    row['unique_id_count'] = len(ids)
    row['temporal_motion_verified'] = False
    row['temporal_motion_note'] = 'A second sample with retained UniqueID is required'
    if len(ids) == len(positions) and positions and len(set(ids)) == len(ids):
        key = (world_path, label)
        now = row['simulation_age_seconds']
        current = {int(pid): _xyz(pos) for pid, pos in zip(ids, positions)}
        previous = _PREVIOUS.get(key)
        if previous and now > previous['time']:
            shared = sorted(current.keys() & previous['positions'].keys())
            deltas = [current[pid][2] - previous['positions'][pid][2] for pid in shared]
            row['matched_particles_between_samples'] = len(shared)
            row['sample_interval_seconds'] = now - previous['time']
            row['matched_world_z_delta_cm'] = _stats(deltas)
            row['temporal_motion_verified'] = bool(deltas and all(dz < -0.001 for dz in deltas))
            row['temporal_motion_note'] = 'Compared matching live particle UniqueIDs across real game frames'
        _PREVIOUS[key] = {'time': now, 'positions': current}
    else:
        row['temporal_motion_note'] = 'UniqueID not retained; actual Velocity data is the motion evidence'
    row['passed'] = not row['errors']
    return row


def sample(world):
    """Return counts and measured velocities for all three authored petal zones.

    Run from PIE's game thread (for example a registered editor tick callback).
    The function never waits, steps simulation, spawns actors, or saves assets.
    A failing result includes errors instead of inventing counts or movement.
    """
    report = {'passed': False, 'method': 'Niagara one-frame live simulation cache',
              'expected_actors': list(EXPECTED_LABELS), 'actors': [], 'errors': [],
              'manually_advanced_simulation': False, 'saved_assets': False}
    if world is None:
        report['errors'].append('No PIE world supplied')
        return report
    world_path = world.get_path_name()
    report['world'] = world_path
    report['pie_world'] = 'UEDPIE_' in world_path
    if not report['pie_world']:
        report['errors'].append('World is not a PIE world; runtime validation requires PIE')
        return report
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.NiagaraActor)
    matching = {}
    for actor in actors:
        label = actor.get_actor_label()
        if label in EXPECTED_LABELS:
            if label in matching:
                report['errors'].append('Duplicate petal zone label: ' + label)
            matching[label] = actor
    for label in EXPECTED_LABELS:
        actor = matching.get(label)
        if actor is None:
            report['errors'].append('Missing petal zone: ' + label)
            continue
        try:
            row = _capture(actor, world_path)
        except Exception:
            row = {'actor': label, 'passed': False, 'errors': [traceback.format_exc()]}
        report['actors'].append(row)
        report['errors'].extend(label + ': ' + error for error in row['errors'])
    report['total_live_particles'] = sum(row.get('particle_count', 0) for row in report['actors'])
    report['downward_velocity_verified'] = (
        len(report['actors']) == 3
        and all(row.get('downward_velocity_verified', False) for row in report['actors']))
    report['temporal_motion_verified'] = (
        len(report['actors']) == 3
        and all(row.get('temporal_motion_verified', False) for row in report['actors']))
    report['passed'] = not report['errors'] and report['downward_velocity_verified']
    return report
