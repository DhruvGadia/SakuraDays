"""Reuse the approved House01 modules for two contemporary Japanese rooflines."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
(ROOT/'Exports').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'House01/SakuraHouse01.blend'))
sc=bpy.context.scene
source=bpy.data.collections['02_HOUSE01_ASSEMBLY']
for o in list(bpy.data.objects):o.hide_set(True);o.hide_render=True
mats=[bpy.data.materials[n] for n in ['M_Plaster_Cream','M_Siding_BlueGray','M_Trim_Plum','M_Roof_Slate','M_Timber_Warm','M_Glass_Blue','M_Glass_Reflection','M_Concrete']]
report={'source':'../House01/SakuraHouse01.blend','meters_per_unit':1,'front':'-Y','up':'Z','variants':{}}
def cube(name,p,size,slot,coll):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    coll.objects.link(o)
    for m in mats:o.data.materials.append(m)
    for f in o.data.polygons:f.material_index=slot
    return o
for kind in ['UrbanFlat','HipRoof']:
    coll=bpy.data.collections.new(kind);sc.collection.children.link(coll);parts=[]
    for o in source.objects:
        if any(k in o.name for k in ['Roof_','Ridge_','Gable_','Barge_','Gutter_']):continue
        c=o.copy();c.data=o.data.copy();coll.objects.link(c);c.hide_set(False);c.hide_render=False;parts.append(c)
        if kind=='UrbanFlat' and ('_L2_' in o.name or ('Corner' in o.name and o.name.endswith('_L2')) or 'Balcony' in o.name):
            c2=c.copy();c2.data=c.data.copy();coll.objects.link(c2);c2.location.z+=2.8;parts.append(c2)
    top=8.7 if kind=='UrbanFlat' else 5.9
    parts.append(cube(kind+'_Eave',(0,0,top),(8.8,6.8,.18),2,coll))
    if kind=='UrbanFlat':
        parts.append(cube('RoofDeck',(0,0,top+.08),(8.4,6.4,.12),3,coll))
        for y in [-3.2,3.2]:parts.append(cube('Parapet',(0,y,top+.28),(8.5,.16,.45),0,coll))
        for x in [-4.2,4.2]:parts.append(cube('Parapet',(x,0,top+.28),(.16,6.4,.45),0,coll))
    else:
        v=[(-4.5,-3.5,top),(4.5,-3.5,top),(4.5,3.5,top),(-4.5,3.5,top),(-2.2,0,top+1.28),(2.2,0,top+1.28)]
        mesh=bpy.data.meshes.new('HipRoof');mesh.from_pydata(v,[],[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4),(3,2,1,0)]);mesh.update()
        for m in mats:mesh.materials.append(m)
        for p in mesh.polygons:p.material_index=3
        roof=bpy.data.objects.new('HipRoof',mesh);coll.objects.link(roof);parts.append(roof)
        parts.append(cube('HipRidge',(0,0,top+1.3),(4.6,.18,.17),2,coll))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object
    o.name='SM_House_'+kind
    sc.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    # Joining source modules and primitive roofs can introduce a third UVMap.
    # Rebuild two deliberate channels on this new derived mesh only.
    for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
    o.data.uv_layers.new(name='UV0_Surface')
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
    if len(o.data.uv_layers)<2:o.data.uv_layers.new(name='UV1_Lightmap')
    for a,b in zip(o.data.uv_layers[0].data,o.data.uv_layers[1].data):b.uv=a.uv
    o.data.calc_loop_triangles();pts=[o.matrix_world@v.co for v in o.data.vertices]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    file='Exports/'+o.name+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(ROOT/file),use_selection=True,object_types={'MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',use_triangles=True,mesh_smooth_type='FACE',bake_anim=False)
    report['variants'][kind]={'fbx':file,'bounds_m':{'min':lo,'max':hi,'dimensions':[hi[i]-lo[i] for i in range(3)]},'triangles':len(o.data.loop_triangles),'materials':[m.name for m in o.data.materials],'collision_body_height_cm':870 if kind=='UrbanFlat' else 590}
    o.hide_set(True);o.hide_render=True
(ROOT/'build_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HouseTownVariants.blend'))
print('HOUSE_VARIANTS_COMPLETE')
