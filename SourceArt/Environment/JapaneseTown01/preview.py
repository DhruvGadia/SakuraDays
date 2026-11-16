"""Render the existing JapaneseTown01.blend without modifying it or any FBX.

Use Blender --background JapaneseTown01.blend --threads 4 --python preview.py.
Cycles is explicitly CPU-only; four 1000-pixel previews use 16 samples.
"""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
assert Path(bpy.data.filepath).resolve()==ROOT/'JapaneseTown01.blend'
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU'
sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
stage=bpy.data.collections['04_PREVIEW_ONLY'];modules=bpy.data.collections['01_REUSABLE_MODULES']
cam=sc.camera;cam.data.type='ORTHO'
def camera(pos,target,scale):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
renders=[]
def render(name,w=1000,h=750):
    if '--signs-only' in sys.argv and name!='Japanese_Signage.png':
        renders.append(name);return
    sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.filepath=str(ROOT/'Previews'/name)
    bpy.ops.render.render(write_still=True);renders.append(name)
camera((10,-16,9),(0,-.3,3.1),11.5);render('RamenShop_ThreeQuarter.png')
camera((0,-20,3.7),(0,-2.5,3.1),8);render('RamenShop_Front.png',1000,875)
for o in bpy.data.collections['02_RAMEN_ASSEMBLY'].objects:o.hide_render=True
preview=[]
def show(n,pos):
    o=bpy.data.objects.new('PREVIEW_'+n,modules.objects[n].data);stage.objects.link(o);o.location=pos;preview.append(o)
for n,pos in [('SM_VendingMachine',(-3,0,0)),('SM_CityBicycle',(-1.3,-.1,0)),('SM_PublicNoticeboard',(1.1,.4,0)),('SM_RoadsideMirror',(3,1.0,0)),('SM_ResidentialMailbox',(3,-.9,0)),('SM_AC_Outdoor',(-.1,-.7,0))]:show(n,pos)
camera((8,-17,9),(0,.0,1.2),8.7);render('TownProps_Lineup.png',1000,656)
for o in preview:o.hide_render=True
for o in stage.objects:
    if o.name=='PREVIEW_Ground':o.hide_render=True
# Deliberately separate lettering specimens so no sign overlaps another.
for n,pos in [('SM_Sign_Hana_Japanese',(-2,0,1.55)),('SM_Sign_SakuraStreet',(-2,0,.60)),('SM_Sign_Ramen_Fascia',(1.4,0,1.55)),('SM_Sign_Ramen_Vertical',(1.05,0,-.65)),('SM_Sign_Open',(2.35,0,-.10))]:show(n,pos)
camera((0,-14,1.1),(0,0,.75),8);render('Japanese_Signage.png',1000,625)
(ROOT/'Previews/preview_manifest.json').write_text(json.dumps({'source':'JapaneseTown01.blend','source_modified':False,'renderer':'Cycles CPU','samples':16,'files':renders},indent=2),encoding='utf-8')
print('TOWN_PREVIEWS_COMPLETE',flush=True)
