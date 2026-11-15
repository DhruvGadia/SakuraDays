"""Approved street assets: revisioned Unreal import, preserving existing packages.

Run in Unreal Python. SAKURA_STREET_IMPORT_MODE=plan|import|validate (default import).
Optional SAKURA_STREET_IMPORT_REVISION adds a review label without overwrites.
Output: Saved/StreetAssembly/imports.json. Only this script's allowlist is imported.
"""
import hashlib
import json
import math
import os
import re
import traceback
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
assert Path(unreal.Paths.project_dir()).resolve() == ROOT, 'Wrong project; refusing import'
OUT = ROOT / 'Saved/StreetAssembly'
OUT.mkdir(parents=True, exist_ok=True)
MODE = os.environ.get('SAKURA_STREET_IMPORT_MODE', 'import')
LABEL = os.environ.get('SAKURA_STREET_IMPORT_REVISION', '')
assert MODE in ('plan', 'import', 'validate')
assert not LABEL or re.fullmatch('[A-Za-z0-9_]{1,32}', LABEL)
RECIPE = 'street_v1_authored_normals_cafe_palette_local_collision'
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
SM = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()
CAFE_ROOT = ROOT / 'SourceArt/Architecture/Cafe01'
TREE_ROOT = ROOT / 'SourceArt/Foliage/SakuraTreeKit'
CAFE = json.loads((CAFE_ROOT / 'build_manifest.json').read_text(encoding='utf-8'))
TREES = json.loads((TREE_ROOT / 'build_manifest.json').read_text(encoding='utf-8'))
PILOT = json.loads((ROOT / 'Docs/ASSET_IMPORT_RESULTS.json').read_text(encoding='utf-8'))
assert PILOT.get('passed') and not PILOT.get('errors'), 'Passed pilot required'
REPORT = {'recipe': RECIPE, 'mode': MODE, 'engine': unreal.SystemLibrary.get_engine_version(),
          'assets': {}, 'results': {}, 'errors': []}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(*values):
    return hashlib.sha256('|'.join([RECIPE, *values]).encode()).hexdigest()


def revision(fp):
    return 'r_' + fp[:12] + ('_' + LABEL if LABEL else '')


def save_report():
    REPORT['passed'] = not REPORT['errors'] and len(REPORT['assets']) == 13
    (OUT / 'imports.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')


def own(asset, fp):
    EAL.set_metadata_tag(asset, 'SakuraDays.ImportRecipe', RECIPE)
    EAL.set_metadata_tag(asset, 'SakuraDays.SourceFingerprint', fp)


def existing(path, fp):
    if not EAL.does_asset_exist(path):
        return None
    asset = unreal.load_asset(path)
    if EAL.get_metadata_tag(asset, 'SakuraDays.SourceFingerprint') != fp:
        raise RuntimeError('Existing asset preserved; choose a fresh revision: ' + path)
    return asset


