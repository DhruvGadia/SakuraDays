"""Build exactly one SakuraDays house and its linked modular kit. Run with Blender --background --python."""
import bpy, math, json, bmesh
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent
EXPORT=ROOT/'Exports'; PREVIEW=ROOT/'Previews'
EXPORT.mkdir(parents=True,exist_ok=True); PREVIEW.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.unit_settings.system='METRIC'; sc.unit_settings.scale_length=1.0
sc.unit_settings.length_unit='METERS'
sc.render.engine='CYCLES'; sc.cycles.samples=48
sc.cycles.use_denoising=True
sc.render.resolution_x=1600; sc.render.resolution_y=1200; sc.render.resolution_percentage=100
sc.view_settings.view_transform='Standard'
sc.view_settings.exposure=0; sc.view_settings.gamma=1
kit=bpy.data.collections.new('01_MODULE_LIBRARY'); sc.collection.children.link(kit)
house=bpy.data.collections.new('02_HOUSE01_ASSEMBLY'); sc.collection.children.link(house)
stage=bpy.data.collections.new('03_PREVIEW_ONLY'); sc.collection.children.link(stage)

def linear(h):
    rgb=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)
spec=[('M_Plaster_Cream','DDC9AD',.88),('M_Siding_BlueGray','A7B5C0',.85),
      ('M_Trim_Plum','393344',.78),('M_Roof_Slate','555B70',.85),
      ('M_Timber_Warm','725548',.8),('M_Glass_Blue','6E93AF',.48),
      ('M_Glass_Reflection','BDD0DD',.6),('M_Concrete','B8B1A9',.9)]
mats=[]
for name,color,rough in spec:
    m=bpy.data.materials.new(name);m.diffuse_color=(*linear(color),1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=0
    mats.append(m)

# Modules are closed primitive components joined into a named reusable mesh.
verts=[];faces=[];slots=[]
def reset():
    global verts,faces,slots
    verts=[];faces=[];slots=[]
def prism(points,polys,mat):
    off=len(verts);verts.extend(points);faces.extend([tuple(off+i for i in f) for f in polys]);slots.extend([mat]*len(polys))
def box(x,y,z,w,d,h,mat):
    p=[(x,y,z),(x+w,y,z),(x+w,y+d,z),(x,y+d,z),(x,y,z+h),(x+w,y,z+h),(x+w,y+d,z+h),(x,y+d,z+h)]
    prism(p,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat)
def beam(a,b,width,mat):
    a,b=Vector(a),Vector(b);axis=b-a
    v=axis.normalized().cross(Vector((0,1,0)))
    if v.length<.01:v=axis.normalized().cross(Vector((1,0,0)))
    v.normalize();u=axis.normalized().cross(v).normalized();v*=width/2;u*=width/2
    p=[tuple(q+s*v+t*u) for q in (a,b) for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    prism(p,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat)
def finish(name):
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    for m in mats:mesh.materials.append(m)
    for p,s in zip(mesh.polygons,slots):p.material_index=s
    obj=bpy.data.objects.new(name,mesh);kit.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02,area_weight=0.,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.uv_layers.active.name='UV0_Surface'
    uv2=mesh.uv_layers.new(name='UV1_Lightmap')
    for a,b in zip(mesh.uv_layers[0].data,uv2.data):b.uv=a.uv
    # Preserve explicit hard planar normals and triangulate deterministically at export.
    tri=obj.modifiers.new('Export_Triangulate','TRIANGULATE');tri.keep_custom_normals=True
    obj['module_pivot']='local bottom-left-front unless stated';obj['units']='meters'
    return obj
modules={}
def module(name,fn):
    reset();fn();modules[name]=finish(name);return modules[name]
def wall(opening=None,mat=0,siding=False):
    if opening:
        x,z,w,h=opening
        box(0,0,0,x,.18,2.8,mat);box(x+w,0,0,2-x-w,.18,2.8,mat)
        if z>0:box(x,0,0,w,.18,z,mat)
        box(x,0,z+h,w,.18,2.8-z-h,mat)
    else:box(0,0,0,2,.18,2.8,mat)
    if siding:
        for i in range(1,14):
            z=i*.2
            spans=[(0,2)]
            if opening and opening[1]<z<opening[1]+opening[3]:spans=[(0,opening[0]),(opening[0]+opening[2],2)]
            for a,b in spans:
                if b-a>.001:box(a,-.008,z,b-a,.012,.012,1)
for mat,label in [(0,'Cream'),(1,'Siding')]:
    module('SM_Wall_Solid_2m_'+label,lambda m=mat:wall(mat=m,siding=m==1))
    module('SM_Wall_Window_2m_'+label,lambda m=mat:wall((.3,.9,1.4,1.4),m,m==1))
module('SM_Wall_Entry_2m',lambda:wall((.45,0,1.1,2.2),1,True))
module('SM_Wall_BalconyDoor_2m',lambda:wall((.3,.1,1.4,2.2),0))

def window(w,h):
    t=.065
    # This assembly fits the opening; front is -Y, recess lies inside wall thickness.
    box(0,.035,0,w,.10,t,2);box(0,.035,h-t,w,.10,t,2)
    for x in [0,w/2-t/2,w-t]:box(x,.035,t,t,.10,h-2*t,2)
    for x in [t,w/2+t/2]:
        box(x,.10,t,w/2-1.5*t,.018,h-2*t,5)
        # Broad authored diagonal reflection, restrained and exportable geometry.
        x0=x+.06; x1=x+.20; low=t+.12; high=h-t-.12
        pts=[(x0,.098,low),(x1,.098,low),(min(x1+.24,x+w/2-1.6*t),.098,high),(min(x0+.24,x+w/2-1.7*t),.098,high)]
        prism(pts,[(0,1,2,3)],6)
    box(-.08,-.08,-.045,w+.16,.28,.045,7)
module('SM_Window_Slider_140x140',lambda:window(1.4,1.4))
module('SM_Window_Balcony_140x220',lambda:window(1.4,2.2))
def door():
    box(0,.045,0,1.1,.10,2.2,2)
    box(.055,.025,.05,.99,.03,2.1,4)
    for i in range(1,8):box(i*.125+.03,.018,.08,.012,.012,2.04,2)
    box(.83,-.01,.9,.025,.045,.28,2)
    box(-.06,-.03,0,.06,.21,2.24,2);box(1.1,-.03,0,.06,.21,2.24,2);box(-.06,-.03,2.2,1.22,.21,.06,2)
module('SM_Door_Entry_110x220',door)
module('SM_Foundation_2m',lambda:box(0,0,0,2,.22,.3,7))
module('SM_StoryTrim_2m',lambda:box(0,-.035,0,2,.25,.10,2))
module('SM_CornerTrim_280',lambda:(box(-.04,-.045,0,.10,.13,2.8,2),box(-.04,-.045,0,.13,.10,2.8,2)))

# 2 m repeat along roof ridge, slope runs 3.6 m out from the centerline.
def roofsection():
    pts=[(0,0,1.35),(2,0,1.35),(2,3.6,0),(0,3.6,0),(0,0,1.23),(2,0,1.23),(2,3.6,-.12),(0,3.6,-.12)]
    prism(pts,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],3)
    box(0,3.52,-.18,2,.12,.19,2)
    for i in range(1,7):
        y=i*.5;z=1.35-y*1.35/3.6
        beam((0,y,z+.014),(2,y,z+.014),.025,3)
module('SM_Roof_Slope_2m',roofsection)
module('SM_Roof_Ridge_2m',lambda:box(0,-.105,0,2,.21,.14,2))
def gable():
    pts=[(0,0,0),(0,6,0),(0,3,1.125),(.18,0,0),(.18,6,0),(.18,3,1.125)]
    prism(pts,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],0)
