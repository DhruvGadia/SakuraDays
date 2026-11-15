"""Two-asset pilot. Run with Unreal Editor Python; never replaces existing assets.

SAKURA_IMPORT_MODE: import (default), reimport (new revision), validate, plan.
SAKURA_IMPORT_REVISION: optional alphanumeric review label for a fresh revision.
Only the assembled House01 and hero sakura LOD0 are allowlisted.
"""
import unreal, json, hashlib, math, os, re, traceback
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
PROJECT=Path(unreal.Paths.project_dir()).resolve()
assert PROJECT==ROOT or PROJECT.name=='AssetImportPilotSandbox', 'Unexpected project; refusing import'
OUT=PROJECT/'Saved/AssetImportPilot';OUT.mkdir(parents=True,exist_ok=True)
MODE=os.environ.get('SAKURA_IMPORT_MODE','import')
assert MODE in ('import','reimport','validate','plan')
LABEL=os.environ.get('SAKURA_IMPORT_REVISION','')
assert not LABEL or re.fullmatch('[A-Za-z0-9_]{1,32}',LABEL), 'Invalid revision label'
if MODE=='reimport' and not LABEL:LABEL=datetime.now(timezone.utc).strftime('review_%Y%m%d_%H%M%S')
RECIPE='pilot_v2_import_normals_mikk_masked_040'
EAL=unreal.EditorAssetLibrary; MEL=unreal.MaterialEditingLibrary
AT=unreal.AssetToolsHelpers.get_asset_tools()
SM=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load_json(path):return json.loads(path.read_text(encoding='utf-8'))
house_manifest=load_json(ROOT/'SourceArt/Architecture/House01/build_manifest.json')
tree_manifest=load_json(ROOT/'SourceArt/Foliage/SakuraTreeKit/build_manifest.json')['trees']['SM_Sakura_Hero_LOD0']
HOUSE_MATS=[('M_Plaster_Cream','DDC9AD',.88),('M_Siding_BlueGray','A7B5C0',.85),('M_Trim_Plum','393344',.78),
    ('M_Roof_Slate','555B70',.85),('M_Timber_Warm','725548',.8),('M_Glass_Blue','6E93AF',.48),
    ('M_Glass_Reflection','BDD0DD',.6),('M_Concrete','B8B1A9',.9)]
SPECS={
 'house':dict(source=ROOT/'SourceArt/Architecture/House01/Exports/SM_SakuraHouse01_Assembled.fbx',
    base='/Game/SakuraDays/Environment/Architecture/House01',name='SM_House01',
    bounds=house_manifest['assembled_bounds_m'],triangles=house_manifest['assembled_triangles'],slots=[x[0] for x in HOUSE_MATS],uv=2),
 'tree':dict(source=ROOT/'SourceArt/Foliage/SakuraTreeKit/Exports/SM_Sakura_Hero_LOD0.fbx',
    texture=ROOT/'SourceArt/Foliage/SakuraTreeKit/Textures/T_Sakura_Blossom_Atlas.png',
    base='/Game/SakuraDays/Environment/Foliage/Sakura/Hero',name='SM_Sakura_Hero',
    bounds=tree_manifest['bounds_m'],triangles=tree_manifest['triangles'],slots=tree_manifest['material_slots'],uv=1)}
report={'engine':unreal.SystemLibrary.get_engine_version(),'project':str(PROJECT),'recipe':RECIPE,'mode':MODE,
    'results':{},'errors':[],'remaining_assets':'NOT processed; pilot allowlist contains exactly one house and one tree'}
def save_report():
    report['passed']=not report['errors'] and len(report['results'])==2
    (OUT/'latest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def own(asset,fingerprint):
    EAL.set_metadata_tag(asset,'SakuraDays.ImportRecipe',RECIPE)
    EAL.set_metadata_tag(asset,'SakuraDays.SourceFingerprint',fingerprint)
def require_new(path):
    if EAL.does_asset_exist(path):raise RuntimeError('Existing asset preserved; use a new revision label: '+path)
def color(h):
    vals=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    vals=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in vals]
    return unreal.LinearColor(*vals,1)
def expr(mat,cls,x,y):return MEL.create_material_expression(mat,cls,x,y)
def constant(mat,value,x,y):
    n=expr(mat,unreal.MaterialExpressionConstant,x,y);n.set_editor_property('r',value);return n
def connect(a,out,b,inp):
    if not MEL.connect_material_expressions(a,out,b,inp):raise RuntimeError('Material connection failed '+inp)
def output(n,out,mat,prop):
    if not MEL.connect_material_property(n,out,prop):raise RuntimeError('Material property connection failed '+str(prop))