def linear_color(hexcolor):
    values = [int(hexcolor[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return unreal.LinearColor(*values, 1)


def constant(mat, value, x, y):
    n = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, x, y)
    n.set_editor_property('r', value)
    return n


def link(node, pin, mat, prop):
    if not MEL.connect_material_property(node, pin, prop):
        raise RuntimeError('Material connection failed: ' + str(prop))


def cafe_material(folder, name, color, fp):
    path = folder + '/' + name
    prior = existing(path, fp)
    if prior:
        return prior
    if MODE == 'validate':
        raise RuntimeError('Missing material: ' + path)
    mat = AT.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    base = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    base.set_editor_property('constant', linear_color(color))
    link(base, '', mat, unreal.MaterialProperty.MP_BASE_COLOR)
    link(constant(mat, .82, -300, 150), '', mat, unreal.MaterialProperty.MP_ROUGHNESS)
    link(constant(mat, .2, -300, 230), '', mat, unreal.MaterialProperty.MP_SPECULAR)
    link(constant(mat, 0, -300, 310), '', mat, unreal.MaterialProperty.MP_METALLIC)
    if name == 'M_Cafe_Lamp':
        mult = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -100, -150)
        strength = constant(mat, .3, -300, -220)
        assert MEL.connect_material_expressions(base, '', mult, 'A')
        assert MEL.connect_material_expressions(strength, '', mult, 'B')
        link(mult, '', mat, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errors = MEL.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compile failed ' + name + ': ' + str(errors))
    own(mat, fp)
    EAL.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat


def import_mesh(source, folder, name):
    if EAL.does_asset_exist(folder + '/' + name):
        raise RuntimeError('Refusing replacement of ' + folder + '/' + name)
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.one_convex_hull_per_ucx = True
    data.generate_lightmap_u_vs = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = True
    data.import_uniform_scale = 1
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method = unreal.FBXNormalGenerationMethod.MIKK_T_SPACE
    data.vertex_color_import_option = unreal.VertexColorImportOption.REPLACE
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    task.options = options
    task.factory = unreal.FbxFactory()
    AT.import_asset_tasks([task])
    objects = [a for a in task.get_objects() if isinstance(a, unreal.StaticMesh)]
    if len(objects) != 1:
        raise RuntimeError('Expected one imported static mesh for ' + name)
    mesh = objects[0]
    settings = SM.get_lod_build_settings(mesh, 0)
    settings.recompute_normals = False
    settings.recompute_tangents = True
    settings.use_mikk_t_space = True
    SM.set_lod_build_settings(mesh, 0, settings)
    return mesh


# Centimeter collision bounds in each prop's Blender local coordinates.
# The export basis is UE=(-BlenderY, BlenderX, BlenderZ).
# Plants block only the container, and the lamp blocks its base/pole, not lantern canopy.
PROP_BOXES = {
    'bench': ((0, 4, 46), (160, 55, 92)),
    'chair': ((0, 1.4, 43.6), (48, 49.4, 87.2)),
    'table': ((0, 0, 37.25), (70, 70, 74.5)),
    'pot': ((0, 0, 19), (40, 40, 38)),
    'planter': ((0, 0, 21), (120, 44, 42)),
    'menu': ((0, 2, 54.3), (68, 60, 108.6)),
    'lamp': ((0, 0, 130), (16, 16, 260)),
    'ac': ((0, 0, 32.25), (82, 42, 64.5)),
}


def transformed_prop_box(key, position=(0, 0, 0), angle=0):
    center, size = PROP_BOXES[key]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    bx = position[0] + c * center[0] - s * center[1]
    by = position[1] + s * center[0] + c * center[1]
    dims = (abs(c) * size[1] + abs(s) * size[0],
            abs(c) * size[0] + abs(s) * size[1], size[2])
    return ((-by, bx, position[2] + center[2]), dims)


def set_boxes(mesh, specs):
    SM.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.BOX)
    body = mesh.get_editor_property('body_setup')
    agg = body.get_editor_property('agg_geom')
    boxes = []
    for center, size in specs:
        box = unreal.KBoxElem()
        box.set_editor_property('center', unreal.Vector(*center))
        for field, value in zip(('x', 'y', 'z'), size):
            box.set_editor_property(field, value)
        boxes.append(box)
    agg.set_editor_property('box_elems', boxes)
    body.set_editor_property('agg_geom', agg)
    mesh.set_editor_property('customized_collision', True)


def collision(mesh, key):
    if key.startswith('tree_'):
        return 'Three authored UCX trunk hulls; foliage nonblocking'
    if key == 'cafe':
        boxes = [((0, 0, 304), (500, 600, 608))]
        # These are the kit's existing placed furnishings, not additional copies.
        placements = [('bench', (-240, -340, 0), 0), ('table', (210, -420, 0), 0),
                      ('chair', (128, -420, 0), 90), ('chair', (292, -420, 0), -90),
                      ('pot', (105, -295, 0), 0), ('pot', (-330, -290, 0), 0),
                      ('planter', (355, 50, 0), 90), ('menu', (-110, -385, 0), -8),
                      ('lamp', (410, -310, 0), 0), ('ac', (305, 170, 35), 90)]
        boxes += [transformed_prop_box(*p) for p in placements]
        note = 'Closed 500x600cm cafe shell plus 10 local furnishing/container proxies; terrace gaps remain walkable'
    else:
        boxes = [transformed_prop_box(key)]
        note = 'Simple local prop proxy; plants block containers only, lamp blocks pole/base'
    set_boxes(mesh, boxes)
    return note


def validate(mesh, manifest, uv_channels, key):
    b = mesh.get_bounds()
    dims = [2 * b.box_extent.x, 2 * b.box_extent.y, 2 * b.box_extent.z]
    bd = manifest['bounds_m']['dimensions']
    expected = [bd[1] * 100, bd[0] * 100, bd[2] * 100]
    errors = []
    if max(abs(a - b) for a, b in zip(dims, expected)) > .1:
        errors.append('Source centimeter bounds mismatch')
    slots = [str(x.material_slot_name) for x in mesh.static_materials]
    if slots != manifest['material_slots']:
        errors.append('Material slot names/order mismatch')
    if any(x.material_interface is None for x in mesh.static_materials):
        errors.append('Unassigned material')
    triangles = mesh.get_static_mesh_description(0).get_triangle_count()
    if triangles != manifest['triangles']:
        errors.append('Triangle count mismatch')
    uvs = SM.get_num_uv_channels(mesh, 0)
    if uvs != uv_channels:
        errors.append('UV channel count mismatch')
    invalid = 0
    count = 0
    for section in range(mesh.get_num_sections(0)):
        _, _, normals, _, _ = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, section)
        for n in normals:
            length = math.sqrt(n.x * n.x + n.y * n.y + n.z * n.z)
            count += 1
            invalid += not math.isfinite(length) or abs(length - 1) > .02
    if invalid or not count:
        errors.append('Invalid render normals')
    convex, simple = SM.get_convex_collision_count(mesh), SM.get_simple_collision_count(mesh)
    if key.startswith('tree_') and convex != 3:
        errors.append('Expected 3 trunk hulls')
    if not key.startswith('tree_') and not simple:
        errors.append('Missing simple collision')
    bottom = b.origin.z - b.box_extent.z
    if abs(bottom - manifest['bounds_m']['min'][2] * 100) > .1:
        errors.append('Pivot/bottom mismatch')
    return {'asset': mesh.get_path_name(), 'dimensions_cm': dims, 'expected_dimensions_cm': expected,
            'bounds_origin_cm': [b.origin.x, b.origin.y, b.origin.z], 'bottom_cm': bottom,
            'triangles': triangles, 'uv_channels': uvs, 'material_slots': slots,
            'simple_collision_shapes': simple, 'convex_hulls': convex,
            'normal_samples': count, 'invalid_normals': invalid, 'errors': errors}


