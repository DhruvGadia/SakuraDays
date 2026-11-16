"""Original SakuraDays Japanese neighborhood modules. Blender background Python.

All text is authored Unicode, never generated lettering. Yu Gothic is read from
the host OS and converted to outlines; no font file is copied or packed.
Run --no-render for asset-only rebuild; preserve hand edits before rebuilding.
"""
import bpy, bmesh, math, json, struct, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
for sub in ('Exports','Previews'): (ROOT/sub).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
sc.render.image_settings.file_format='PNG';sc.render.resolution_percentage=100
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.view_settings.exposure=-.4
def collection(name):
    c=bpy.data.collections.new(name);sc.collection.children.link(c);return c
lib=collection('01_REUSABLE_MODULES');assembled=collection('02_RAMEN_ASSEMBLY')
texts=collection('03_EDITABLE_JAPANESE_TEXT');stage=collection('04_PREVIEW_ONLY')
FONT=Path('C:/Windows/Fonts/YuGothB.ttc')

def font_coverage(path,chars):
    """Read SFNT Unicode cmap directly, including TTC first-face offsets."""
    raw=path.read_bytes();u16=lambda p:struct.unpack_from('>H',raw,p)[0]
    u32=lambda p:struct.unpack_from('>I',raw,p)[0]
    sfnt=u32(12) if raw[:4]==b'ttcf' else 0
    tables={raw[sfnt+12+i*16:sfnt+16+i*16].decode('ascii'):(u32(sfnt+20+i*16),u32(sfnt+24+i*16)) for i in range(u16(sfnt+4))}
    base=tables['cmap'][0];subtables=[]
    for i in range(u16(base+2)):
        row=base+4+i*8;platform=u16(row);encoding=u16(row+2);p=base+u32(row+4)
        if platform==0 or (platform==3 and encoding in (1,10)):subtables.append(p)
    def glyph(code):
        for p in subtables:
            fmt=u16(p)
            if fmt==12:
                for i in range(u32(p+12)):
                    q=p+16+i*12;start,end,first=struct.unpack_from('>III',raw,q)
                    if start<=code<=end:return first+code-start
            if fmt==4 and code<65536:
                n=u16(p+6)//2;ends=p+14;starts=ends+2*n+2;deltas=starts+2*n;ranges=deltas+2*n
                for i in range(n):
                    if u16(starts+2*i)<=code<=u16(ends+2*i):
                        delta=u16(deltas+2*i);offset=u16(ranges+2*i)
                        if offset==0:return (code+delta)&65535
                        g=u16(ranges+2*i+offset+2*(code-u16(starts+2*i)))
                        return ((g+delta)&65535) if g else 0
        return 0
    result={c:glyph(ord(c)) for c in sorted(set(chars)) if not c.isspace()}
    missing=[c for c,v in result.items() if not v]
    if missing:raise RuntimeError('Japanese font lacks glyphs: '+repr(missing))
    return result

STRINGS=['喫茶 花','HANA','ラーメン','営業中','さくら通り','掲示板','止まれ','P','COFFEE + TEA']
coverage=font_coverage(FONT,''.join(STRINGS))
font=bpy.data.fonts.load(str(FONT))
PALETTE={'Plaster':'D9C8AD','Siding':'8D9DAB','Timber':'705447','Trim':'393344','Roof':'535B6D',
 'Glass':'6F8EA4','Reflection':'B6CCD8','Stone':'B2ACA5','Metal':'5D6470','Paper':'F0E3CC',
 'RamenRed':'B74A44','Noren':'963C3F','VendingRed':'BD504E','Sage':'6F9581','Leaf':'64895D',
 'Lamp':'EDC894','Tire':'34343C','Bicycle':'648B91','Yellow':'D8B64D','White':'E5E3DA','Blue':'477D9A'}
