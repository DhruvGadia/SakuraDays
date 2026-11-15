"""Build one SakuraDays cafe and one prop set. Blender --background --python.
Generated outputs stay beside this script; preserve hand edits before rebuilding.
"""
import bpy, bmesh, math, json, sys
sys.dont_write_bytecode=True
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
for sub in ('Exports','Previews'): (ROOT/sub).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
sc.render.engine='CYCLES';sc.cycles.samples=16 if '--draft' in sys.argv else 48
sc.cycles.use_denoising=True
sc.render.resolution_percentage=60 if '--draft' in sys.argv else 100
sc.render.image_settings.file_format='PNG'
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=-.35
def coll(name):
    c=bpy.data.collections.new(name);sc.collection.children.link(c);return c
library=coll('01_MODULE_LIBRARY');assembly=coll('02_CAFE_ASSEMBLY');stage=coll('03_PREVIEW_ONLY');texts=coll('04_EDITABLE_SIGN_TEXT')
def linear(h):
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in [int(h[i:i+2],16)/255 for i in (0,2,4)])
spec={'plaster':'DDC9AD','wood':'80614F','trim':'393344','roof':'596276','rose':'BF7B8A',
      'glass':'717C8C','reflection':'B9C7D1','stone':'B8B1A9','metal':'484C58',
      'leaf':'648954','leaf_light':'8DA767','terracotta':'B27C65','soil':'554B49','paper':'EEE1CA','lamp':'E6C18C','chalk':'414651'}
mats={}
for key,color in spec.items():
    m=bpy.data.materials.new('M_Cafe_'+key.title());m.use_nodes=True;m.diffuse_color=(*linear(color),1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color
    p.inputs['Roughness'].default_value=.82;p.inputs['Specular IOR Level'].default_value=.2
    if key=='lamp':p.inputs['Emission Color'].default_value=m.diffuse_color;p.inputs['Emission Strength'].default_value=.3
    mats[key]=m

V=[];F=[];S=[]
def reset():
    V.clear();F.clear();S.clear()
def poly(points,faces,mat):
    off=len(V);V.extend(tuple(p) for p in points);F.extend(tuple(off+i for i in f) for f in faces);S.extend([mat]*len(faces))
def box(x,y,z,w,d,h,mat):
    poly([(x,y,z),(x+w,y,z),(x+w,y+d,z),(x,y+d,z),(x,y,z+h),(x+w,y,z+h),(x+w,y+d,z+h),(x,y+d,z+h)],
         [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat)
def beam(a,b,w,mat):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,1,0)))
    if u.length<.01:u=axis.cross(Vector((1,0,0)))
    u.normalize();v=axis.cross(u);u*=w/2;v*=w/2
    poly([q+i*u+j*v for q in (a,b) for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]],[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat)
def disk(x,y,z,rx,rz,depth,mat,n=24):
    pts=[(x+rx*math.cos(i*math.tau/n),yy,z+rz*math.sin(i*math.tau/n)) for yy in (y,y+depth) for i in range(n)]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    poly(pts,faces,mat)
def finish(name):
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(V,[],F);mesh.update()
    keys=list(dict.fromkeys(S))
    for k in keys:mesh.materials.append(mats[k])
    for p,k in zip(mesh.polygons,S):p.material_index=keys.index(k)
    obj=bpy.data.objects.new(name,mesh);library.objects.link(obj);return obj
modules={}
def module(name,fn):
    reset();fn();obj=finish(name);modules[name]=obj;return obj
def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
def prepare(obj):
    activate(obj)
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.015,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT');obj.data.uv_layers.active.name='UV0_Surface'
    uv1=obj.data.uv_layers.new(name='UV1_Lightmap')
    for a,b in zip(obj.data.uv_layers[0].data,uv1.data):b.uv=a.uv
    obj['units']='meters; Z up; display front -Y'
    obj['pivot']='Facade module bottom-left on wall plane; props at ground center; awning at upper rear-left wall anchor'
    obj.data.calc_loop_triangles()

