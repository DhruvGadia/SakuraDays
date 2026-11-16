"""Shared non-destructive authoring helpers for the Prompt 12 town pass."""
import hashlib
import json
import math
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/TownRefinement'
OUT.mkdir(parents=True, exist_ok=True)
MAP = '/Game/SakuraDays/Maps/L_SakuraStreet'
BASE = '/Game/SakuraDays/Environment/JapaneseTown/Prompt12'
TAG = 'SakuraDaysTownRefinement'
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def color(h):
    a = [int(h[i:i+2],16)/255 for i in (0,2,4)]
    return unreal.LinearColor(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in a],1)

def node(mat,cls,x=0,y=0,**props):
    n=MEL.create_material_expression(mat,cls,x,y)
    for k,v in props.items():n.set_editor_property(k,v)
    return n

def link(n,prop,pin=''):
    if not MEL.connect_material_property(n,pin,prop):raise RuntimeError('Material connection: '+str(prop))

def scalar(mat,value,x=0,y=0):return node(mat,unreal.MaterialExpressionConstant,x,y,r=value)

def material(name,hexcolor,pattern='',emission=0):
    fp=hashlib.sha256((name+hexcolor+pattern+str(emission)+'v2').encode()).hexdigest()[:12]
    path=BASE+'/Materials/M_'+name+'_'+fp
    if EAL.does_asset_exist(path):return unreal.load_asset(path)
    m=AT.create_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],unreal.Material,unreal.MaterialFactoryNew())
    b=node(m,unreal.MaterialExpressionConstant3Vector,-400,0,constant=color(hexcolor))
    if pattern:
        p=node(m,unreal.MaterialExpressionWorldPosition,-400,-200)
        custom=node(m,unreal.MaterialExpressionCustom,-100,0)
        ins=[]
        for name in ['P','C']:
            pin=unreal.CustomInput();pin.set_editor_property('input_name',name);ins.append(pin)
        custom.set_editor_property('inputs',ins)
        custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        if pattern=='asphalt':
            code='float2 q=floor(P.xy/2.0); float n=frac(sin(dot(q,float2(12.9898,78.233)))*43758.5453); float broad=sin(P.x*.003)*sin(P.y*.006); return C*(.95+.075*n+.025*broad);'
        elif pattern=='siding':
            code='float f=frac(P.z/18.0); float seam=smoothstep(.015,.045,f); return C*(.84+.16*seam);'
        elif pattern=='tile':
            code='float2 q=P.xy/45; q.x+=fmod(floor(q.y),2)*.5; float2 f=frac(q); float e=min(min(f.x,1-f.x),min(f.y,1-f.y)); return C*(.85+.15*smoothstep(.008,.02,e));'
        elif pattern=='blocks':
            code='float2 q=float2(P.x+P.y,P.z)/40; q.x+=fmod(floor(q.y),2)*.5; float2 f=frac(q); float e=min(min(f.x,1-f.x),min(f.y,1-f.y)); return C*(.82+.18*smoothstep(.008,.024,e));'
        else:raise ValueError(pattern)
        custom.set_editor_property('code',code)
        assert MEL.connect_material_expressions(p,'',custom,'P')
        assert MEL.connect_material_expressions(b,'',custom,'C')
        b=custom
    link(b,unreal.MaterialProperty.MP_BASE_COLOR)
    link(scalar(m,.88,-100,200),unreal.MaterialProperty.MP_ROUGHNESS)
    link(scalar(m,.12,-100,280),unreal.MaterialProperty.MP_SPECULAR)
    if emission:
        mult=node(m,unreal.MaterialExpressionMultiply,-50,-200)
        assert MEL.connect_material_expressions(b,'',mult,'A')
        assert MEL.connect_material_expressions(scalar(m,emission,-200,-300),'',mult,'B')
        link(mult,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=MEL.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    EAL.set_metadata_tag(m,'SakuraDays.TownRecipe',fp)
    EAL.save_loaded_asset(m,only_if_is_dirty=False)
    return m

class Scene:
    def __init__(self):
        assert Path(unreal.Paths.project_dir()).resolve()==ROOT
        if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Unsaved maps preserved. Save normally before this pass.')
        assert unreal.EditorLevelLibrary.load_level(MAP)
        self.actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.existing={a.get_actor_label():a for a in self.actors.get_all_level_actors()}
        self.cube=unreal.load_asset('/Engine/BasicShapes/Cube')
        self.cylinder=unreal.load_asset('/Engine/BasicShapes/Cylinder')
        self.sphere=unreal.load_asset('/Engine/BasicShapes/Sphere')
        self.placed=[]
    def actor(self,name,cls=unreal.StaticMeshActor,folder='Details'):
        label='JP_'+name
        a=self.existing.get(label)
        if a and not a.actor_has_tag(TAG):raise RuntimeError('Unowned actor preserved: '+label)
        if not a:
            a=self.actors.spawn_actor_from_class(cls,unreal.Vector())
            a.set_actor_label(label);a.set_editor_property('tags',[TAG]);self.existing[label]=a
        a.set_folder_path('SakuraDays/Prompt12/'+folder)
        return a
    def mesh(self,name,asset,p,yaw=0,scale=(1,1,1),mat=None,collision=False,folder='Details'):
        a=self.actor(name,folder=folder);c=a.static_mesh_component
        c.set_static_mesh(asset);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
        a.set_actor_location(unreal.Vector(*p),False,False)
        a.set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),False)
        a.set_actor_scale3d(unreal.Vector(*scale))
        if mat:c.set_material(0,mat)
        self.placed.append(a.get_actor_label())
        return a
    def box(self,name,p,size,mat,yaw=0,collision=False,folder='Details'):
        return self.mesh(name,self.cube,p,yaw,tuple(v/100 for v in size),mat,collision,folder)
    def beam(self,name,a,b,r,mat,folder='Utilities'):
        obj=self.mesh(name,self.cylinder,tuple((x+y)/2 for x,y in zip(a,b)),scale=(r/50,r/50,math.dist(a,b)/100),mat=mat,folder=folder)
        obj.set_actor_rotation(unreal.MathLibrary.make_rot_from_z(unreal.Vector(*[y-x for x,y in zip(a,b)])),False)
        if r<6:obj.static_mesh_component.set_cast_shadow(False)
        return obj
    def camera(self,name,p,target,fov=65):
        a=self.actor(name,unreal.CameraActor,'Cameras')
        a.set_actor_location(unreal.Vector(*p),False,False)
        a.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*p),unreal.Vector(*target)),False)
        a.camera_component.set_field_of_view(fov)
        a.camera_component.set_aspect_ratio(16/9)
        return a
    def save(self):
        if not unreal.EditorLevelLibrary.save_current_level():raise RuntimeError('Map save failed')