module('SM_Gable_End_6m',gable)
def roofedge():
    beam((0,-.6,0),(0,3,1.35),.14,2);beam((0,3,1.35),(0,6.6,0),.14,2)
module('SM_Roof_Bargeboard',roofedge)
def balcony():
    box(0,0,0,2,1,.13,7)
    box(0,-.03,.13,2,.08,.16,2)
    for x in [i*.2 for i in range(11)]:box(x-.015,-.015,.29,.03,.03,.78,2)
    box(-.025,-.04,1.06,2.05,.08,.06,2)
module('SM_Balcony_2m',balcony)
def canopy():
    box(0,0,0,2,.85,.10,3);box(0,-.025,-.055,2,.07,.13,2)
    for x in [.15,1.85]:beam((x,.8,-.6),(x,.08,-.03),.05,2)
module('SM_Entry_Canopy_2m',canopy)
def ac():
    box(0,0,0,.85,.32,.60,7);box(.05,-.015,.06,.49,.02,.48,2)
    for z in [.1+i*.055 for i in range(8)]:box(.065,-.026,z,.46,.02,.018,1)
    for x in [.61,.67,.73]:box(x,-.016,.08,.025,.02,.43,1)
    for x in [.12,.70]:box(x,.06,-.08,.05,.35,.08,2)
module('SM_AC_Outdoor_85',ac)
def gutter():
    box(0,0,0,2,.15,.06,2);box(0,-.025,0,2,.025,.12,2)
module('SM_Gutter_2m',gutter)
module('SM_Downpipe_280',lambda:box(0,0,0,.075,.075,2.8,2))
module('SM_Entry_Step',lambda:(box(0,0,0,1.8,.9,.15,7),box(0,.3,.15,1.8,.6,.15,7)))

