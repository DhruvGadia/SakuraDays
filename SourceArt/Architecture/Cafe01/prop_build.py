"""One SakuraDays cafe prop set; imported by build_cafe.py.

All geometry is original and deterministic. No scene reset, export, UV or save
operations occur here. The caller supplies materials and owns finalization.
"""
import math
import random
import bpy
from mathutils import Vector


class PropMesh:
    def __init__(self, materials):
        self.materials = materials
        self.verts, self.faces, self.tags, self.smooth = [], [], [], []

    def piece(self, points, faces, material, smooth=False):
        offset = len(self.verts)
        self.verts.extend(tuple(point) for point in points)
        for face in faces:
            self.faces.append(tuple(offset + index for index in face))
            self.tags.append(material)
            self.smooth.append(smooth)

    def box(self, center, size, material):
        x, y, z = center
        w, d, h = (v / 2 for v in size)
        points = [(x-w,y-d,z-h),(x+w,y-d,z-h),(x+w,y+d,z-h),(x-w,y+d,z-h),
                  (x-w,y-d,z+h),(x+w,y-d,z+h),(x+w,y+d,z+h),(x-w,y+d,z+h)]
        self.piece(points, [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)], material)

    def beam(self, start, end, width, material, depth=None):
        a, b = Vector(start), Vector(end)
        axis = (b-a).normalized()
        u = axis.cross(Vector((0,1,0)))
        if u.length < .001:
            u = axis.cross(Vector((1,0,0)))
        u.normalize()
        v = axis.cross(u).normalized()
        u *= width / 2
        v *= (depth if depth is not None else width) / 2
        points = [p + u*s + v*t for p in (a,b) for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        self.piece(points, [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)], material)

    def tube(self, start, end, r0, material, r1=None, sides=12):
        a, b = Vector(start), Vector(end)
        axis = (b-a).normalized()
        u = axis.cross(Vector((0,1,0)))
        if u.length < .001:
            u = axis.cross(Vector((1,0,0)))
        u.normalize()
        v = axis.cross(u).normalized()
        if r1 is None:
            r1 = r0
        points = [p + r*(math.cos(j*math.tau/sides)*u + math.sin(j*math.tau/sides)*v)
                  for p,r in ((a,r0),(b,r1)) for j in range(sides)]
        faces = [tuple(reversed(range(sides))), tuple(range(sides,sides*2))]
        faces += [(j,(j+1)%sides,(j+1)%sides+sides,j+sides) for j in range(sides)]
        self.piece(points, faces, material, True)

    def lathe(self, center_xy, profile, material, sides=16):
        """Closed lathed solid. Profile begins/ends with nonzero-radius rings."""
        x,y = center_xy
        points = [(x+r*math.cos(j*math.tau/sides),y+r*math.sin(j*math.tau/sides),z)
                  for r,z in profile for j in range(sides)]
        faces = [tuple(reversed(range(sides)))]
        for ring in range(len(profile)-1):
            for j in range(sides):
                k = (j+1)%sides
                faces.append((ring*sides+j,ring*sides+k,(ring+1)*sides+k,(ring+1)*sides+j))
        faces.append(tuple((len(profile)-1)*sides+j for j in range(sides)))
        self.piece(points,faces,material,True)

    def shrub_mass(self, center, size, material, phase=0):
        """Low-resolution leaf mass with deliberate broad planar anime values."""
        center = Vector(center)
        rx,ry,rz = size
        sides = 7
        points = [center+Vector((0,0,-rz))]
        for zfac, radial in [(-.55,.80),(.15,1.),(.73,.65)]:
            for j in range(sides):
                a = j*math.tau/sides+phase
                points.append(center+Vector((rx*radial*math.cos(a),ry*radial*math.sin(a),rz*zfac)))
        points.append(center+Vector((0,0,rz)))
        faces = [(0,1+(j+1)%sides,1+j) for j in range(sides)]
        for ring in range(2):
            for j in range(sides):
                faces.append((1+ring*sides+j,1+ring*sides+(j+1)%sides,
                              1+(ring+1)*sides+(j+1)%sides,1+(ring+1)*sides+j))
        faces += [(1+2*sides+j,1+2*sides+(j+1)%sides,len(points)-1) for j in range(sides)]
        self.piece(points,faces,material)

    def leaf(self, start, end, width, material):
        a,b = Vector(start),Vector(end)
        axis = (b-a).normalized()
        cross = axis.cross(Vector((0,0,1)))
        if cross.length < .01:cross = axis.cross(Vector((0,1,0)))
        cross.normalize()
        c = a.lerp(b,.52)
        ridge = c+Vector((0,0,.018))
        # Closed six-face leaf, with a raised midrib and shallow lower face.
        points = [a,c+cross*width*.5,b,c-cross*width*.5,ridge,c-Vector((0,0,.008))]
        self.piece(points,[(0,1,4),(1,2,4),(2,3,4),(3,0,4),
                           (1,0,5),(2,1,5),(3,2,5),(0,3,5)], material)

    def finish(self, name, collection):
        mesh = bpy.data.meshes.new(name+'_Mesh')
        # Ground the actual lowest vertex while keeping identity object transforms.
        floor = min(point[2] for point in self.verts)
        mesh.from_pydata([(x,y,z-floor) for x,y,z in self.verts],[],self.faces)
        mesh.update()
        used = list(dict.fromkeys(self.tags))
        for key in used:
            mesh.materials.append(self.materials[key])
        for face,tag,smooth in zip(mesh.polygons,self.tags,self.smooth):
            face.material_index = used.index(tag)
            face.use_smooth = smooth
        obj = bpy.data.objects.new(name,mesh)
        collection.objects.link(obj)
        obj['pivot'] = 'Ground-centered; +Z up; -Y front; 1 unit = 1 meter'
        obj['source'] = 'Original SakuraDays procedural cafe prop; one design per category'
        return obj


