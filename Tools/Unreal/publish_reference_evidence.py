"""Retain verified real captures for the newly supplied reference follow-up."""
import json
import shutil
import struct
from pathlib import Path
from publish_anime_evidence import ROOT, VIEWS, sha, write

WORK = ROOT / '.dream-loop/prompt13'
DEST = ROOT / 'Docs/Validation/AnimeReferenceUpdate'
IMAGES = ROOT / 'Docs/Images/AnimeReferenceUpdate'
REFS = Path('C:/Users/HP/Documents/SakuraDays_Codex_Prompt_Pack/References')
REFERENCE_NAMES = (
    '02_School_Campus.png', '03_Riverside_Path.png', '04_Hilltop_Overlook.png',
    '05_Local_Cafe.png', '06_Residential_Alley.png', '07_Train_Station.png',
    '08_Evening_Sunset.png', '09_Night_Festival.png', 'Style_A.png', 'Style_B.png')


def main():
    baseline = json.loads((WORK/'pass3/scene_snapshot.json').read_text(encoding='utf-8'))
    final = json.loads((WORK/'references/scene_snapshot.json').read_text(encoding='utf-8'))
    result = json.loads((WORK/'references/validation.json').read_text(encoding='utf-8'))
    applied = json.loads((ROOT/'Saved/AnimeRefinement/references/applied.json').read_text(encoding='utf-8'))
    assert result['status']=='complete' and result['passed'] and not result['errors']
    assert len(result['checks'])==32 and all(c['passed'] for c in result['checks'])
    assert result['petals_runtime']['passed'] and applied['applied'] and not applied['errors']
    assert final['target_sha256']==baseline['target_sha256']
    assert sha(ROOT/'Content/SakuraDays/Maps/L_SakuraStreet.umap')==final['saved_map_sha256']
    checked=[]
    for name, old in baseline['actors'].items():
        if 'mesh' not in old and not any(t in old['class'] for t in ('CameraActor','PlayerStart')):
            continue
        assert name in final['actors'], 'Missing preserved actor '+name
        new=final['actors'][name]
        for prop in ('class','position','rotation','scale','mesh','collision_profile','collision_enabled'):
            assert new.get(prop)==old.get(prop), (name,prop)
        checked.append(name)
    manifest={'map':final['map'], 'checkpoint':'6ec5b17',
              'before_commit':'ff30d2f', 'before_map_sha256':baseline['saved_map_sha256'],
              'final_saved_map_sha256':final['saved_map_sha256'],
              'target_sha256':final['target_sha256'], 'checks_passed':len(result['checks']),
              'preserved_geometry_collision_camera_spawn_records':len(checked),
              'references':{name:sha(REFS/name) for name in REFERENCE_NAMES}, 'images':{}}
    for view in VIEWS:
        source=WORK/'references'/(view+'.png')
        with source.open('rb') as handle:
            header=handle.read(24)
        assert header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(1920,1080)
        output=IMAGES/(view+'.png');output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,output)
        before=ROOT/'Docs/Images/AnimeRefinement/pass3'/(view+'.png')
        assert sha(before)==sha(WORK/'pass3'/(view+'.png'))
        manifest['images'][view]={'before':before.relative_to(ROOT).as_posix(),
            'before_sha256':sha(before), 'after':output.relative_to(ROOT).as_posix(),
            'after_sha256':sha(output), 'dimensions':[1920,1080], 'source':'Genuine Unreal PIE HighResShot'}
    write(DEST/'PIE.json',result)
    write(DEST/'applied.json',applied)
    write(DEST/'preservation.json',{'passed':True,'actors':checked})
    write(DEST/'manifest.json',manifest)
    print('Verified 32 PIE checks, preserved %d records and retained 8 genuine 1080p captures.' % len(checked))


if __name__=='__main__':
    main()