def wall(opening=None,upper=False):
    h=2.7 if upper else 3.2
    if opening:
        x,z,w,oh=opening
        box(0,0,0,x,.18,h,'plaster');box(x+w,0,0,2-x-w,.18,h,'plaster')
        if z>0:box(x,0,0,w,.18,z,'wood' if not upper else 'plaster')
        box(x,0,z+oh,w,.18,h-z-oh,'plaster')
    else:box(0,0,0,2,.18,h,'plaster')
    if not upper:
        box(0,-.035,0,2,.24,.16,'stone')
        for x in (0,1.93):box(x,-.045,.16,.07,.26,h-.16,'trim')
module('SM_Cafe_Wall_Window_2m',lambda:wall((.16,.6,1.68,2.05)))
module('SM_Cafe_Wall_Door_2m',lambda:wall((.35,.05,1.3,2.6)))
module('SM_Cafe_Wall_Solid_2m',lambda:wall())
module('SM_Cafe_Upper_Window_2m',lambda:wall((.40,.70,1.2,1.35),True))
module('SM_Cafe_Upper_Solid_2m',lambda:wall(upper=True))

def window(w,h):
    t=.065
    box(0,.05,0,w,.12,h,'trim')
    # Broad opaque glazing with a subtle warm lower register; exterior-only.
    box(t,.035,t,w-2*t,.018,h-2*t,'glass')
    for x in (.0,w/2-t/2,w-t):box(x,-.015,0,t,.11,h,'wood')
    for z in (0,h*.25,h*.72,h-t):box(0,-.018,z,w,.115,t,'wood')
    for x in (.1,w/2+.05):
        p=[(x,.012,h*.35),(x+.045,.012,h*.35),(min(x+.34,w-.09),.012,h*.86),(min(x+.28,w-.1),.012,h*.86)]
        poly(p,[(0,1,2,3)],'reflection')
    box(-.045,-.10,-.035,w+.09,.30,.05,'wood')
module('SM_Cafe_Window_168x205',lambda:window(1.68,2.05))
module('SM_Cafe_Window_120x135',lambda:window(1.2,1.35))
def door():
    box(0,.02,0,1.3,.12,2.6,'trim');box(.06,-.005,.06,1.18,.03,2.48,'wood')
    box(.13,-.012,.75,1.04,.015,1.63,'glass')
    for x in (.13,.62,1.12):box(x,-.04,.75,.05,.065,1.63,'wood')
    box(.13,-.04,1.93,1.04,.065,.055,'wood')
    for x in (.14,.42,.70,.98):box(x,-.02,.12,.025,.02,.50,'trim')
    beam((1.12,-.10,.9),(1.12,-.10,1.25),.032,'metal')
module('SM_Cafe_Door_130x260',door)
def awning():
    poly([(0,.03,.08),(2,.03,.08),(2,-1.2,-.22),(0,-1.2,-.22),(0,.03,.025),(2,.03,.025),(2,-1.2,-.275),(0,-1.2,-.275)],
         [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],'rose')
    beam((0,-1.2,-.22),(2,-1.2,-.22),.035,'paper')
    for i in range(8):
        left=i*.25
        outline=[(left,-1.21,-.23),(left+.25,-1.21,-.23)]
        for j in range(7):
            a=j*math.pi/6
            outline.append((left+.125+.125*math.cos(a),-1.21,-.35-.095*math.sin(a)))
        pts=outline+[(x,y+.025,z) for x,y,z in outline];n=len(outline)
        poly(pts,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],'rose')
    for x in (.08,1.92):beam((x,0,-.6),(x,-1.15,-.25),.025,'metal')
module('SM_Cafe_Awning_2m',awning)
module('SM_Cafe_StoryTrim_2m',lambda:box(0,-.06,0,2,.28,.16,'trim'))
module('SM_Cafe_Foundation_2m',lambda:box(0,0,0,2,.26,.18,'stone'))
module('SM_Cafe_CornerTrim_3m',lambda:box(-.035,-.04,0,.11,.11,3.2,'wood'))
def roof():
    poly([(0,0,1),(2,0,1),(2,2.9,0),(0,2.9,0),(0,0,.9),(2,0,.9),(2,2.9,-.1),(0,2.9,-.1)],
         [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],'roof')
    box(0,2.86,-.16,2,.10,.17,'trim')
    for y in (.5,1,1.5,2,2.5):beam((0,y,1-y/2.9+.01),(2,y,1-y/2.9+.01),.018,'roof')