def linear(h):return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in [int(h[i:i+2],16)/255 for i in (0,2,4)])
M={}
for k,h in PALETTE.items():
    m=bpy.data.materials.new('M_Town_'+k);m.use_nodes=True;m.diffuse_color=(*linear(h),1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color
    p.inputs['Roughness'].default_value=.82;p.inputs['Specular IOR Level'].default_value=.18
    M[k]=m
V=[];F=[];S=[];modules={};sign_content={}
def reset():V.clear();F.clear();S.clear()
def poly(points,faces,key):
    off=len(V);V.extend(tuple(p) for p in points);F.extend(tuple(off+i for i in f) for f in faces);S.extend([key]*len(faces))
def box(x,y,z,w,d,h,key):
    poly([(x,y,z),(x+w,y,z),(x+w,y+d,z),(x,y+d,z),(x,y,z+h),(x+w,y,z+h),(x+w,y+d,z+h),(x,y+d,z+h)],[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],key)
def beam(a,b,r,key,n=8):
    a,b=Vector(a),Vector(b);d=(b-a).normalized();u=d.cross(Vector((0,1,0)))
    if u.length<.01:u=d.cross(Vector((1,0,0)))
    u.normalize();v=d.cross(u)
    pts=[q+r*(math.cos(i*math.tau/n)*u+math.sin(i*math.tau/n)*v) for q in (a,b) for i in range(n)]
    poly(pts,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],key)
def disk(x,y,z,r,depth,key,n=32):beam((x,y,z),(x,y+depth,z),r,key,n)
def ring(x,y,z,outer,inner,depth,key,n=32):
    pts=[(x+r*math.cos(i*math.tau/n),yy,z+r*math.sin(i*math.tau/n)) for yy in (y,y+depth) for r in (outer,inner) for i in range(n)]
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    poly(pts,faces,key)
def finish(name,coll=lib):
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(V,[],F);mesh.update()
    keys=list(dict.fromkeys(S))
    for k in keys:mesh.materials.append(M[k])
    for p,k in zip(mesh.polygons,S):p.material_index=keys.index(k)
    ob=bpy.data.objects.new(name,mesh);coll.objects.link(ob);return ob
def module(name,fn):
    reset();fn();o=finish(name);modules[name]=o;return o