def material(folder,name,hexcolor,rough,fingerprint,texture=None,vertex=False):
    path=folder+'/Materials/'+name;require_new(path)
    mat=AT.create_asset(name,folder+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    base=expr(mat,unreal.MaterialExpressionConstant3Vector,-500,0);base.set_editor_property('constant',color(hexcolor))
    baseout=''
    if texture:
        base=expr(mat,unreal.MaterialExpressionTextureSample,-700,0);base.set_editor_property('texture',texture);baseout='RGB'
        mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
        mat.set_editor_property('two_sided',True)
        mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        mat.set_editor_property('opacity_mask_clip_value',.4)
        output(base,'A',mat,unreal.MaterialProperty.MP_OPACITY_MASK)
        sub=expr(mat,unreal.MaterialExpressionConstant3Vector,-300,350);sub.set_editor_property('constant',color('B878A4'))
        output(sub,'',mat,unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    if vertex:
        vc=expr(mat,unreal.MaterialExpressionVertexColor,-700,-220)
        mul=expr(mat,unreal.MaterialExpressionMultiply,-250,0)
        connect(base,baseout,mul,'A');connect(vc,'',mul,'B');base=mul;baseout=''
    output(base,baseout,mat,unreal.MaterialProperty.MP_BASE_COLOR)
    output(constant(mat,rough,-200,170),'',mat,unreal.MaterialProperty.MP_ROUGHNESS)
    output(constant(mat,.2,-200,250),'',mat,unreal.MaterialProperty.MP_SPECULAR)
    output(constant(mat,0,-200,300),'',mat,unreal.MaterialProperty.MP_METALLIC)
    own(mat,fingerprint)
    compiler_errors=MEL.recompile_material(mat)
    if compiler_errors:raise RuntimeError('Material compile failed '+name+': '+str(compiler_errors))
    EAL.save_loaded_asset(mat,only_if_is_dirty=False)
    return mat
def import_texture(spec,folder,fingerprint):
    path=folder+'/Textures/T_Sakura_Blossom_Atlas';require_new(path)
    task=unreal.AssetImportTask();task.filename=str(spec['texture']);task.destination_path=folder+'/Textures'
    task.destination_name='T_Sakura_Blossom_Atlas';task.automated=True;task.replace_existing=False;task.save=False
    task.factory=unreal.TextureFactory();AT.import_asset_tasks([task])
    tex=next(o for o in task.get_objects() if isinstance(o,unreal.Texture2D))
    tex.set_editor_property('srgb',True);own(tex,fingerprint);EAL.save_loaded_asset(tex,only_if_is_dirty=False);return tex
def mesh_import(spec,folder,fingerprint):
    require_new(folder+'/'+spec['name'])
    options=unreal.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    d=options.static_mesh_import_data
    d.combine_meshes=True;d.auto_generate_collision=False;d.one_convex_hull_per_ucx=True
    d.generate_lightmap_u_vs=False;d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=True;d.import_uniform_scale=1
    d.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    d.normal_generation_method=unreal.FBXNormalGenerationMethod.MIKK_T_SPACE
    d.vertex_color_import_option=unreal.VertexColorImportOption.REPLACE
    task=unreal.AssetImportTask();task.filename=str(spec['source']);task.destination_path=folder;task.destination_name=spec['name']
    task.automated=True;task.replace_existing=False;task.save=False;task.options=options;task.factory=unreal.FbxFactory()
    AT.import_asset_tasks([task]);objects=[o for o in task.get_objects() if isinstance(o,unreal.StaticMesh)]
    if len(objects)!=1:raise RuntimeError('Expected one static mesh: '+str(objects))
    mesh=objects[0];own(mesh,fingerprint)
    settings=SM.get_lod_build_settings(mesh,0)
    settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
    SM.set_lod_build_settings(mesh,0,settings)
    return mesh
def house_collision(mesh):
    SM.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)
    body=mesh.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom');boxes=[]
    for center,size in [((0,0,295),(600,800,590)),((345,-100,7.5),(90,180,15)),((330,-100,22.5),(60,180,15))]:
        box=unreal.KBoxElem();box.set_editor_property('center',unreal.Vector(*center))
        for field,value in zip(('x','y','z'),size):box.set_editor_property(field,value)
        boxes.append(box)
    agg.set_editor_property('box_elems',boxes);body.set_editor_property('agg_geom',agg)
    mesh.set_editor_property('customized_collision',True)
    return 'Three simple boxes: 600x800x590cm closed exterior body and two entry steps; roof/balcony are not walkable targets'
def validate(key,spec,mesh):
    errors=[];b=mesh.get_bounds();dims=[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z]
    expected=spec['bounds']['dimensions'];expected=[expected[1]*100,expected[0]*100,expected[2]*100]
    delta=max(abs(a-c) for a,c in zip(dims,expected))
    if delta>.1:errors.append('Centimeter scale / axes mismatch')
    bottom=b.origin.z-b.box_extent.z
    if abs(bottom)>.1:errors.append('Ground pivot mismatch: bottom='+str(bottom))
    desc=mesh.get_static_mesh_description(0);normal_bad=0;normal_count=0
    for section in range(mesh.get_num_sections(0)):
        vertices,indices,normals,uvs,tangents=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,section)
        for n in normals:
            length=math.sqrt(n.x*n.x+n.y*n.y+n.z*n.z);normal_count+=1
            if not math.isfinite(length) or abs(length-1)>.02:normal_bad+=1
    if not normal_count:errors.append('No render normals available for inspection')
    if normal_bad:errors.append('Invalid normals: '+str(normal_bad))
    settings=SM.get_lod_build_settings(mesh,0)
    if settings.recompute_normals:errors.append('Imported normals unexpectedly recomputed')
    slots=[str(s.material_slot_name) for s in mesh.static_materials]
    if slots!=spec['slots']:errors.append('Unexpected material slots')
    if any(s.material_interface is None for s in mesh.static_materials):errors.append('Missing assigned material')
    if desc.get_triangle_count()!=spec['triangles']:errors.append('Triangle count mismatch')
    if SM.get_num_uv_channels(mesh,0)!=spec['uv']:errors.append('UV channel count mismatch')
    convex=SM.get_convex_collision_count(mesh);simple=SM.get_simple_collision_count(mesh)
    if key=='tree' and convex!=3:errors.append('Expected three trunk hulls')
    if key=='house' and simple<1:errors.append('Missing house collision')
    return {'asset':mesh.get_path_name(),'dimensions_cm':dims,'expected_dimensions_cm':expected,'max_dimension_error_cm':delta,
        'bounds_origin_cm':[b.origin.x,b.origin.y,b.origin.z],'ground_pivot_bottom_cm':bottom,
        'triangles':desc.get_triangle_count(),'normal_samples':normal_count,'invalid_normals':normal_bad,
        'normal_policy':'Import authored normals; compute Mikk tangents','uv_channels':SM.get_num_uv_channels(mesh,0),
        'material_slots':slots,'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials],
        'convex_hulls':convex,'simple_collision_shapes':simple,'errors':errors}