module('SM_Cafe_RoofSlope_2m',roof)
module('SM_Cafe_Ridge_2m',lambda:box(0,-.1,0,2,.2,.13,'trim'))
def gable():
    poly([(0,0,0),(0,5,0),(0,2.5,.862),(.16,0,0),(.16,5,0),(.16,2.5,.862)],[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],'plaster')
module('SM_Cafe_Gable_5m',gable)
module('SM_Cafe_Bargeboard_5m',lambda:(beam((0,-2.9,0),(0,0,1),.12,'trim'),beam((0,0,1),(0,2.9,0),.12,'trim')))
module('SM_Cafe_Gutter_2m',lambda:(box(0,0,0,2,.14,.07,'metal'),box(0,-.02,0,2,.025,.12,'metal')))
module('SM_Cafe_Downpipe_3m',lambda:box(-.035,-.035,0,.07,.07,3,'metal'))

def text_mesh(owner,text,center,size,material='paper'):
    data=bpy.data.curves.new(owner.name+'_Type','FONT');data.body=text;data.size=size;data.align_x='CENTER';data.align_y='CENTER'
    data.extrude=.0006;data.resolution_u=2
    source=bpy.data.objects.new(owner.name+'_Editable_'+str(len(texts.objects)),data);texts.objects.link(source)
    source.location=center;source.rotation_euler.x=math.pi/2;data.materials.append(mats[material]);source.hide_render=True;source.hide_set(True)
    obj=source.copy();obj.data=source.data.copy();library.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
    activate(obj);bpy.ops.object.convert(target='MESH')
    obj=bpy.context.object;obj.select_set(True);owner.select_set(True);bpy.context.view_layer.objects.active=owner;bpy.ops.object.join()
def sign():
    box(-1.55,0,0,3.1,.12,.58,'trim');box(-1.48,-.018,.055,2.96,.022,.47,'paper')
sign_obj=module('SM_Cafe_FasciaSign',sign)
text_mesh(sign_obj,'H A N A',(0,-.045,.365),.26,'trim');text_mesh(sign_obj,'COFFEE  +  TEA',(0,-.045,.15),.085,'wood')
def round_sign():
    beam((0,0,.85),(0,-.72,.85),.04,'metal');beam((0,0,.5),(0,-.65,.85),.025,'metal')
    disk(0,-.75,.4,.32,.32,.075,'trim');disk(0,-.77,.4,.285,.285,.02,'paper')
    for i in range(5):
        a=i*math.tau/5;disk(math.sin(a)*.082,-.79,.44+math.cos(a)*.082,.055,.055,.005,'rose',12)
round_obj=module('SM_Cafe_RoundSign',round_sign);text_mesh(round_obj,'HANA',(0,-.80,.26),.085,'trim')
def board():
    for x in (-.31,.31):
        beam((x,-.26,0),(x,0,1.08),.045,'wood');beam((x,.30,0),(x,0,1.08),.045,'wood')
    box(-.34,-.16,.20,.68,.045,.80,'wood');box(-.285,-.173,.255,.57,.012,.69,'chalk')
    beam((-.3,.15,.4),(.3,.15,.4),.025,'metal')
board_obj=module('SM_Cafe_MenuBoard',board)
for v in board_obj.data.vertices:v.co.z=max(0.,v.co.z)
for t,z,s in [('HANA',.82,.12),('COFFEE',.63,.072),('TEA',.48,.072),('CAKE',.33,.072)]:text_mesh(board_obj,t,(0,-.188,z),s)

from prop_build import create_props
modules.update(create_props(mats,library))
for obj in modules.values():prepare(obj)

placed=[]
def inst(key,label,pos,angle=0,scale_x=1):
    proto=modules[key];o=bpy.data.objects.new('CAFE_'+label,proto.data);assembly.objects.link(o)
    o.location=pos;o.rotation_euler.z=math.radians(angle)
    if scale_x!=1:
        o.data=o.data.copy()
        for v in o.data.vertices:v.co.x*=scale_x
    o['module']=key;placed.append(o);return o