def transform(a):
    p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]

def import_fbx(path,folder,name):
    if EAL.does_asset_exist(folder+'/'+name):return unreal.load_asset(folder+'/'+name)
    ui=unreal.FbxImportUI();ui.import_mesh=True;ui.import_materials=False;ui.import_textures=False
    ui.import_as_skeletal=False;ui.automated_import_should_detect_type=False
    ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    d=ui.static_mesh_import_data
    d.combine_meshes=True;d.auto_generate_collision=False;d.one_convex_hull_per_ucx=True
    d.generate_lightmap_u_vs=False;d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=True
    d.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    d.normal_generation_method=unreal.FBXNormalGenerationMethod.MIKK_T_SPACE
    d.vertex_color_import_option=unreal.VertexColorImportOption.REPLACE
    t=unreal.AssetImportTask();t.filename=str(path);t.destination_path=folder;t.destination_name=name
    t.automated=True;t.replace_existing=False;t.save=False;t.options=ui;t.factory=unreal.FbxFactory()
    AT.import_asset_tasks([t])
    meshes=[o for o in t.get_objects() if isinstance(o,unreal.StaticMesh)]
    if len(meshes)!=1:raise RuntimeError('Import did not produce one mesh: '+str(path))
    return meshes[0]

def boxes(mesh,specs):
    sm=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()
    if sm.get_simple_collision_count(mesh)==0:sm.add_simple_collisions(mesh,unreal.ScriptingCollisionShapeType.BOX)
    body=mesh.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom');result=[]
    for center,size in specs:
        b=unreal.KBoxElem();b.set_editor_property('center',unreal.Vector(*center))
        for k,v in zip(('x','y','z'),size):b.set_editor_property(k,v)
        result.append(b)
    agg.set_editor_property('box_elems',result);body.set_editor_property('agg_geom',agg)
    mesh.set_editor_property('customized_collision',True)
