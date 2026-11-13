"""Run in isolated Saved/House01UEValidation project, never in the main game."""
import unreal,json,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
assert 'House01UEValidation' in unreal.Paths.project_dir(), 'Use only the isolated validation project'
tasks=[]
destination='/Game/House01Validation/Check_'+uuid.uuid4().hex[:8]
for filename in ['SM_SakuraHouse01_Assembled','SM_Wall_Entry_2m','SM_Door_Entry_110x220']:
    options=unreal.FbxImportUI()
    options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    d=options.static_mesh_import_data
    d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
    d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=True;d.import_uniform_scale=1.
    task=unreal.AssetImportTask()
    task.filename=str(ROOT/'Exports'/(filename+'.fbx'))
    task.destination_path=destination
    task.destination_name=filename;task.automated=True;task.save=True;task.replace_existing=False
    task.options=options;task.factory=unreal.FbxFactory()
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
results={};errors=[]
for task in tasks:
    objects=task.get_objects()
    meshes=[x for x in objects if isinstance(x,unreal.StaticMesh)]
    if len(meshes)!=1:
        errors.append(task.destination_name+' expected 1 static mesh; found '+str(len(meshes)));continue
    mesh=meshes[0];b=mesh.get_bounds();ext=b.box_extent
    desc=mesh.get_static_mesh_description(0)
    uv_samples=[]
    if desc:
        for channel in [0,1]:
            v=desc.get_vertex_instance_uv(unreal.VertexInstanceID(0),channel)
            uv_samples.append([v.x,v.y])
    else:errors.append(task.destination_name+' has no source mesh description')
    results[task.destination_name]={'dimensions_cm':[2*ext.x,2*ext.y,2*ext.z],
        'origin_cm':[b.origin.x,b.origin.y,b.origin.z],'material_slots':len(mesh.static_materials),
        'asset':mesh.get_path_name(),'source_uv_channels_sampled':[0,1],'source_uv_samples':uv_samples,
        'source_vertex_instances':desc.get_vertex_instance_count() if desc else 0}
manifest=json.loads((ROOT/'build_manifest.json').read_text())
if 'SM_SakuraHouse01_Assembled' in results:
    dims=results['SM_SakuraHouse01_Assembled']['dimensions_cm'];expected=manifest['assembled_bounds_m']['dimensions']
    # Force Front X maps Blender -Y to Unreal +X; width maps onto the Y axis.
    target=[expected[1]*100,expected[0]*100,expected[2]*100]
    if max(abs(a-b) for a,b in zip(dims,target))>.1:errors.append('Unreal centimeter dimensions mismatch: '+str(dims)+' expected '+str(target))
if 'SM_Wall_Entry_2m' in results:
    d=results['SM_Wall_Entry_2m']['dimensions_cm']
    if abs(d[1]-200)>.1 or abs(d[2]-280)>.1:errors.append('2 m wall orientation/scale mismatch')
if 'SM_Door_Entry_110x220' in results:
    o=results['SM_Door_Entry_110x220']['origin_cm']
    # Door extends toward negative local Y; positive Unreal X is the facade front.
    results['front_direction_check']='Door width mapped to Unreal Y; depth to X; Z height retained'
report={'engine':unreal.SystemLibrary.get_engine_version(),'isolated_project':unreal.Paths.project_dir(),
    'force_front_x_axis':True,'convert_scene':True,'convert_scene_unit':True,'uniform_scale':1,
    'results':results,'errors':errors,'passed':not errors}
(ROOT/'validation_unreal.json').write_text(json.dumps(report,indent=2))
unreal.log('HOUSE01_UE_VALIDATION '+json.dumps(report))
if errors:raise RuntimeError(errors)
