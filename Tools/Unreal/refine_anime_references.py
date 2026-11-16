"""One controlled Prompt 13 correction using the subsequently supplied references.

Style A/B remain authoritative. Daylight 02/03/04 guide clearer blue atmosphere;
05/06/07 guide warmer café glazing and readable local colors in residential shade.
08/09 are future mood context only. No geometry, collision, sun direction, exposure,
foliage/wind/masking, particles, inputs or cameras are changed. This does not create
an interior or substitute new meshes. Run in Unreal; PIE review is separate.
"""
import hashlib
import json
import shutil
import traceback
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/AnimeRefinement/references'
MAP = '/Game/SakuraDays/Maps/L_SakuraStreet'
DEST = '/Game/SakuraDays/Environment/AnimeRefinement/References'
TAG = 'SakuraDaysAnimeReferences'
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
REPORT = {'applied': False, 'changes': [], 'skipped': [], 'errors': [], 'reference_scope': {'style_authority': ['Style_A.png', 'Style_B.png'], 'daylight': ['02_School_Campus.png', '03_Riverside_Path.png', '04_Hilltop_Overlook.png'], 'environment_warmth': ['05_Local_Cafe.png', '06_Residential_Alley.png', '07_Train_Station.png'], 'future_mood_only': ['08_Evening_Sunset.png', '09_Night_Festival.png']}}


def value(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    for fields in (('x', 'y', 'z', 'w'), ('r', 'g', 'b', 'a'), ('x', 'y', 'z')):
        if all(hasattr(v, field) for field in fields):
            return {field: float(getattr(v, field)) for field in fields}
    raise TypeError('Unsupported report value: ' + type(v).__name__)


def set_read(obj, prop, new):
    old = obj.get_editor_property(prop)
    obj.set_editor_property(prop, new)
    REPORT['changes'].append({'object': obj.get_path_name(), 'property': prop,
                              'before': value(old), 'after': value(obj.get_editor_property(prop))})


def optional(obj, prop, new):
    try:
        obj.get_editor_property(prop)
    except Exception:
        REPORT['skipped'].append(obj.get_path_name() + ':' + prop)
        return
    set_read(obj, prop, new)


def transform(a):
    p, r, s = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
    return [[p.x, p.y, p.z], [r.pitch, r.yaw, r.roll], [s.x, s.y, s.z]]


def snapshot(actors):
    data = {}
    for a in actors:
        row = {'class': a.get_class().get_name(), 'transform': transform(a), 'materials': []}
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            row['materials'].append({'component': c.get_name(), 'mesh': c.static_mesh.get_path_name() if c.static_mesh else None,
                                    'collision': str(c.get_collision_profile_name()),
                                    'slots': [c.get_material(i).get_path_name() if c.get_material(i) else None
                                              for i in range(c.get_num_materials())]})
        data[a.get_path_name()] = row
    return data


def derive(source, tint, lift):
    # First-run source paths are used on every run: never stack tint operations.
    key = hashlib.sha256((source.get_path_name() + str(tint) + str(lift) + 'references_v1').encode()).hexdigest()[:16]
    path = DEST + '/M_Anime_' + key
    if EAL.does_asset_exist(path):
        result = unreal.load_asset(path)
        if EAL.get_metadata_tag(result, 'SakuraDays.AnimeRecipe') != key:
            raise RuntimeError('Unowned derived material: ' + path)
        return result
    if not isinstance(source, unreal.Material):
        REPORT['skipped'].append('Non-base material preserved: ' + source.get_path_name())
        return source
    m = EAL.duplicate_asset(source.get_path_name(), path)
    if not m:
        raise RuntimeError('Material duplication failed: ' + path)
    prop = unreal.MaterialProperty.MP_BASE_COLOR
    src = MEL.get_material_property_input_node(m, prop)
    pin = MEL.get_material_property_input_node_output_name(m, prop)
    if not src:
        raise RuntimeError('No base color input on ' + source.get_path_name())
    tint_node = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, 500, 0)
    tint_node.set_editor_property('constant', unreal.LinearColor(*tint, 1))
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, 750, 0)
    assert MEL.connect_material_expressions(src, pin, mul, 'A')
    assert MEL.connect_material_expressions(tint_node, '', mul, 'B')
    assert MEL.connect_material_property(mul, '', prop)
    if lift:
        # A restrained local-color floor makes shaded architecture readable.
        # Preserve any pre-existing emissive contribution as well as the untouched
        # opacity, normal, roughness and world-position-offset graph connections.
        emissive_prop = unreal.MaterialProperty.MP_EMISSIVE_COLOR
        prior_emissive = MEL.get_material_property_input_node(m, emissive_prop)
        prior_pin = MEL.get_material_property_input_node_output_name(m, emissive_prop)
        gain = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, 500, 180)
        gain.set_editor_property('r', lift)
        em = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, 750, 180)
        assert MEL.connect_material_expressions(mul, '', em, 'A')
        assert MEL.connect_material_expressions(gain, '', em, 'B')
        if prior_emissive:
            add = MEL.create_material_expression(m, unreal.MaterialExpressionAdd, 950, 180)
            assert MEL.connect_material_expressions(prior_emissive, prior_pin, add, 'A')
            assert MEL.connect_material_expressions(em, '', add, 'B')
            em = add
        assert MEL.connect_material_property(em, '', emissive_prop)
    compile_errors = MEL.recompile_material(m)
    if compile_errors:
        raise RuntimeError('Material compilation failed: ' + str(compile_errors))
    EAL.set_metadata_tag(m, 'SakuraDays.AnimeRecipe', key)
    EAL.set_metadata_tag(m, 'SakuraDays.SourceMaterial', source.get_path_name())
    if not EAL.save_loaded_asset(m, only_if_is_dirty=True):
        raise RuntimeError('Could not save ' + path)
    REPORT.setdefault('derived_materials', []).append(path)
    REPORT.setdefault('material_recipes', []).append({
        'source': source.get_path_name(), 'derived': path,
        'base_color_multiplier': list(tint), 'local_color_floor': lift})
    return m