for bay in range(3):
    x=-3+bay*2
    inst('SM_Cafe_Wall_Door_2m' if bay==1 else 'SM_Cafe_Wall_Window_2m',f'Front_Bay{bay}',(x,-2.5,.18))
    if bay==1:inst('SM_Cafe_Door_130x260','FrontDoor',(x+.35,-2.5,.23))
    else:inst('SM_Cafe_Window_168x205',f'DisplayWindow{bay}',(x+.16,-2.5,.78))
    inst('SM_Cafe_Awning_2m',f'Awning{bay}',(x,-2.5,3.12))
    inst('SM_Cafe_Upper_Window_2m',f'UpperFront{bay}',(x,-2.5,3.38))
    inst('SM_Cafe_Window_120x135',f'UpperWindow{bay}',(x+.4,-2.5,4.08))
    inst('SM_Cafe_StoryTrim_2m',f'FrontTrim{bay}',(x,-2.5,3.38))
    inst('SM_Cafe_Foundation_2m',f'FrontBase{bay}',(x,-2.5,0))
    for level in (0,1):
        inst('SM_Cafe_Wall_Solid_2m' if level==0 else 'SM_Cafe_Upper_Solid_2m',f'Rear{bay}_{level}',(3-bay*2,2.5,.18 if level==0 else 3.38),180)
    for side,a,y in [('Back',0,0),('Front',180,0)]:
        inst('SM_Cafe_RoofSlope_2m',f'Roof{side}{bay}',(x if not a else x+2,0,5.94),a)
    inst('SM_Cafe_Ridge_2m',f'Ridge{bay}',(x,0,6.94))
    inst('SM_Cafe_Gutter_2m',f'Gutter{bay}',(x,-2.96,5.77))
for side,x,a in [('Right',3,90),('Left',-3,-90)]:
    for bay,(offset,width) in enumerate([(0,2),(2,2),(4,1)]):
        y=-2.5+offset if a==90 else 2.5-offset
        for level in (0,1):
            inst('SM_Cafe_Wall_Solid_2m' if level==0 else 'SM_Cafe_Upper_Solid_2m',f'{side}{bay}_{level}',(x,y,.18 if level==0 else 3.38),a,width/2)
        inst('SM_Cafe_Foundation_2m',f'{side}Base{bay}',(x,y,0),a,width/2)
    inst('SM_Cafe_Gable_5m',side+'Gable',(x-.08,-2.5,5.958))
    for h in (0,3):inst('SM_Cafe_Downpipe_3m',f'{side}Drain{h}',(x-.12,-2.65,h))
# Extend the same roof modules across each gable; dark bargeboards close the ends.
for side,x in [('Left',-3.2),('Right',3)]:
    inst('SM_Cafe_RoofSlope_2m',side+'RoofOverhangBack',(x,0,5.94),0,.1)
    inst('SM_Cafe_RoofSlope_2m',side+'RoofOverhangFront',(x+.2,0,5.94),180,.1)
    inst('SM_Cafe_Ridge_2m',side+'RidgeOverhang',(x,0,6.94),0,.1)
    inst('SM_Cafe_Bargeboard_5m',side+'RoofEdge',(-3.21 if side=='Left' else 3.21,0,5.94))
inst('SM_Cafe_FasciaSign','MainSign',(0,-2.59,3.48))
inst('SM_Cafe_RoundSign','HangingSign',(-2.6,-2.5,3.05))
inst('SM_Cafe_Bench','Bench',(-2.4,-3.40,0))
inst('SM_Cafe_Table','TerraceTable',(2.1,-4.2,0))
inst('SM_Cafe_Chair','ChairLeft',(1.28,-4.2,0),90)
inst('SM_Cafe_Chair','ChairRight',(2.92,-4.2,0),-90)
inst('SM_Cafe_PottedPlant','DoorPlant',(1.05,-2.95,0))
inst('SM_Cafe_PottedPlant','CornerPlant',(-3.3,-2.9,0))
inst('SM_Cafe_Planter','SidePlanter',(3.55,.5,0),90)
inst('SM_Cafe_MenuBoard','Menu',(-1.1,-3.85,0),-8)
inst('SM_Cafe_StreetLamp','StreetLamp',(4.1,-3.1,0))
inst('SM_Cafe_AC','ServiceAC',(3.05,1.7,.35),90)

def bounds(o):
    bpy.context.view_layer.update();pts=[o.matrix_world@v.co for v in o.data.vertices]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    return {'min':lo,'max':hi,'dimensions':[hi[i]-lo[i] for i in range(3)]}
