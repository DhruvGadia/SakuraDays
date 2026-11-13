"""Inspect source UVs and round-trip exported FBX in a separate Blender process."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from io_scene_fbx import parse_fbx
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SakuraHouse01.blend'))
errors=[];details={}
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def area(poly):return abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2) if len(poly)>=3 else 0
def intersection(a,b):
    poly=list(a)
    if cross(*b)<0:b=list(reversed(b))
    for i in range(3):
        p,q=b[i],b[(i+1)%3];new=[]
        if not poly:return 0
        for j,s in enumerate(poly):
            t=poly[(j+1)%len(poly)];cs=cross(p,q,s);ct=cross(p,q,t)
            if cs>=-1e-12:new.append(s)
            if (cs>0 and ct<0) or (cs<0 and ct>0):
                f=cs/(cs-ct);new.append((s[0]+f*(t[0]-s[0]),s[1]+f*(t[1]-s[1])))
        poly=new
    return area(poly)
for obj in bpy.data.collections['01_MODULE_LIBRARY'].objects:
    mesh=obj.data;mesh.calc_loop_triangles();tris=[];zero=0;overlap=0
    for tri in mesh.loop_triangles:
        pts=[tuple(mesh.uv_layers[0].data[i].uv) for i in tri.loops]
        if area(pts)<1e-11:zero+=1
        tris.append((pts,(min(p[0] for p in pts),max(p[0] for p in pts),min(p[1] for p in pts),max(p[1] for p in pts))))
    order=sorted(tris,key=lambda v:v[1][0])
    for i,(a,ba) in enumerate(order):
        for b,bb in order[i+1:]:
            if bb[0]>=ba[1]-1e-10:break
            if bb[3]<=ba[2] or bb[2]>=ba[3]:continue
            if intersection(a,b)>1e-9:overlap+=1
    valid_slots=all(p.material_index<len(mesh.materials) for p in mesh.polygons)
    details[obj.name]={'uv_degenerate_triangles':zero,'uv_overlapping_triangle_pairs':overlap,'material_indices_valid':valid_slots,'uv_channels':len(mesh.uv_layers)}
    if zero or overlap or not valid_slots:errors.append(obj.name+' failed UV/material validation')
source={o.name:{'matrix':[list(row) for row in o.matrix_world],'bounds':[list(o.matrix_world@Vector(p)) for p in o.bound_box]} for o in bpy.data.collections['02_HOUSE01_ASSEMBLY'].objects}
root,ver=parse_fbx.parse(str(ROOT/'Exports/SM_SakuraHouse01_Assembled.fbx'))
gs=next(e for e in root.elems if e.id==b'GlobalSettings')
props=next(e for e in gs.elems if e.id==b'Properties70')
metadata={e.props[0].decode():e.props[-1] for e in props.elems if e.id==b'P' and e.props[0] in [b'UnitScaleFactor',b'OriginalUnitScaleFactor',b'UpAxis',b'UpAxisSign',b'FrontAxis',b'FrontAxisSign',b'CoordAxis',b'CoordAxisSign']}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
bpy.ops.import_scene.fbx(filepath=str(ROOT/'Exports/SM_SakuraHouse01_Assembled.fbx'),use_anim=False)
bpy.context.view_layer.update()
max_error=0.;count=0;atlas=[]
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    count+=1
    if len(obj.data.uv_layers)!=2:errors.append(obj.name+' missing exported UV channel')
    else:
        uv=[tuple(d.uv) for d in obj.data.uv_layers[1].data]
        atlas.append((obj.name,[min(p[0] for p in uv),max(p[0] for p in uv),min(p[1] for p in uv),max(p[1] for p in uv)]))
    if obj.name not in source:errors.append('Unexpected imported mesh '+obj.name);continue
    expected=source[obj.name]['bounds'];actual=[list(obj.matrix_world@Vector(p)) for p in obj.bound_box]
    # Compare sorted world-space extrema; triangulation may reorder bound-box corners.
    for axis in range(3):
        for fn in [min,max]:max_error=max(max_error,abs(fn(p[axis] for p in actual)-fn(p[axis] for p in expected)))
if count!=len(source):errors.append('FBX object count differs')
atlas_overlaps=0
for i,(name,a) in enumerate(atlas):
    if any(v<-.00001 or v>1.00001 for v in a):errors.append(name+' atlas outside unit square')
    for _,b in atlas[i+1:]:
        if min(a[1],b[1])-max(a[0],b[0])>1e-8 and min(a[3],b[3])-max(a[2],b[2])>1e-8:atlas_overlaps+=1
if atlas_overlaps:errors.append('Assembled UV1 atlas objects overlap')
if max_error>.0001:errors.append('Roundtrip scale/orientation/bounds mismatch')
if metadata['UpAxis']!=2 or metadata['UpAxisSign']!=1:errors.append('FBX is not Z up')
if abs(metadata['UnitScaleFactor']-100)>.001:errors.append('FBX unit scale is not centimeters per meter')
result={'source_module_checks':details,'fbx_version':ver,'fbx_global_settings':metadata,
        'roundtrip_objects':count,'assembled_uv1_overlapping_object_bounds':atlas_overlaps,'max_world_bounds_error_m':max_error,'errors':errors,'passed':not errors}
(ROOT/'validation_blender.json').write_text(json.dumps(result,indent=2))
print('HOUSE_VALIDATION '+json.dumps({k:v for k,v in result.items() if k!='source_module_checks'}))
if errors:raise RuntimeError(errors)
