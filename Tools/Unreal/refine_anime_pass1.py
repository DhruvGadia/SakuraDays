"""Prompt 13, iteration 1. Run in the existing Unreal Editor Python environment.

Only actor material overrides and environment lighting are authored. No geometry,
camera, collision, input, project settings or original material package is edited.
The first-run snapshot and package copies persist across repeat runs. Execution
does not constitute PIE or visual validation; those are separate review steps.
"""
import hashlib
import json
import shutil
import traceback
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/AnimeRefinement/pass1'
MAP = '/Game/SakuraDays/Maps/L_SakuraStreet'
DEST = '/Game/SakuraDays/Environment/AnimeRefinement/Pass1'
TAG = 'SakuraDaysAnimePass1'
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
REPORT = {'applied': False, 'changes': [], 'skipped': [], 'errors': []}


def value(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


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
    key = hashlib.sha256((source.get_path_name() + str(tint) + str(lift) + 'v1').encode()).hexdigest()[:16]
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
        # A small local-color floor keeps pink/green masses legible in deep shade.
        # Existing emissive surfaces are excluded by recipe classification below.
        gain = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, 500, 180)
        gain.set_editor_property('r', lift)
        em = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, 750, 180)
        assert MEL.connect_material_expressions(mul, '', em, 'A')
        assert MEL.connect_material_expressions(gain, '', em, 'B')
        assert MEL.connect_material_property(em, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.set_metadata_tag(m, 'SakuraDays.AnimeRecipe', key)
    EAL.set_metadata_tag(m, 'SakuraDays.SourceMaterial', source.get_path_name())
    if not EAL.save_loaded_asset(m, only_if_is_dirty=True):
        raise RuntimeError('Could not save ' + path)
    REPORT.setdefault('derived_materials', []).append(path)
    return m


def recipe(actor, source):
    n = source.get_name().lower()
    # Match material identity, never broad actor-name replacements: sign lettering,
    # texture atlases, glazing, bark and architectural borders retain their sources.
    if 'sakura_blossom' in n:
        return ((1.06, .88, 1.04), .14)
    if any(x in n for x in ('leaf', 'hedge', 'shrub')):
        return ((.88, 1.06, .82), .07)
    if 'distanthill' in n:
        return ((.85, 1.05, 1.13), .10)
    if 'townasphalt' in n:
        return ((.88, .91, 1.02), 0)
    if 'townpaving' in n:
        return ((1.02, .97, .98), 0)
    if 'caferose' in n:
        return ((1.08, .80, .85), 0)
    return None


def run():
    OUT.mkdir(parents=True, exist_ok=True)
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
    suns = [a for a in actors if isinstance(a, unreal.DirectionalLight)]
    if len(suns) != 1:
        raise RuntimeError('Expected one existing sun; no lighting changes made')
    sun = suns[0]
    # Retain approved shadow composition while warming the illumination.
    set_read(sun.light_component, 'intensity', 5.5)
    sun.light_component.set_light_color(unreal.LinearColor(1., .965, .90, 1.))
    set_read(sun.light_component, 'light_source_angle', 1.25)
    REPORT['sun_color_readback'] = str(sun.light_component.get_editor_property('light_color'))
    for a in actors:
        if isinstance(a, unreal.SkyLight):
            set_read(a.light_component, 'intensity', 1.65)
            a.light_component.set_light_color(unreal.LinearColor(.89, .94, 1., 1.))
        for c in a.get_components_by_class(unreal.SkyAtmosphereComponent):
            # UE stores normalized scattering colors with small coefficient scales,
            # not unit-default artistic multipliers (SkyAtmosphereComponent.cpp).
            # Use absolute values from the original street's default coefficients;
            # multiplying current values would accumulate on repeated executions.
            optional(c, 'rayleigh_scattering_scale', .0331 * 1.12)
            optional(c, 'mie_scattering_scale', .003996 * .65)
        # Legacy sky sphere exposes these controls; do not replace sky architecture.
        if 'BP_Sky_Sphere' in a.get_class().get_name():
            optional(a, 'cloud_opacity', .55)
            optional(a, 'colors_determined_by_sun_position', False)
            optional(a, 'zenith_color', unreal.LinearColor(.025, .15, .42, 1))
            optional(a, 'horizon_color', unreal.LinearColor(.38, .59, .78, 1))
            try:
                a.call_method('RefreshMaterial')
            except Exception as exc:
                REPORT['skipped'].append('Legacy sky refresh: ' + str(exc))
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            original = baseline.get(a.get_path_name(), {}).get('materials', [])
            row = next((r for r in original if r['component'] == c.get_name()), None)
            if not row:
                continue
            for i, path in enumerate(row['slots']):
                source = unreal.load_asset(path) if path else None
                setting = recipe(a, source) if source else None
                if setting:
                    derived = derive(source, *setting)
                    c.set_material(i, derived)
                    REPORT['changes'].append({'actor': a.get_actor_label(), 'slot': i,
                                              'source': path, 'after': c.get_material(i).get_path_name()})
    label = 'Anime_Pass1_ColorGrade'
    pp = next((a for a in actors if a.get_actor_label() == label), None)
    if pp and not pp.actor_has_tag(TAG):
        raise RuntimeError('Unowned grade actor')
    if not pp:
        pp = subsystem.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
        pp.set_actor_label(label)
        pp.set_editor_property('tags', [TAG])
        pp.set_folder_path('SakuraDays/AnimeRefinement')
    set_read(pp, 'unbound', True)
    set_read(pp, 'priority', 50.)
    settings = pp.get_editor_property('settings')
    grades = {'auto_exposure_min_brightness': 1., 'auto_exposure_max_brightness': 1.,
              'auto_exposure_bias': 2., 'bloom_intensity': .04, 'motion_blur_amount': 0.,
              'vignette_intensity': 0., 'scene_fringe_intensity': 0.,
              'color_saturation': unreal.Vector4(1.045, 1.045, 1.045, 1.),
              'color_gamma_shadows': unreal.Vector4(1.055, 1.065, 1.09, 1.),
              'color_gain_highlights': unreal.Vector4(1.015, 1., .985, 1.)}
    for prop, val in grades.items():
        settings.set_editor_property('override_' + prop, True)
        settings.set_editor_property(prop, val)
    pp.set_editor_property('settings', settings)
    REPORT['post_process_readback'] = {k: value(pp.get_editor_property('settings').get_editor_property(k)) for k in grades}
    after = snapshot(actors)
    for path, old in before.items():
        new = after[path]
        if old['transform'] != new['transform']:
            raise RuntimeError('Unexpected actor transform change: ' + path)
        for a, b in zip(old['materials'], new['materials']):
            if a['mesh'] != b['mesh'] or a['collision'] != b['collision']:
                raise RuntimeError('Unexpected mesh/collision change: ' + path)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError('Map save failed')
    (OUT / 'after.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
    REPORT.update(applied=True, preserved_actor_count=len(actors),
                  effects='Existing three Niagara zones and vertex-weighted wind preserved',
                  validation='Authoring readback only; PIE and image review required separately')


try:
    run()
except Exception:
    REPORT['errors'].append(traceback.format_exc())
    raise
finally:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'applied.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