def recipe(actor, source):
    n = source.get_name().lower()
    label = actor.get_actor_label()
    # Restrict changes to explicit architectural identities. A small local-color
    # floor compensates for the unusually dark blue shaded façade in the capture;
    # sunlit faces still receive their original physically lit contribution.
    if label in ('SD_House01', 'SD_House02', 'SD_House03', 'SD_House04', 'SD_House05'):
        if 'houseplaster' in n:
            return ((1.02, 1.0, .96), .10)
        if 'housesiding' in n:
            return ((1.04, 1.0, .94), .12)
    # Keep the existing glazing and separate reflection geometry. This is a warm
    # smoked-glass color treatment, not fabricated interior detail or transparency.
    if label == 'SD_Cafe_HANA' and n == 'm_cafe_glass':
        return ((1.30, 1.0, .72), .16)
    return None


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before authoring; live session preserved.')
    if Path(unreal.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    if (unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or
            unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Save intentional editor changes first; dirty packages preserved.')
    # Back up the complete map and any external actor/object packages before load.
    backup = OUT / 'Backup'
    if not (backup / 'complete.json').exists():
        paths = [ROOT / 'Content/SakuraDays/Maps/L_SakuraStreet.umap']
        for kind in ('__ExternalActors__', '__ExternalObjects__'):
            base = ROOT / 'Content' / kind / 'SakuraDays/Maps/L_SakuraStreet'
            if base.exists():
                paths.extend(p for p in base.rglob('*') if p.is_file())
        manifest = []
        for src in paths:
            dst = backup / src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            manifest.append({'path': str(src.relative_to(ROOT)), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest()})
        (backup / 'complete.json').write_text(json.dumps(manifest, indent=2))
    if not unreal.EditorLevelLibrary.load_level(MAP):
        raise RuntimeError('Could not load street')
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(subsystem.get_all_level_actors())
    before = snapshot(actors)
    baseline_file = OUT / 'before.json'
    if not baseline_file.exists():
        baseline_file.write_text(json.dumps(before, indent=2), encoding='utf-8')
    baseline = json.loads(baseline_file.read_text(encoding='utf-8'))
    # Clearer blue sky from daylight references, retaining the same physical sky,
    # clouds and scattering model. Exposure and the approved sun remain fixed.
    atmospheres = [c for a in actors for c in a.get_components_by_class(unreal.SkyAtmosphereComponent)]
    if len(atmospheres) != 1:
        raise RuntimeError('Expected the existing single atmosphere')
    set_read(atmospheres[0], 'sky_luminance_factor', unreal.LinearColor(.64, .90, 1.30, 1.))
    for a in actors:
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            original = baseline.get(a.get_path_name(), {}).get('materials', [])
            row = next((r for r in original if r['component'] == c.get_name()), None)
            if not row:
                continue
            for i, path in enumerate(row['slots']):
                source = unreal.load_asset(path) if path else None
                # Resolve earlier derivations back to original art; never stack color
                # multipliers, including on a repeat run from the saved snapshot.
                seen = set()
                while source and EAL.get_metadata_tag(source, 'SakuraDays.SourceMaterial'):
                    if source.get_path_name() in seen:
                        raise RuntimeError('Cyclic derived-material provenance')
                    seen.add(source.get_path_name())
                    original_path = EAL.get_metadata_tag(source, 'SakuraDays.SourceMaterial')
                    source = unreal.load_asset(original_path)
                    if not source:
                        raise RuntimeError('Missing original material: ' + original_path)
                setting = recipe(a, source) if source else None
                if setting:
                    derived = derive(source, *setting)
                    c.set_material(i, derived)
                    REPORT['changes'].append({'actor': a.get_actor_label(), 'slot': i,
                                              'source': path, 'after': c.get_material(i).get_path_name()})
    label = 'Anime_References_ColorGrade'
    pp = next((a for a in actors if a.get_actor_label() == label), None)
    if pp and not pp.actor_has_tag(TAG):
        raise RuntimeError('Unowned grade actor')
    if not pp:
        pp = subsystem.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        pp.set_actor_label(label)
        pp.set_editor_property('tags', [TAG])
        pp.set_folder_path('SakuraDays/AnimeRefinement')
    set_read(pp, 'unbound', True)
    set_read(pp, 'priority', 80.)
    settings = pp.get_editor_property('settings')
    grades = {'auto_exposure_min_brightness': 1., 'auto_exposure_max_brightness': 1.,
              'auto_exposure_bias': 1.8, 'bloom_intensity': .04, 'motion_blur_amount': 0.,
              'vignette_intensity': 0., 'scene_fringe_intensity': 0.,
              'color_saturation': unreal.Vector4(1.045, 1.045, 1.045, 1.),
              'color_gamma_shadows': unreal.Vector4(1.10, 1.08, 1.09, 1.),
              'color_saturation_shadows': unreal.Vector4(.85, .85, .85, 1.),
              'color_gain_highlights': unreal.Vector4(1.015, 1., .985, 1.)}
    for prop, val in grades.items():
        settings.set_editor_property('override_' + prop, True)
        settings.set_editor_property(prop, val)
    pp.set_editor_property('settings', settings)
    REPORT['post_process_readback'] = {k: value(pp.get_editor_property('settings').get_editor_property(k)) for k in grades}
    if not REPORT.get('derived_materials') and not any('slot' in c for c in REPORT['changes']):
        raise RuntimeError('Expected architectural material matches; none found')
    after = snapshot(actors)
    for path, old in before.items():
        new = after[path]
        if old['transform'] != new['transform']:
            raise RuntimeError('Unexpected actor transform change: ' + path)
        if len(old['materials']) != len(new['materials']):
            raise RuntimeError('Unexpected component count change: ' + path)
        for a, b in zip(old['materials'], new['materials']):
            if a['mesh'] != b['mesh'] or a['collision'] != b['collision']:
                raise RuntimeError('Unexpected mesh/collision change: ' + path)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError('Map save failed')
    (OUT / 'after.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
    REPORT.update(applied=True, preserved_actor_count=len(actors),
                  intentional_mesh_substitutions=[],
                  effects='Existing three Niagara zones (144 petals) and vertex-weighted wind preserved',
                  validation='Authoring readback only; PIE and image review required separately')


try:
    run()
except Exception:
    REPORT['errors'].append(traceback.format_exc())
    raise
finally:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'applied.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