assembly=[]
def inst(key,label,pos,angle=0):
    proto=modules[key];obj=bpy.data.objects.new('H01_'+label,proto.data);house.objects.link(obj)
    obj.location=pos;obj.rotation_euler.z=math.radians(angle)
    obj['module']=key;obj['front_axis']='local -Y';obj['source']='SakuraDays House01'
    tri=obj.modifiers.new('Export_Triangulate','TRIANGULATE');tri.keep_custom_normals=True
    assembly.append(obj);return obj
def facepos(side,bay,z):
    return {'Front':((-4+2*bay,-3,z),0),'Right':((4,-3+2*bay,z),90),
            'Back':((4-2*bay,3,z),180),'Left':((-4,3-2*bay,z),-90)}[side]
def offset(pos,angle,dx,dy,dz):
    return Vector(pos)+Matrix.Rotation(math.radians(angle),4,'Z')@Vector((dx,dy,dz))
for side,n in [('Front',4),('Right',3),('Back',4),('Left',3)]:
    for bay in range(n):
        p,a=facepos(side,bay,0);inst('SM_Foundation_2m',f'{side}_Foundation_{bay}',p,a)
        for floor in range(2):
            z=.3+floor*2.8;p,a=facepos(side,bay,z)
            label=f'{side}_L{floor+1}_Bay{bay+1}'
            kind='Window' if (side in ['Front','Right'] or bay%2==0) else 'Solid'
            if side=='Front' and bay==1 and floor==0:
                key='SM_Wall_Entry_2m';inst('SM_Door_Entry_110x220',label+'_Door',offset(p,a,.45,0,0),a)
            elif side=='Front' and bay in (1,2) and floor==1:
                key='SM_Wall_BalconyDoor_2m';inst('SM_Window_Balcony_140x220',label+'_BalconyDoor',offset(p,a,.3,0,.1),a)
            else:
                key='SM_Wall_'+kind+'_2m_'+('Cream' if floor else 'Siding')
                if kind=='Window':inst('SM_Window_Slider_140x140',label+'_Window',offset(p,a,.3,0,.9),a)
            inst(key,label+'_Wall',p,a)
            p,a=facepos(side,bay,z);inst('SM_StoryTrim_2m',label+'_Trim',p,a)
for floor in range(2):
    for i,(x,y,a) in enumerate([(-4,-3,0),(4,-3,90),(4,3,180),(-4,3,-90)]):
        inst('SM_CornerTrim_280',f'Corner{i}_L{floor+1}',(x,y,.3+floor*2.8),a)
# Roof strips include 0.4 m end overhang. End strips are scaled mesh copies, preserving object scale 1.
roof_bays=[(-4.4,.4),(-4,2),(-2,2),(0,2),(2,2),(4,.4)]
for side,angle in [('Back',0),('Front',180)]:
    for j,(x,width) in enumerate(roof_bays):
        obj=inst('SM_Roof_Slope_2m',f'Roof_{side}_{j}',(x if angle==0 else x+width,0,5.675),angle)
        obj.data=obj.data.copy()
        for v in obj.data.vertices:v.co.x*=width/2
for j,(x,width) in enumerate(roof_bays):
    obj=inst('SM_Roof_Ridge_2m',f'Ridge_{j}',(x,0,7.025))
    obj.data=obj.data.copy()
    for v in obj.data.vertices:v.co.x*=width/2
inst('SM_Gable_End_6m','Gable_Left',(-4.002,-3,5.78))
inst('SM_Gable_End_6m','Gable_Right',(3.822,-3,5.78))
for x in [-4.4,4.4]:inst('SM_Roof_Bargeboard',f'Barge_{x}',(x,-3,5.675))
for j in range(4):
    inst('SM_Gutter_2m',f'Gutter_Front{j}',(-4+j*2,-3.64,5.55))
    inst('SM_Gutter_2m',f'Gutter_Back{j}',(4-j*2,3.64,5.55),180)
for x in [-3.86,3.86]:
    for z in [.2,3]:inst('SM_Downpipe_280',f'Pipe_{x}_{z}',(x,-3.18,z))
for j in range(2):inst('SM_Balcony_2m',f'Balcony{j}',(-2+j*2,-4,3.03))
# Separate end rails keep balcony slabs from being duplicated.
def side_rail():
    for y in [i*.2 for i in range(6)]:box(-.015,y,.13,.03,.03,.94,2)
    box(-.04,0,1.06,.08,1,.06,2)
