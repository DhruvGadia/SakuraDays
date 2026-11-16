"""Revisioned Japanese town FBX import and geometry/material validation."""
import json, math, sys, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from town_common import *

SOURCE=ROOT/'SourceArt/Environment/JapaneseTown01'
MANIFEST=json.loads((SOURCE/'build_manifest.json').read_text(encoding='utf-8'))
SELECT={
 'ramen':'SM_RamenShop_Assembled','hana_sign':'SM_Sign_Hana_Japanese',
 'open_sign':'SM_Sign_Open','street_sign':'SM_Sign_SakuraStreet',
 'vending':'SM_VendingMachine','bicycle':'SM_CityBicycle','noticeboard':'SM_PublicNoticeboard',
 'mirror':'SM_RoadsideMirror','mailbox':'SM_ResidentialMailbox',
 'shutter':'SM_Shutter_76x140','gutter':'SM_Gutter_3m','downpipe':'SM_Downpipe_3m',
 'balcony':'SM_Balcony_Compact_320','lantern':'SM_Ramen_Lantern'}
REPORT={'passed':False,'assets':{},'results':{},'errors':[],'signs':{}}
SM=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.StaticMeshEditorSubsystem()

try:
    assert Path(unreal.Paths.project_dir()).resolve()==ROOT
    mats={n:material(n.removeprefix('M_'),h,emission=.08 if 'Paper' in n else 0) for n,h in MANIFEST['materials'].items()}
    for key,name in SELECT.items():
        desc=MANIFEST['modules'][name];fbx=SOURCE/desc['fbx']
        fp=hashlib.sha256((sha(fbx)+json.dumps(MANIFEST['materials'],sort_keys=True)+'town_import_v1').encode()).hexdigest()
        folder=BASE+'/Meshes/'+name+'/r_'+fp[:12]
        mesh=import_fbx(fbx,folder,name)
        for i,slot in enumerate(mesh.static_materials):
            n=str(slot.material_slot_name)
            if n not in mats:raise RuntimeError('Unknown slot '+n)
            mesh.set_material(i,mats[n])
        if key=='ramen':boxes(mesh,[((0,0,280),(460,600,560))])
        elif key=='vending':boxes(mesh,[((0,0,93),(76,100,186))])
        elif key=='bicycle':boxes(mesh,[((0,0,52),(48,180,104))])
        elif key=='noticeboard':boxes(mesh,[((0,0,100),(20,160,200))])
        elif key=='mirror':boxes(mesh,[((0,0,130),(12,12,260))])
        elif key=='mailbox':boxes(mesh,[((0,0,55),(30,32,110))])
        settings=SM.get_lod_build_settings(mesh,0)
        settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
        SM.set_lod_build_settings(mesh,0,settings)
        EAL.set_metadata_tag(mesh,'SakuraDays.TownSourceFingerprint',fp)
        EAL.save_loaded_asset(mesh,only_if_is_dirty=False)
        bounds=mesh.get_bounds();dims=[2*bounds.box_extent.x,2*bounds.box_extent.y,2*bounds.box_extent.z]
        expected=[desc['bounds_m']['dimensions'][i]*100 for i in (1,0,2)]
        errors=[]
        if max(abs(a-b) for a,b in zip(dims,expected))>.1:errors.append('Centimeter scale/orientation mismatch')
        slots=[str(x.material_slot_name) for x in mesh.static_materials]
        if slots!=desc['material_slots']:errors.append('Material slots mismatch')
        triangles=mesh.get_static_mesh_description(0).get_triangle_count()
        if triangles!=desc['triangles']:errors.append('Triangle count mismatch')
        uvs=SM.get_num_uv_channels(mesh,0)
        if uvs!=desc['uv_channels']:errors.append('UV channel mismatch')
        invalid=0;count=0
        for section in range(mesh.get_num_sections(0)):
            _,_,normals,_,_=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,section)
            for n in normals:
                length=math.sqrt(n.x*n.x+n.y*n.y+n.z*n.z);count+=1
                invalid+=not math.isfinite(length) or abs(length-1)>.02
        if invalid or not count:errors.append('Invalid render normals')
        REPORT['assets'][key]=mesh.get_path_name()
        REPORT['results'][key]={'dimensions_cm':dims,'expected_cm':expected,'triangles':triangles,'uv_channels':uvs,'materials':slots,'normal_samples':count,'invalid_normals':invalid,'collision_shapes':SM.get_simple_collision_count(mesh),'errors':errors}
        if desc.get('text'):REPORT['signs'][key]=desc['text']
        REPORT['errors'] += [key+': '+e for e in errors]
    REPORT['glyph_coverage']=MANIFEST['glyph_coverage']
    REPORT['passed']=not REPORT['errors'] and len(REPORT['assets'])==len(SELECT)
except Exception:
    REPORT['errors'].append(traceback.format_exc());raise
finally:
    (OUT/'imports.json').write_text(json.dumps(REPORT,indent=2,ensure_ascii=False),encoding='utf-8')
