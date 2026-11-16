"""Import airy sakura revisions, their authored LODs, and vertex-weighted wind."""
import json, math, sys, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from town_common import *

SRC=ROOT/'SourceArt/Foliage/SakuraTreeKitV2'
MAN=json.loads((SRC/'build_manifest.json').read_text())
DEST='/Game/SakuraDays/Environment/Foliage/Sakura/Prompt12'
SM=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()
REPORT={'passed':False,'assets':{},'results':{},'errors':[]}

def tree_material(folder,texture=None):
    name='M_Sakura_Blossom_Wind' if texture else 'M_Sakura_Bark'
    if EAL.does_asset_exist(folder+'/'+name):return unreal.load_asset(folder+'/'+name)
    m=AT.create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    vc=node(m,unreal.MaterialExpressionVertexColor,-700,-200)
    if texture:
        b=node(m,unreal.MaterialExpressionTextureSample,-700,0,texture=texture);pin='RGB'
        m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED);m.set_editor_property('two_sided',True)
        m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        m.set_editor_property('opacity_mask_clip_value',.4)
        link(b,unreal.MaterialProperty.MP_OPACITY_MASK,'A')
        sub=node(m,unreal.MaterialExpressionConstant3Vector,-300,300,constant=color('A87996'))
        link(sub,unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    else:
        b=node(m,unreal.MaterialExpressionConstant3Vector,-700,0,constant=color('54464D'));pin=''
    mul=node(m,unreal.MaterialExpressionMultiply,-300,0)
    assert MEL.connect_material_expressions(b,pin,mul,'A')
    assert MEL.connect_material_expressions(vc,'',mul,'B')
    link(mul,unreal.MaterialProperty.MP_BASE_COLOR)
    link(scalar(m,.94),unreal.MaterialProperty.MP_ROUGHNESS)
    link(scalar(m,.10),unreal.MaterialProperty.MP_SPECULAR)
    if texture:
        wind=node(m,unreal.MaterialExpressionCustom,0,-300)
        inputs=[]
        for name in ['P','T','W']:
            i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
        wind.set_editor_property('inputs',inputs)
        wind.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        wind.set_editor_property('code','float f=T*.8+P.x*.003+P.y*.002; return float3(sin(f)*2.3,cos(f*.83)*1.5,sin(f*1.6)*.45)*W;')
        pos=node(m,unreal.MaterialExpressionWorldPosition,-600,-400)
        timer=node(m,unreal.MaterialExpressionTime,-600,-500)
        assert MEL.connect_material_expressions(pos,'',wind,'P')
        assert MEL.connect_material_expressions(timer,'',wind,'T')
        assert MEL.connect_material_expressions(vc,'A',wind,'W')
        link(wind,unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    errors=MEL.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    EAL.save_loaded_asset(m,only_if_is_dirty=False)
    return m

try:
    texfile=SRC/MAN['atlas'];texfolder=DEST+'/Materials/r_'+sha(texfile)[:10]
    texpath=texfolder+'/T_BlossomAtlas'
    if EAL.does_asset_exist(texpath):tex=unreal.load_asset(texpath)
    else:
        task=unreal.AssetImportTask();task.filename=str(texfile);task.destination_path=texfolder;task.destination_name='T_BlossomAtlas'
        task.automated=True;task.replace_existing=False;task.save=False;task.factory=unreal.TextureFactory()
        AT.import_asset_tasks([task]);tex=next(x for x in task.get_objects() if isinstance(x,unreal.Texture2D))
        tex.set_editor_property('srgb',True);EAL.save_loaded_asset(tex,only_if_is_dirty=False)
    mats=[tree_material(texfolder),tree_material(texfolder,tex)]
    for kind in ('Hero','Spread','Weeping'):
        name='SM_Sakura_'+kind+'_LOD0';source=SRC/'Exports'/(name+'.fbx')
        lod_files=[SRC/'Exports'/('SM_Sakura_'+kind+'_LOD'+str(i)+'.fbx') for i in range(3)]
        fp=hashlib.sha256((''.join(sha(p) for p in lod_files)+'wind_lods_v2').encode()).hexdigest()[:12]
        folder=DEST+'/'+kind+'/r_'+fp
        mesh=import_fbx(source,folder,name)
        if SM.get_lod_count(mesh)<3:
            for lod in (1,2):
                result=SM.import_lod(mesh,lod,str(SRC/'Exports'/('SM_Sakura_'+kind+'_LOD'+str(lod)+'.fbx')))
                if result!=lod:raise RuntimeError('LOD import failed '+kind+str(lod))
        for i,m in enumerate(mats):mesh.set_material(i,m)
        # Material assignment can rebuild render data. Set explicit thresholds
        # after that rebuild; preserve source-model thresholds in the package.
        mesh.get_bounds()
        assert SM.set_lod_screen_sizes(mesh,[1.,.38,.16])
        EAL.save_loaded_asset(mesh,only_if_is_dirty=False)
        desc=MAN['trees'][name];b=mesh.get_bounds();dims=[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z]
        expected=[desc['bounds_m']['dimensions'][i]*100 for i in (1,0,2)]
        errors=[]
        # LOD bounds may conservatively include larger distant cards, inspect LOD0 vertices too.
        points=[];invalid=0
        for section in range(mesh.get_num_sections(0)):
            vertices,_,normals,_,_=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,section)
            points+=vertices
            for n in normals:invalid+=abs(math.sqrt(n.x*n.x+n.y*n.y+n.z*n.z)-1)>.02
        actual=[max(getattr(p,axis) for p in points)-min(getattr(p,axis) for p in points) for axis in ('x','y','z')]
        if max(abs(a-b) for a,b in zip(actual,expected))>.1:errors.append('LOD0 centimeter scale mismatch')
        if invalid:errors.append('Invalid normals')
        hulls=SM.get_convex_collision_count(mesh)
        if hulls!=3:errors.append('Expected three trunk hulls')
        lods=[mesh.get_static_mesh_description(i).get_triangle_count() for i in range(SM.get_lod_count(mesh))]
        expected_lods=[MAN['trees']['SM_Sakura_'+kind+'_LOD'+str(i)]['triangles'] for i in range(3)]
        if lods!=expected_lods:errors.append('Render LOD counts differ from source: '+str(lods)+' expected '+str(expected_lods))
        REPORT['assets'][kind]=mesh.get_path_name()
        assert SM.set_lod_screen_sizes(mesh,[1.,.38,.16])
        EAL.save_loaded_asset(mesh,only_if_is_dirty=False)
        REPORT['results'][kind]={'lod_triangles':lods,'lod0_dimensions_cm':actual,'expected_cm':expected,'combined_lod_bounds_cm':dims,'uv_channels':SM.get_num_uv_channels(mesh,0),'trunk_hulls':hulls,'invalid_normals':invalid,'requested_screen_sizes':[1.,.38,.16],'render_screen_sizes':list(SM.get_lod_screen_sizes(mesh)),'errors':errors}
        REPORT['errors'] += [kind+': '+e for e in errors]
    if REPORT['errors']:raise RuntimeError('Tree validation failed')
    scene=Scene();changed=[]
    for name,a in scene.existing.items():
        if not name.startswith('SD_Sakura_'):continue
        old=a.static_mesh_component.static_mesh.get_name()
        kind='Weeping' if 'Weeping' in old else 'Spread' if 'Spread' in old else 'Hero'
        a.static_mesh_component.set_static_mesh(unreal.load_asset(REPORT['assets'][kind]))
        changed.append(name)
    if len(changed)!=10:raise RuntimeError('Expected ten existing street trees; got '+str(len(changed)))
    scene.save()
    REPORT.update(passed=True,actors_updated=changed,wind='Vertex alpha weights; maximum horizontal amplitude 2.3cm; no bark motion')
except Exception:
    REPORT['errors'].append(traceback.format_exc());raise
finally:(OUT/'trees.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
