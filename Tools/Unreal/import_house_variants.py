"""Revisioned imports of derived roof/façade variants, retaining original house assets."""
import json,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from town_common import *
SRC=ROOT/'SourceArt/Architecture/HouseTownVariants'
MAN=json.loads((SRC/'build_manifest.json').read_text())
REPORT={'passed':False,'assets':{},'errors':[],'results':{}}
SM=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()
try:
    original=json.loads((ROOT/'Docs/STREET_IMPORT_RESULTS.json').read_text())['assets']['house']
    original_mesh=unreal.load_asset(original)
    palette={str(s.material_slot_name):s.material_interface for s in original_mesh.static_materials}
    for kind,desc in MAN['variants'].items():
        fbx=SRC/desc['fbx'];folder=BASE+'/Architecture/'+kind+'/r_'+sha(fbx)[:12]
        mesh=import_fbx(fbx,folder,'SM_House_'+kind)
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,palette[str(slot.material_slot_name)])
        height=desc['collision_body_height_cm']
        boxes(mesh,[((0,0,height/2),(600,800,height)),((345,-100,7.5),(90,180,15)),((330,-100,22.5),(60,180,15))])
        EAL.save_loaded_asset(mesh,only_if_is_dirty=False)
        b=mesh.get_bounds();dims=[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2]
        expected=[desc['bounds_m']['dimensions'][i]*100 for i in (1,0,2)]
        if max(abs(a-b) for a,b in zip(dims,expected))>.1:raise RuntimeError('House variant scale mismatch: '+kind)
        if SM.get_num_uv_channels(mesh,0)!=2:raise RuntimeError('House variant UVs')
        REPORT['assets'][kind]=mesh.get_path_name()
        REPORT['results'][kind]={'dimensions_cm':dims,'uv_channels':2,'triangles':mesh.get_static_mesh_description(0).get_triangle_count(),'collision_shapes':SM.get_simple_collision_count(mesh)}
    scene=Scene()
    for name,kind in [('SD_House02','UrbanFlat'),('SD_House04','HipRoof'),('SD_House05','HipRoof')]:
        scene.existing[name].static_mesh_component.set_static_mesh(unreal.load_asset(REPORT['assets'][kind]))
    scene.save();REPORT['passed']=True
except Exception:
    REPORT['errors'].append(traceback.format_exc());raise
finally:(OUT/'house_variants.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