def create_props(materials, collection):
    props = {}

    # Wood slats, dark iron frame, human-scaled seat; back faces +Y.
    b=PropMesh(materials)
    for y in [-.165,-.055,.055,.165]:
        b.box((0,y,.455),(.46,.098,.036),'wood')
    for x in [-.20,.20]:
        b.beam((x*1.13,-.22,.018),(x,-.18,.44),.026,'metal')
        b.beam((x*1.13,.23,.018),(x,.17,.47),.026,'metal')
        b.beam((x,.17,.45),(x,.245,.86),.026,'metal')
        b.beam((x,-.18,.42),(x,.17,.42),.027,'metal')
        b.beam((x*1.07,-.21,.19),(x*1.07,.20,.19),.018,'metal')
    b.beam((-.20,.205,.64),(.20,.205,.64),.018,'metal')
    for z in [.66,.77,.855]:
        y=.17+(z-.45)*.18
        b.box((0,y,z),(.48,.036,.065),'wood')
    b.beam((-.20,-.16,.425),(.20,-.16,.425),.025,'metal')
    props['SM_Cafe_Chair']=b.finish('SM_Cafe_Chair',collection)

    # One bistro table design, 70 cm round top and a solid pedestal.
    b=PropMesh(materials)
    b.lathe((0,0),[(.325,.697),(.35,.705),(.35,.735),(.335,.744)],'wood',24)
    b.tube((0,0,.10),(0,0,.705),.032,'metal',.026,12)
    b.tube((0,0,.66),(0,0,.69),.16,'metal',.16,16)
    for a in [0,math.tau/3,math.tau*2/3]:
        end=(math.cos(a)*.275,math.sin(a)*.275,.02)
        b.tube((0,0,.16),end,.018,'metal',.014,10)
        b.tube((end[0],end[1],0),(end[0],end[1],.025),.027,'metal',sides=10)
    # Restrained board joints are flush graphic lines, not grain noise.
    for x in [-.12,.12]:
        length=2*math.sqrt(.33**2-x**2)
        b.box((x,0,.7445),(.004,length,.001),'trim')
    props['SM_Cafe_Table']=b.finish('SM_Cafe_Table',collection)

    # 1.6 m slatted bench with rounded iron arms.
    b=PropMesh(materials)
    for y in [-.18,-.06,.06,.18]:
        b.box((0,y,.43),(1.60,.103,.045),'wood')
    for x in [-.64,.64]:
        for y in [-.16,.17]:
            b.beam((x,y*1.14,0),(x,y,.43),.045,'metal')
        b.beam((x,-.20,.385),(x,.22,.385),.048,'metal')
        b.beam((x,.18,.39),(x,.30,.92),.045,'metal')
        arm=[(x,-.15,.45),(x,-.15,.64),(x,-.10,.69),(x,.18,.69),(x,.25,.73)]
        for p,q in zip(arm[:-1],arm[1:]):b.tube(p,q,.022,'metal',sides=10)
    for z in [.60,.735,.87]:
        y=.18+(z-.39)*.23
        b.box((0,y,z),(1.60,.045,.108),'wood')
    props['SM_Cafe_Bench']=b.finish('SM_Cafe_Bench',collection)

    # Compact neighborhood lantern; one side-mounted hanging form is avoided so
    # the ground-centered asset can rotate freely without a misleading pivot.
    b=PropMesh(materials)
    b.lathe((0,0),[(.16,0),(.16,.06),(.12,.09),(.10,.30),(.065,.36)],'metal',12)
    b.tube((0,0,.30),(0,0,2.53),.052,'metal',.036,12)
    for z in [.42,2.38]:b.tube((0,0,z),(0,0,z+.055),.069,'metal',sides=12)
    b.lathe((0,0),[(.09,2.48),(.20,2.57),(.22,2.59)],'metal',6)
    # Lantern glazing is a matte warm panel, suitable for a restrained future emissive.
    b.lathe((0,0),[(.165,2.60),(.215,2.97)],'lamp',6)
    for j in range(6):
        a=j*math.tau/6
        b.tube((math.cos(a)*.17,math.sin(a)*.17,2.59),
               (math.cos(a)*.22,math.sin(a)*.22,2.98),.012,'metal',sides=6)
    b.lathe((0,0),[(.235,2.97),(.265,3.00),(.10,3.14),(.035,3.17)],'metal',6)
    b.tube((0,0,3.16),(0,0,3.20),.025,'metal',.01,8)
    props['SM_Cafe_StreetLamp']=b.finish('SM_Cafe_StreetLamp',collection)

    # One terracotta pot and original composed broad-leaf shrub.
    b=PropMesh(materials)
    b.lathe((0,0),[(.13,0),(.145,.025),(.195,.30),(.215,.31),(.215,.365),(.185,.365)],'terracotta',16)
    b.tube((0,0,.349),(0,0,.355),.181,'soil',sides=16)
    rng=random.Random(430)
    for j in range(7):
        a=j*2.39996
        top=Vector((math.cos(a)*.13,math.sin(a)*.13,.64+rng.random()*.16))
        b.tube((0,0,.35),top,.012,'wood',.006,7)
        b.shrub_mass(top,(.11,.12,.17),'leaf' if j%3 else 'leaf_light',a)
        for k in range(3):
            point=Vector((0,0,.35)).lerp(top,.45+k*.19)
            la=a+k*.9
            end=point+Vector((math.cos(la)*.22,math.sin(la)*.22,.05))
            b.leaf(point,end,.115,'leaf_light' if k==2 else 'leaf')
    props['SM_Cafe_PottedPlant']=b.finish('SM_Cafe_PottedPlant',collection)

    # A single reusable low planter. Three leaf fans are its planting arrangement,
    # not separate pot variations.
    b=PropMesh(materials)
    b.box((0,0,.055),(1.16,.34,.11),'wood')
    b.box((0,0,.19),(1.10,.32,.25),'soil')
    for y in [-.19,.19]:
        for z in [.12,.235,.35]:b.box((0,y,z),(1.20,.045,.10),'wood')
    for x in [-.585,.585]:b.box((x,0,.235),(.045,.38,.34),'wood')
    for x in [-.47,.47]:
        for y in [-.212,.212]:b.box((x,y,.24),(.035,.018,.35),'metal')
    for index,x in enumerate([-.38,0,.38]):
        center=Vector((x,0,.59))
        b.tube((x,0,.33),center,.015,'wood',.008,8)
        b.shrub_mass(center,(.18,.15,.23),'leaf',index*.4)
        for j in range(7):
            a=j*math.tau/7+index
            start=Vector((x,0,.41+(j%3)*.055))
            end=start+Vector((math.cos(a)*.25,math.sin(a)*.19,.15))
            b.leaf(start,end,.13,'leaf_light' if j%3==0 else 'leaf')
    props['SM_Cafe_Planter']=b.finish('SM_Cafe_Planter',collection)

    # Exterior AC condenser, front -Y, practical quiet neighborhood detail.
    b=PropMesh(materials)
    b.box((0,0,.36),(.82,.32,.57),'plaster')
    for x in [-.28,.28]:b.box((x,0,.04),(.065,.39,.08),'metal')
    b.box((-.12,-.166,.36),(.46,.014,.46),'trim')
    b.tube((-.12,-.18,.36),(-.12,-.195,.36),.212,'metal',sides=24)
    b.tube((-.12,-.198,.36),(-.12,-.204,.36),.034,'stone',sides=12)
    for j in range(9):
        z=.18+j*.045
        half=math.sqrt(max(.001,.205**2-(z-.36)**2))
        b.box((-.12,-.213,z),(half*2,.009,.012),'stone')
    for x in [.22,.27,.32]:b.box((x,-.168,.36),(.012,.012,.39),'trim')
    b.box((.22,-.18,.57),(.12,.01,.035),'paper')
    props['SM_Cafe_AC']=b.finish('SM_Cafe_AC',collection)
    return props