def run():
    # Reuse the reviewed pilot imports without writing to their mesh/material packages.
    for oldkey, key in [('house', 'house'), ('tree', 'tree_hero')]:
        entry = PILOT['results'][oldkey]
        mesh = unreal.load_asset(entry['asset'])
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError('Pilot mesh missing: ' + entry['asset'])
        REPORT['assets'][key] = mesh.get_path_name()
        REPORT['results'][key] = dict(entry, action='reused reviewed pilot; no writes')
    hero = unreal.load_asset(REPORT['assets']['tree_hero'])
    tree_materials = {str(s.material_slot_name): s.material_interface for s in hero.static_materials}
    if set(tree_materials) != {'M_Sakura_Bark', 'M_Sakura_Blossom'} or any(v is None for v in tree_materials.values()):
        raise RuntimeError('Pilot tree materials unavailable')
    material_fp = fingerprint(json.dumps(CAFE['materials'], sort_keys=True))
    material_folder = '/Game/SakuraDays/Environment/Architecture/Cafe01/Revisions/' + revision(material_fp) + '/Materials'
    materials = {} if MODE == 'plan' else {
        'M_Cafe_' + key.title(): cafe_material(material_folder, 'M_Cafe_' + key.title(), color, material_fp)
        for key, color in CAFE['materials'].items()}
    specs = [('cafe', CAFE_ROOT / 'Exports/SM_Cafe01_Assembled.fbx', CAFE['assembled'], 2,
              '/Game/SakuraDays/Environment/Architecture/Cafe01', 'SM_Cafe01')]
    for key, suffix in [('chair', 'Chair'), ('table', 'Table'), ('bench', 'Bench'), ('lamp', 'StreetLamp'),
                        ('pot', 'PottedPlant'), ('planter', 'Planter'), ('ac', 'AC'), ('menu', 'MenuBoard')]:
        name = 'SM_Cafe_' + suffix
        specs.append((key, CAFE_ROOT / 'Exports' / (name + '.fbx'), CAFE['modules'][name], 2,
                      '/Game/SakuraDays/Environment/Props/Cafe01/' + suffix, name))
    for key, suffix in [('tree_spread', 'Spread'), ('tree_weeping', 'Weeping')]:
        name = 'SM_Sakura_' + suffix + '_LOD0'
        specs.append((key, TREE_ROOT / 'Exports' / (name + '.fbx'), TREES['trees'][name], 1,
                      '/Game/SakuraDays/Environment/Foliage/Sakura/' + suffix, 'SM_Sakura_' + suffix))
    for key, source, manifest, uv, base, name in specs:
        if not source.is_file():
            raise RuntimeError('Missing approved FBX: ' + str(source))
        source_hash = digest(source)
        deps = '|'.join(m.get_path_name() for m in tree_materials.values()) if key.startswith('tree_') else material_fp
        fp = fingerprint(source_hash, deps, json.dumps(manifest, sort_keys=True))
        folder = base + '/Revisions/' + revision(fp)
        path = folder + '/' + name
        if MODE == 'plan':
            REPORT['assets'][key] = path
            REPORT['results'][key] = {'asset': path, 'source': str(source.relative_to(ROOT)), 'exists': EAL.does_asset_exist(path)}
            continue
        mesh = existing(path, fp)
        action = 'reused without writing'
        if mesh is None:
            if MODE == 'validate':
                raise RuntimeError('Missing imported asset: ' + path)
            mesh = import_mesh(source, folder, name)
            use_materials = tree_materials if key.startswith('tree_') else materials
            for i, slot in enumerate(mesh.static_materials):
                mesh.set_material(i, use_materials[str(slot.material_slot_name)])
            note = collision(mesh, key)
            if uv == 2:
                mesh.set_editor_property('light_map_coordinate_index', 1)
            own(mesh, fp)
            EAL.set_metadata_tag(mesh, 'SakuraDays.CollisionPolicy', note)
            EAL.save_loaded_asset(mesh, only_if_is_dirty=False)
            action = 'created new revision'
        result = validate(mesh, manifest, uv, key)
        result.update(action=action, source=str(source.relative_to(ROOT)), source_sha256=source_hash,
                      fingerprint=fp, collision_policy=EAL.get_metadata_tag(mesh, 'SakuraDays.CollisionPolicy'))
        REPORT['assets'][key] = mesh.get_path_name()
        REPORT['results'][key] = result
        REPORT['errors'].extend(key + ': ' + e for e in result['errors'])
        save_report()
        if result['errors']:
            raise RuntimeError('Street import validation failed; further imports stopped')


try:
    run()
except Exception as error:
    REPORT['errors'].append(str(error))
    REPORT['traceback'] = traceback.format_exc()
    save_report()
    raise
save_report()
unreal.log('SAKURA_STREET_IMPORT ' + json.dumps(REPORT))
