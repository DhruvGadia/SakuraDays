"""Fresh import checks in Saved/Cafe01UEValidation only; never the game project."""
import hashlib
import json
import uuid
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parent
assert 'Cafe01UEValidation' in unreal.Paths.project_dir(), 'Use only the isolated Cafe01UEValidation project'
source = json.loads((ROOT/'validation_blender.json').read_text(encoding='utf-8'))
assert source['passed'], 'Blender validation must pass first'
for relative_path, digest in source['validated_sha256'].items():
    assert hashlib.sha256((ROOT/relative_path).read_bytes()).hexdigest() == digest, 'Asset changed after validation: ' + relative_path

destination = '/Game/Cafe01Validation/Check_' + uuid.uuid4().hex[:8]
tasks = []
for name in source['checks']:
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
    data.generate_lightmap_u_vs = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = True
    data.import_uniform_scale = 1.0
    task = unreal.AssetImportTask()
    task.filename = str(ROOT/'Exports'/(name+'.fbx'))
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = False
    task.options = options
    task.factory = unreal.FbxFactory()
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
if subsystem is None:
    subsystem = unreal.StaticMeshEditorSubsystem()

results = {}
errors = []
for task in tasks:
    name = task.destination_name
    meshes = [obj for obj in task.get_objects() if isinstance(obj, unreal.StaticMesh)]
    if len(meshes) != 1:
        errors.append(name + ': expected 1 static mesh; found ' + str(len(meshes)))
        continue
    mesh = meshes[0]
    b = mesh.get_bounds()
    dims = [b.box_extent.x*2, b.box_extent.y*2, b.box_extent.z*2]
    desc = mesh.get_static_mesh_description(0)
    uv_count = subsystem.get_num_uv_channels(mesh, 0)
    expected = source['checks'][name]
    d = expected['bounds_m']['dimensions']
    converted = [d[1]*100, d[0]*100, d[2]*100]
    error = max(abs(a-b) for a, b in zip(dims, converted))
    slots = [str(slot.material_slot_name) for slot in mesh.static_materials]
    triangles = desc.get_triangle_count() if desc else 0
    result = {'asset': mesh.get_path_name(), 'dimensions_cm': dims,
              'expected_dimensions_cm': converted, 'max_dimensions_error_cm': error,
              'material_slots': slots, 'uv_channels': uv_count, 'triangles': triangles}
    if error > .1:
        errors.append(name + ': centimeter bounds/axis mismatch')
    if slots != expected['material_slots']:
        errors.append(name + ': material slot names/order mismatch')
    if uv_count != len(expected['uv_channels']):
        errors.append(name + ': UV channel count mismatch')
    if triangles != expected['triangles']:
        errors.append(name + ': triangle count mismatch')
    results[name] = result

report = {'engine': unreal.SystemLibrary.get_engine_version(), 'isolated_project': unreal.Paths.project_dir(),
          'import_settings': {'force_front_x_axis': True, 'convert_scene': True, 'convert_scene_unit': True,
                              'uniform_scale': 1, 'combine_meshes': True, 'generate_lightmap_uvs': False,
                              'auto_generate_collision': False, 'import_materials': False},
          'scope': 'Fresh geometry imports only; final materials, gameplay collision and performance not tested',
          'results': results, 'errors': errors, 'passed': not errors}
(ROOT/'validation_unreal.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('CAFE_UE_VALIDATION ' + json.dumps(report))
if errors:
    raise RuntimeError('Cafe Unreal validation failed: ' + str(errors))