module('SM_Balcony_EndRail_1m',side_rail)
for x in [-2,2]:inst('SM_Balcony_EndRail_1m',f'BalconyRail_{x}',(x,-4,3.03))
inst('SM_Entry_Canopy_2m','EntranceCanopy',(-2,-3.85,2.63))
inst('SM_Entry_Step','EntranceStep',(-1.9,-3.9,0))
inst('SM_AC_Outdoor_85','AC_Right',(4.02,-1.8,1.15),90)

# Library prototypes are hidden; linked assembly instances remain visible.
for o in kit.objects:o.hide_render=True;o.hide_set(True)

def bounds(objects):
    bpy.context.view_layer.update()
    pts=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    return {'min':lo,'max':hi,'dimensions':[hi[i]-lo[i] for i in range(3)]}

fbx_args=dict(use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,
    mesh_smooth_type='FACE',use_triangles=True,bake_anim=False,path_mode='AUTO',use_custom_props=True)
def export(path,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.fbx(filepath=str(path),**fbx_args)
def export_assembled():
    # Preserve linked source modules while giving the combined FBX a unique lightmap atlas.
    original={o:o.data for o in assembly};grid=math.ceil(math.sqrt(len(assembly)))
    for i,o in enumerate(assembly):
        o.data=o.data.copy()
        for loop in o.data.uv_layers[1].data:
            u,v=loop.uv;loop.uv=((i%grid+.02+.96*u)/grid,(i//grid+.02+.96*v)/grid)
    export(EXPORT/'SM_SakuraHouse01_Assembled.fbx',assembly)
    for o,data in original.items():
        temp=o.data;o.data=data;bpy.data.meshes.remove(temp)
export_assembled()
for name,obj in modules.items():
    export(EXPORT/(name+'.fbx'),[obj]);obj.hide_set(True)
report={'blender':bpy.app.version_string,'unit_system':'METRIC','meters_per_unit':1,
    'front_axis_blender':'-Y','up_axis':'Z','body_dimensions_m':[8,6,5.9],
    'assembled_bounds_m':bounds(assembly),'assembly_objects':len(assembly),'modules':{},
    'material_slots':[m.name for m in mats],'export_settings':fbx_args}
report['assembled_fbx_uv1']='Unique 12x12 per-object lightmap atlas; source modules retain local UVs'
report['export_settings']['object_types']=['MESH']
for name,obj in modules.items():
    obj.data.calc_loop_triangles()
    uv=obj.data.uv_layers[0]
    report['modules'][name]={'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles),
        'bounds_local_m':bounds([obj]),'uv_layers':[u.name for u in obj.data.uv_layers],
        'uv_in_unit_square':all(-.00001<=v<=1.00001 for d in uv.data for v in d.uv),
        'scale':list(obj.scale),'pivot_local_m':[0,0,0]}
report['assembled_triangles']=sum(len(o.data.loop_triangles) or (o.data.calc_loop_triangles() or len(o.data.loop_triangles)) for o in assembly)
(ROOT/'build_manifest.json').write_text(json.dumps(report,indent=2))

# Preview stage is never included in FBX exports.
def move_to_stage(obj):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    stage.objects.link(obj)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));ground=bpy.context.object;ground.name='PREVIEW_Ground';move_to_stage(ground)
ground.data.materials.append(mats[7])
world=bpy.data.worlds.new('Preview_BlueFill');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.48,.65,.85,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.65;sc.world=world
ld=bpy.data.lights.new('Preview_Sun','SUN');ld.energy=2.2;ld.angle=math.radians(2)
sun=bpy.data.objects.new('Preview_Sun',ld);stage.objects.link(sun);sun.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-35))
camd=bpy.data.cameras.new('Preview_Camera');cam=bpy.data.objects.new('Preview_Camera',camd);stage.objects.link(cam);sc.camera=cam
def camera(pos,target,ortho=13.8):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    camd.type='ORTHO';camd.ortho_scale=ortho;camd.lens=50
camera((12,-17,11),(0,-.2,3.3))
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.object.select_all(action='DESELECT')
sc['asset']='SakuraDays House01 inspection candidate; exterior only'
sc['front']='-Y; Z up; 1 Blender unit = 1 meter'
sc['library']='01_MODULE_LIBRARY contains hidden reusable prototypes; assembly meshes are linked except roof-length variants'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SakuraHouse01.blend'))
sc.render.filepath=str(PREVIEW/'House01_ThreeQuarter.png');bpy.ops.render.render(write_still=True)
camera((-12,15,10),(0,0,3.3));sc.render.filepath=str(PREVIEW/'House01_Rear.png');bpy.ops.render.render(write_still=True)
camera((0,-20,3.6),(0,0,3.6),10.8);sc.render.filepath=str(PREVIEW/'House01_Front.png');bpy.ops.render.render(write_still=True)
print('SAKURA_HOUSE_BUILD_COMPLETE '+str(ROOT))