def activate(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def text(owner,body,center,size,key='Paper',rotate=False):
    data=bpy.data.curves.new(owner.name+'_Text','FONT');data.body=body;data.font=font
    data.size=size;data.align_x='CENTER';data.align_y='CENTER';data.extrude=.00035;data.resolution_u=2
    source=bpy.data.objects.new(owner.name+'_EditableText_'+str(len(texts.objects)),data);texts.objects.link(source)
    source.location=center;source.rotation_euler=(math.pi/2,0,0)
    if rotate:source.rotation_euler=(math.pi/2,math.pi/2,0)
    data.materials.append(M[key]);source.hide_render=True;source.hide_set(True)
    obj=source.copy();obj.data=source.data.copy();lib.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
    activate(obj);bpy.ops.object.convert(target='MESH');obj=bpy.context.object
    obj.select_set(True);owner.select_set(True);bpy.context.view_layer.objects.active=owner;bpy.ops.object.join()
    sign_content.setdefault(owner.name,[]).append(body)
def signboard(name,w,h,paper,body,fontsize,textmat='Paper'):
    ob=module(name,lambda:(box(-w/2,0,0,w,.085,h,'Trim'),box(-w/2+.045,-.012,.045,w-.09,.018,h-.09,paper)))
    text(ob,body,(0,-.034,h*.51),fontsize,textmat);return ob

# Authored lettering, with clear context and generous margins.
signboard('SM_Sign_Ramen_Fascia',3.8,.68,'Paper','ラーメン',.48,'RamenRed')
vsign=module('SM_Sign_Ramen_Vertical',lambda:(box(-.30,0,0,.6,.10,1.90,'Trim'),box(-.26,-.015,.04,.52,.02,1.82,'RamenRed')))
for ch,z in zip('ラーメン',(1.62,1.20,.78,.36)):text(vsign,ch,(0,-.042,z),.36,'Paper',rotate=ch=='ー')
signboard('SM_Sign_Hana_Japanese',2.55,.62,'Paper','喫茶 花',.40,'Timber')
signboard('SM_Sign_Open',.64,.88,'Noren','営業中',.18,'Paper')
signboard('SM_Sign_SakuraStreet',1.35,.35,'Blue','さくら通り',.19,'White')

def stop_shape():
    # Japanese inverted triangular stop sign, front -Y; pole base is origin.
    beam((0,0,0),(0,0,2.75),.033,'Metal',12)
    p=[(-.39,-.04,2.72),(.39,-.04,2.72),(0,-.04,2.045)]
    poly(p,[(0,1,2)],'White');p2=[(-.345,-.045,2.695),(.345,-.045,2.695),(0,-.045,2.098)]
    poly(p2,[(0,1,2)],'RamenRed')
stop=module('SM_Road_StopSign',stop_shape);text(stop,'止まれ',(0,-.055,2.49),.16,'White')

def notice():
    for x in (-.71,.71):box(x-.045,-.02,0,.09,.12,2.1,'Timber')
    box(-.86,-.03,.65,1.72,.13,1.4,'Timber');box(-.79,-.045,.72,1.58,.02,1.26,'Sage')
    box(-.94,-.12,2.05,1.88,.37,.10,'Roof')
    # Three blank notices have ruled lines, intentionally no pseudo-writing.
    for x,z,w,h in [(-.64,.93,.37,.61),(-.15,1.01,.33,.50),(.31,.91,.33,.65)]:
        box(x,-.075,z,w,.012,h,'Paper')
        for zz in (z+h*.28,z+h*.48,z+h*.68):box(x+.05,-.09,zz,w-.10,.006,.012,'Siding')
notice_obj=module('SM_PublicNoticeboard',notice);text(notice_obj,'掲示板',(0,-.079,1.81),.18,'Paper')

# Compact exterior-only local ramen shop, six-meter frontage and 4.6 m depth.
def shell():
    box(-3,-2.3,0,6,4.6,.20,'Stone')
    box(-3,-2.25,.2,.18,4.5,5.4,'Plaster');box(2.82,-2.25,.2,.18,4.5,5.4,'Plaster')
    box(-3,2.1,.2,6,.2,5.4,'Plaster');box(-3,-2.3,2.9,6,.20,2.7,'Plaster')
    # Front lower wall split with a broad recessed shop window and real door bay.
    box(-3,-2.3,.20,.24,.18,2.7,'Timber');box(2.75,-2.3,.20,.25,.18,2.7,'Timber')
    box(.85,-2.3,.20,.17,.18,2.7,'Timber');box(-3,-2.3,.20,3.85,.18,.48,'Timber')
    box(-3,-2.3,2.58,6,.18,.32,'Timber')
    for x in (-2.96,2.88):box(x,-2.37,.20,.08,.13,5.43,'Timber')
    box(-3.05,-2.39,2.82,6.10,.30,.13,'Trim')
shell_ob=module('SM_Ramen_Shell',shell)
def glazing():
    box(-2.74,-2.28,.7,3.52,.08,1.87,'Glass')
    for x in (-2.74,-1.58,-.42,.71):box(x,-2.39,.65,.065,.16,1.98,'Timber')
    for z in (.65,1.20,2.55):box(-2.74,-2.39,z,3.52,.16,.055,'Timber')
    # Restrained broad reflection shapes.
    for x in (-2.53,-1.30,-.14):
        poly([(x,-2.395,1.25),(x+.09,-2.395,1.25),(x+.52,-2.395,2.45),(x+.43,-2.395,2.45)],[(0,1,2,3)],'Reflection')
    box(1.06,-2.28,.22,1.62,.08,2.36,'Glass')
    for x in (1.06,1.84,2.62):box(x,-2.4,.20,.055,.16,2.4,'Timber')
    for z in (.20,.78,2.55):box(1.06,-2.40,z,1.62,.16,.055,'Timber')
    for x in (1.72,1.92):beam((x,-2.48,1.0),(x,-2.48,1.33),.018,'Metal')
module('SM_Ramen_ShopGlazing',glazing)
def upper_window():
    box(-.69,.025,0,1.38,.10,1.40,'Trim');box(-.63,.008,.06,1.26,.025,1.28,'Glass')
    for x in (-.68,-.025,.63):box(x,-.035,.02,.05,.09,1.36,'Metal')
    for z in (.02,.72,1.34):box(-.68,-.035,z,1.36,.09,.045,'Metal')
    for x in (-.49,.17):poly([(x,-.03,.14),(x+.075,-.03,.14),(x+.36,-.03,1.27),(x+.285,-.03,1.27)],[(0,1,2,3)],'Reflection')
    box(-.75,-.12,-.06,1.5,.22,.07,'Stone')
module('SM_Window_ShopUpper_140',upper_window)
def noren():
    beam((-2.8,.0,.66),(2.8,.0,.66),.025,'Timber')
    for i in range(8):
        x=-2.77+i*.70
        poly([(x,-.015,.60),(x+.65,-.015,.60),(x+.66,-.06,0),(x+.02,-.045,.015)],[(0,1,2,3)],'Noren')
curtain=module('SM_Ramen_Noren',noren)
# Three large, correct kana on central curtain panels. No invented shop name.
text(curtain,'ラーメン',(0,-.079,.32),.31,'Paper')
def roof():
    # Shallow gable ridge along X, restrained roof courses.
    for side in (-1,1):
        pts=[(-3.35,0,6.35),(3.35,0,6.35),(3.35,side*2.67,5.57),(-3.35,side*2.67,5.57),(-3.35,0,6.23),(3.35,0,6.23),(3.35,side*2.67,5.45),(-3.35,side*2.67,5.45)]
        poly(pts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'Roof')
        beam((-3.39,side*2.67,5.50),(3.39,side*2.67,5.50),.075,'Trim',4)
        for yy in (.4,.85,1.30,1.75,2.2):beam((-3.35,side*yy,6.35-.78*yy/2.67+.01),(3.35,side*yy,6.35-.78*yy/2.67+.01),.018,'Roof',6)
    beam((-3.4,0,6.37),(3.4,0,6.37),.075,'Trim',8)
    for x in (-3.0,2.85):poly([(x,-2.3,5.55),(x,2.3,5.55),(x,0,6.22),(x+.15,-2.3,5.55),(x+.15,2.3,5.55),(x+.15,0,6.22)],[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],'Plaster')
module('SM_Ramen_Roof',roof)
def shop_canopy():
    poly([(-3.15,-2.3,3.05),(3.15,-2.3,3.05),(3.15,-3.05,2.87),(-3.15,-3.05,2.87)],[(0,3,2,1)],'Roof')
    box(-3.17,-3.10,2.76,6.34,.14,.16,'Trim')
    for x in (-2.85,2.85):beam((x,-2.4,2.35),(x,-3.02,2.83),.025,'Metal')
module('SM_Ramen_Canopy',shop_canopy)
def gutter():
    box(-1.5,-.06,0,3,.12,.06,'Metal');box(-1.5,-.085,0,3,.025,.13,'Metal')
module('SM_Gutter_3m',gutter)
def pipe():
    beam((0,.08,0),(0,.08,2.58),.035,'Metal',10);beam((0,.08,2.58),(0,-.16,2.82),.035,'Metal',10)
    beam((0,-.16,2.82),(0,-.16,3),.035,'Metal',10)
    for z in (.35,1.6,2.5):box(-.055,.06,z,.11,.09,.035,'Trim')
module('SM_Downpipe_3m',pipe)
def shutter():
    box(-.38,0,0,.76,.08,1.4,'Trim')
    for i in range(12):box(-.34,-.025,.06+i*.107,.68,.03,.055,'Metal')
module('SM_Shutter_76x140',shutter)
def balcony():
    box(-1.6,-.85,0,3.2,.85,.16,'Stone');box(-1.63,-.9,.15,3.26,.07,.72,'Siding')
    for x in (-1.60,1.56):box(x,-.85,.15,.045,.85,.72,'Siding')
    for x in [-1.5+i*.25 for i in range(13)]:beam((x,-.87,.7),(x,-.87,1.06),.012,'Metal',6)
    beam((-1.63,-.87,1.06),(1.63,-.87,1.06),.027,'Metal')
    for x in (-1.6,1.6):beam((x,-.85,1.06),(x,0,1.06),.027,'Metal')
module('SM_Balcony_Compact_320',balcony)
def lantern():
    # Ribbed paper lantern; a single local accent, no fake glyphs.
    n=16;profiles=[(0,.13),(.05,.19),(.15,.23),(.37,.23),(.47,.19),(.52,.13)]
    pts=[(r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for z,r in profiles for i in range(n)]
    faces=[]
    for j in range(len(profiles)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    poly(pts,faces,'RamenRed')
    for z,r in profiles:beam((0,0,z-.01),(0,0,z+.01),r,'Noren',16)
    for z in (0,.5):beam((0,0,z),(0,0,z+.035),.13,'Trim',16)
    beam((0,0,.53),(0,0,.73),.012,'Metal')
module('SM_Ramen_Lantern',lantern)

def vending():
    box(-.5,-.38,.055,1,.76,1.80,'VendingRed');box(-.45,-.405,.13,.90,.035,1.65,'Trim')
    box(-.40,-.429,.56,.65,.026,1.14,'Paper');box(-.36,-.452,.66,.57,.018,.94,'Glass')
    for z in (.90,1.20,1.50):
        box(-.37,-.485,z-.16,.59,.09,.035,'White')
        for i in range(5):
            x=-.31+i*.11;key=['Paper','Sage','RamenRed','Blue','Yellow'][i]
            beam((x,-.48,z-.12),(x,-.48,z+.04),.031,key,8)
            beam((x,-.48,z+.04),(x,-.48,z+.055),.025,'White',8)
            box(x-.025,-.51,z-.17,.05,.018,.025,'Lamp')
    box(.29,-.435,.62,.11,.02,.72,'Paper');disk(.345,-.47,1.20,.037,.03,'Metal',16)
    box(.31,-.48,.98,.075,.02,.025,'Trim');box(.31,-.48,.79,.075,.02,.07,'Trim')
    box(-.37,-.445,.25,.61,.035,.18,'Tire');box(-.32,-.46,.25,.51,.06,.035,'Metal')
    for x in (-.40,.3):box(x,-.25,0,.10,.5,.055,'Tire')
vend=module('SM_VendingMachine',vending)
# The deliberately text-free drink silhouettes avoid false brands or nonsensical labels.
def bicycle():
    # Utility city bicycle: two wheels along X, front facing -Y for kit consistency.
    for x in (-.56,.56):
        ring(x,-.027,.345,.345,.295,.055,'Tire',32)
        ring(x,-.034,.345,.295,.283,.068,'Metal',32)
        disk(x,-.06,.345,.045,.12,'Metal',12)
        for i in range(12):
            a=i*math.tau/12;beam((x,0,.345),(x+.283*math.cos(a),0,.345+.283*math.sin(a)),.0045,'Metal',4)
    points={'rear':(-.56,0,.345),'bottom':(-.03,0,.29),'seat':(-.19,0,.79),'head':(.39,0,.83),'front':(.56,0,.345)}
    for a,b in [('rear','bottom'),('rear','seat'),('seat','bottom'),('bottom','head'),('head','seat'),('head','front')]:beam(points[a],points[b],.021,'Bicycle')
    beam((-.19,0,.79),(-.22,0,.95),.017,'Metal');box(-.39,-.095,.93,.30,.19,.05,'Timber')
    beam((.39,0,.83),(.33,0,1.10),.017,'Metal');beam((.33,-.25,1.10),(.33,.25,1.10),.018,'Metal')
    for y in (-.27,.17):beam((.33,y,1.10),(.33,y+.10,1.10),.022,'Tire')
    disk(-.03,-.055,.29,.10,.035,'Metal',20)
    beam((-.03,-.075,.29),(.075,-.075,.19),.012,'Metal');box(.045,-.17,.17,.09,.12,.035,'Tire')
    # Simple open-front basket: thin bars, no closed box silhouette.
    for y in (-.17,.17):
        beam((.43,y,.77),(.73,y,.77),.010,'Metal');beam((.41,y,1.03),(.76,y,1.03),.010,'Metal')
    for x in (.43,.73):
        beam((x,-.17,.77),(x,.17,.77),.010,'Metal');beam((x,-.17,1.03),(x,.17,1.03),.010,'Metal')
    for x in (.43,.53,.63,.73):
        for y in (-.17,.17):beam((x,y,.77),(x,y,1.03),.006,'Metal',4)
    for y in (-.085,0,.085):beam((.73,y,.77),(.73,y,1.03),.006,'Metal',4)
    beam((-.13,0,.32),(-.23,-.23,0),.012,'Metal');box(-.75,-.12,.71,.40,.24,.03,'Metal')
module('SM_CityBicycle',bicycle)

def mirror():
    beam((0,0,0),(0,0,2.7),.032,'RamenRed',12)
    beam((0,0,2.65),(.22,-.02,2.85),.025,'Metal')
    disk(.22,-.055,2.85,.32,.08,'RamenRed',32);disk(.22,-.072,2.85,.285,.025,'Reflection',32)
    # Authored broad reflection, intentionally no expensive dynamic scene capture.
    poly([(-.035,-.100,2.75),(.42,-.100,2.75),(.44,-.100,2.92),(.06,-.100,2.98)],[(0,1,2,3)],'Glass')
module('SM_RoadsideMirror',mirror)
def mailbox():
    box(-.035,-.035,0,.07,.07,1.0,'Metal');box(-.24,-.15,.90,.48,.30,.31,'Sage')
    box(-.27,-.18,1.20,.54,.36,.055,'Trim');box(-.18,-.162,1.09,.36,.014,.025,'Tire')
    box(-.11,-.164,.96,.22,.015,.075,'Paper')
module('SM_ResidentialMailbox',mailbox)
def ac():
    box(-.42,-.17,.07,.84,.34,.56,'Paper')
    for x in (-.34,.24):box(x,-.19,0,.10,.38,.07,'Metal')
    disk(-.11,-.197,.35,.22,.025,'Metal',24);disk(-.11,-.215,.35,.18,.018,'Siding',24)
    for i in range(7):
        x=-.29+i*.06;beam((x,-.24,.18),(x,-.24,.52),.006,'Paper',4)
    for z in (.20,.27,.34,.41,.48):beam((-.29,-.24,z),(.07,-.24,z),.006,'Paper',4)
    for z in (.17,.24,.31,.38,.45,.52):box(.18,-.185,z,.18,.02,.018,'Siding')
module('SM_AC_Outdoor',ac)

# A small public shrine entrance is optional at integration; contemporary low-key scale.
def torii():
    for x in (-1.15,1.15):
        beam((x,0,0),(x*.94,0,2.92),.105,'RamenRed',12)
        beam((x,0,0),(x,0,.40),.115,'Trim',12)
    box(-1.47,-.11,2.30,2.94,.22,.17,'RamenRed')
    box(-1.75,-.15,2.89,3.5,.30,.17,'RamenRed');box(-1.80,-.18,3.06,3.6,.36,.12,'Trim')
    box(-.08,-.10,2.47,.16,.20,.42,'RamenRed')
module('SM_SmallTorii',torii)

placed=[]
def inst(key,label,pos,angle=0):
    p=modules[key];o=bpy.data.objects.new('RAMEN_'+label,p.data);assembled.objects.link(o)
    o.location=pos;o.rotation_euler.z=math.radians(angle);placed.append(o);return o
for key in ('Shell','ShopGlazing','Roof','Canopy'):inst('SM_Ramen_'+key,key,(0,0,0))
for i,x in enumerate((-1.9,0,1.9)):inst('SM_Window_ShopUpper_140','UpperWindow'+str(i),(x,-2.34,3.68))
inst('SM_Sign_Ramen_Fascia','Fascia',(-.60,-2.45,3.03))
inst('SM_Sign_Ramen_Vertical','BladeSign',(2.62,-2.66,3.15))
inst('SM_Ramen_Noren','Noren',(0,-2.55,2.00))
inst('SM_Sign_Open','Open',(2.29,-2.56,.84))
for i,x in enumerate((-2.45,.50)):inst('SM_Ramen_Lantern','Lantern'+str(i),(x,-2.78,2.10))
for i,x in enumerate((-1.65,1.65)):inst('SM_Gutter_3m','Gutter'+str(i),(x,-2.67,5.50))
for i,z in enumerate((0,2.7)):inst('SM_Downpipe_3m','Downpipe'+str(i),(-2.84,-2.46,z))
inst('SM_AC_Outdoor','AC',(3.17,1.05,.1),90)

def prepare(o):
    activate(o)
    if any(abs(v)>1e-7 for v in o.rotation_euler) or any(abs(v-1)>1e-7 for v in o.scale):
        if o.data.users>1:o.data=o.data.copy()
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.006,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    o.data.uv_layers.active.name='UV0_Surface'
    uv=o.data.uv_layers.new(name='UV1_Lightmap')
    for a,b in zip(o.data.uv_layers[0].data,uv.data):b.uv=a.uv
    o['units']='meters';o['front']='-Y';o['up']='Z';o['authored_text']=' | '.join(sign_content.get(o.name,[]))
    o.data.calc_loop_triangles()
def record(o):
    bpy.context.view_layer.update();pts=[o.matrix_world@v.co for v in o.data.vertices]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    o.data.calc_loop_triangles()
    return {'fbx':'Exports/'+o.name+'.fbx','triangles':len(o.data.loop_triangles),'bounds_m':{'min':lo,'max':hi,'dimensions':[hi[i]-lo[i] for i in range(3)]},'material_slots':[m.name for m in o.data.materials],'uv_channels':len(o.data.uv_layers),'text':sign_content.get(o.name,[])}
def export(o):
    activate(o)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Exports'/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',global_scale=1,axis_forward='-Y',axis_up='Z',
        use_triangles=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE',use_custom_props=True)
report={'blender':bpy.app.version_string,'meters_per_unit':1,'front_axis_blender':'-Y','front_axis_unreal_after_force_front_x':'X','up_axis':'Z',
 'materials':{'M_Town_'+k:v for k,v in PALETTE.items()},'font':str(FONT),'font_embedded':False,'glyph_coverage':coverage,
 'sign_strings':STRINGS,'collision':'Add simple deliberate proxies in Unreal. Decorative signs and equipment should use NoCollision.',
 'recommended_collision_cm':{'SM_RamenShop_Assembled':[{'center':[0,0,280],'size':[460,600,560]}],'SM_VendingMachine':[{'center':[0,0,93],'size':[76,100,186]}]},'modules':{}}
for n,o in modules.items():
    prepare(o);report['modules'][n]=record(o);export(o);o.hide_set(True);o.hide_render=True
# Join only copies. Original parts and editable Japanese text survive in .blend.
temp=[];grid=math.ceil(math.sqrt(len(placed)))
for i,o in enumerate(placed):
    c=o.copy();c.data=o.data.copy();lib.objects.link(c);temp.append(c)
    for loop in c.data.uv_layers[1].data:
        u,v=loop.uv;loop.uv=((i%grid+.025+.95*u)/grid,(i//grid+.025+.95*v)/grid)
bpy.ops.object.select_all(action='DESELECT')
for o in temp:o.select_set(True)
bpy.context.view_layer.objects.active=temp[0];bpy.ops.object.join();joined=bpy.context.object
sc.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
joined.name='SM_RamenShop_Assembled';report['modules'][joined.name]=record(joined)
report['modules'][joined.name]['text']=['ラーメン','営業中'];export(joined)
bpy.data.objects.remove(joined,do_unlink=True)
(ROOT/'build_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def stage_obj(o):
    for c in list(o.users_collection):c.objects.unlink(o)
    stage.objects.link(o)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.06));ground=bpy.context.object
ground.name='PREVIEW_Ground';stage_obj(ground);ground.data.materials.append(M['Stone'])
world=bpy.data.worlds.new('PREVIEW_Sky');world.use_nodes=True;sc.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.77,1,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65
ld=bpy.data.lights.new('PREVIEW_Sun','SUN');ld.energy=2.0;ld.angle=math.radians(3)
sun=bpy.data.objects.new('PREVIEW_Sun',ld);stage.objects.link(sun);sun.rotation_euler=(math.radians(28),math.radians(-23),math.radians(-28))
camd=bpy.data.cameras.new('PREVIEW_Camera');cam=bpy.data.objects.new('PREVIEW_Camera',camd);stage.objects.link(cam);sc.camera=cam;camd.type='ORTHO'
def camera(pos,target,scale):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camd.ortho_scale=scale
def render(name,w=1600,h=1200):
    sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.filepath=str(ROOT/'Previews'/name)
    if '--no-render' not in sys.argv:bpy.ops.render.render(write_still=True)
camera((10,-16,9),(0,-.3,3.1),11.5)
sc['scope']='Original Japanese neighborhood kit; editable modules and exact authored Japanese glyph outlines.'
# Do not pack external OS fonts. Linked path is intentionally retained for editing.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'JapaneseTown01.blend'))
print('TOWN_ASSETS_EXPORTED '+str(ROOT),flush=True)
render('RamenShop_ThreeQuarter.png')
camera((0,-20,3.7),(0,-2.5,3.1),8);render('RamenShop_Front.png',1600,1400)
for o in placed:o.hide_render=True
preview=[]
def show(n,pos):
    o=bpy.data.objects.new('PREVIEW_'+n,modules[n].data);stage.objects.link(o);o.location=pos;preview.append(o)
for n,pos in [('SM_VendingMachine',(-3,0,0)),('SM_CityBicycle',(-1.3,-.1,0)),('SM_PublicNoticeboard',(1.1,.4,0)),('SM_RoadsideMirror',(3,1.0,0)),('SM_ResidentialMailbox',(3,-.9,0)),('SM_AC_Outdoor',(-.1,-.7,0))]:show(n,pos)
camera((8,-17,9),(0,.0,1.2),8.7);render('TownProps_Lineup.png',1600,1050)
for o in preview:o.hide_render=True
for n,pos in [('SM_Sign_Hana_Japanese',(-1.8,0,1.6)),('SM_Sign_SakuraStreet',(-1.8,0,.65)),('SM_Sign_Ramen_Fascia',(1.5,0,1.6)),('SM_Sign_Ramen_Vertical',(1.25,0,-.8)),('SM_Sign_Open',(2.55,0,-.1))]:show(n,pos)
camera((0,-14,2),(0,0,.90),7.5);render('Japanese_Signage.png',1800,1000)
print('TOWN_KIT_BUILD_COMPLETE',flush=True)