try:
    for key,spec in SPECS.items():
        assert spec['source'].is_file(), 'Missing approved FBX '+str(spec['source'])
        fingerprint=hashlib.sha256((RECIPE+sha(spec['source'])+(sha(spec['texture']) if 'texture' in spec else '')).encode()).hexdigest()
        folder=spec['base']+'/Revisions/r_'+fingerprint[:12]+('_'+LABEL if LABEL else '')
        path=folder+'/'+spec['name'];exists=EAL.does_asset_exist(path)
        if MODE=='plan':
            report['results'][key]={'asset':path,'source':str(spec['source'].relative_to(ROOT)),'exists':exists};continue
        if exists:
            mesh=unreal.load_asset(path)
            if EAL.get_metadata_tag(mesh,'SakuraDays.SourceFingerprint')!=fingerprint:
                raise RuntimeError('Existing unowned asset preserved: '+path)
            action='reused without writing'
        else:
            if MODE=='validate':raise RuntimeError('No matching imported revision: '+path)
            mesh=mesh_import(spec,folder,fingerprint)
            if key=='house':
                materials=[material(folder,n,c,r,fingerprint) for n,c,r in HOUSE_MATS]
                collision_note=house_collision(mesh)
                mesh.set_editor_property('light_map_coordinate_index',1)
            else:
                tex=import_texture(spec,folder,fingerprint)
                materials=[material(folder,'M_Sakura_Bark','51414F',.9,fingerprint,vertex=True),
                    material(folder,'M_Sakura_Blossom','E9A5CE',.9,fingerprint,texture=tex,vertex=True)]
                collision_note='Three imported UCX trunk hulls; canopy is nonblocking'
            for i,mat in enumerate(materials):mesh.set_material(i,mat)
            EAL.set_metadata_tag(mesh,'SakuraDays.CollisionPolicy',collision_note)
            EAL.save_loaded_asset(mesh,only_if_is_dirty=False);action='created new revision'
        result=validate(key,spec,mesh)
        result.update(source=str(spec['source'].relative_to(ROOT)),source_sha256=sha(spec['source']),fingerprint=fingerprint,action=action,
            collision_policy=EAL.get_metadata_tag(mesh,'SakuraDays.CollisionPolicy'))
        report['results'][key]=result;report['errors'].extend(key+': '+e for e in result['errors'])
        save_report()
        if result['errors']:raise RuntimeError('Pilot validation failed; remaining imports stopped')
except Exception as exc:
    report['errors'].append(str(exc));report['traceback']=traceback.format_exc();save_report();raise
save_report();unreal.log('SAKURA_IMPORT_PILOT '+json.dumps(report))