def record(o):
    o.data.calc_loop_triangles();return {'triangles':len(o.data.loop_triangles),'bounds_m':bounds(o),'material_slots':[m.name for m in o.data.materials]}
def export(o):
    activate(o)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Exports'/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',global_scale=1,axis_forward='-Y',axis_up='Z',
        use_triangles=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE',use_custom_props=True)
report={'blender':bpy.app.version_string,'meters_per_unit':1,'modules':{},'assembly_instances':len(placed),
    'materials':spec,'front_axis_blender':'-Y','up_axis':'Z','collision':'No gameplay collision authored; add deliberate simple proxies at integration'}
for name,o in modules.items():
    report['modules'][name]=record(o);export(o);o.hide_set(True);o.hide_render=True
# Temporary single-mesh export with unique per-instance lightmap cells.
temp=[];grid=math.ceil(math.sqrt(len(placed)))
for i,o in enumerate(placed):
    copy=o.copy();copy.data=o.data.copy();library.objects.link(copy);copy.hide_set(False);temp.append(copy)
    for loop in copy.data.uv_layers[1].data:
        u,v=loop.uv;loop.uv=((i%grid+.03+.94*u)/grid,(i//grid+.03+.94*v)/grid)
bpy.ops.object.select_all(action='DESELECT')
for o in temp:o.select_set(True)
bpy.context.view_layer.objects.active=temp[0];bpy.ops.object.join();joined=bpy.context.object
sc.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
joined.name='SM_Cafe01_Assembled';report['assembled']=record(joined);report['assembled']['uv1_grid']=grid
export(joined);bpy.data.objects.remove(joined,do_unlink=True)
(ROOT/'build_manifest.json').write_text(json.dumps(report,indent=2))

# Preview-only sidewalk and daylight. Never in FBX exports.
def to_stage(o):
    for c in list(o.users_collection):c.objects.unlink(o)
    stage.objects.link(o)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.07));ground=bpy.context.object;ground.name='PREVIEW_Ground';to_stage(ground);ground.data.materials.append(mats['stone'])
world=bpy.data.worlds.new('PREVIEW_Sky');world.use_nodes=True;sc.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.64,.76,1,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65
ld=bpy.data.lights.new('PREVIEW_Sun','SUN');ld.energy=2.1;ld.angle=math.radians(3)
sun=bpy.data.objects.new('PREVIEW_Sun',ld);stage.objects.link(sun);sun.rotation_euler=(math.radians(29),math.radians(-23),math.radians(-30))
camd=bpy.data.cameras.new('PREVIEW_Camera');cam=bpy.data.objects.new('PREVIEW_Camera',camd);stage.objects.link(cam);sc.camera=cam
camd.type='ORTHO'
def camera(pos,target,scale):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=scale
def render(name,w=1600,h=1200):
    sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.filepath=str(ROOT/'Previews'/name)
    if '--no-render' not in sys.argv:bpy.ops.render.render(write_still=True)
camera((11,-17,10),(0,-.4,3.05),12.5)
sc.render.resolution_x=1600;sc.render.resolution_y=1200
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
sc['scope']='One modular cafe exterior + one prop set for review. Original HANA signage. No interior/gameplay/variations.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Cafe01.blend'))
render('Cafe01_ThreeQuarter.png')
camera((0,-20,4),(0,-1,3.4),10.5);render('Cafe01_Front.png')
camera((7,-13,5),(0,-2.8,1.8),8.1);render('Cafe01_Entrance.png',1600,1000)
# Same props in an uncluttered lineup, not alternative designs.
for o in placed:o.hide_render=True
preview_props=[]
for name,pos in [('Chair',(-3,-1,0)),('Table',(-1.4,-1,0)),('Bench',(1,-1,0)),('PottedPlant',(3,-1,0)),('Planter',(-2,1.4,0)),('MenuBoard',(.0,1.4,0)),('AC',(1.5,1.4,0)),('StreetLamp',(3.1,2,0))]:
    o=bpy.data.objects.new('PREVIEW_'+name,modules['SM_Cafe_'+name].data);stage.objects.link(o);o.location=pos;preview_props.append(o)
camera((7,-14,9),(0,.5,1.1),9.6);render('Cafe01_PropSet.png',1600,1100)
print('CAFE01_BUILD_COMPLETE '+str(ROOT),flush=True)
