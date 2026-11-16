"""Copy passing local Unreal evidence into versioned Docs; no remote publish."""
import hashlib, json, shutil, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LOCAL=ROOT/'Saved/TownRefinement'
DEST=ROOT/'Docs/Validation/TownRefinement'
IMAGES=ROOT/'Docs/Images'
report=json.loads((LOCAL/'PIE_final/validation.json').read_text(encoding='utf-8'))
assert report['status']=='complete' and report['passed'], 'Final PIE must pass first'
assert report['petals_runtime']['passed'], 'Live Niagara evidence required'
DEST.mkdir(parents=True,exist_ok=True);IMAGES.mkdir(exist_ok=True)
def relative_values(value):
    if isinstance(value,str):
        return value.replace(str(ROOT)+'\\','').replace(ROOT.as_posix()+'/','').replace('\\','/')
    if isinstance(value,dict):return {k:relative_values(v) for k,v in value.items()}
    if isinstance(value,list):return [relative_values(v) for v in value]
    return value
manifest={'map':'/Game/SakuraDays/Maps/L_SakuraStreet','screenshots':{},'evidence':{}}
for name in ('MainStreet','Hana','Residential','Storefront','Gameplay','Reference','StreetSign','Noticeboard'):
    source=LOCAL/'PIE_final'/(name+'.png');header=source.read_bytes()[:24]
    assert header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(1920,1080)
    target=IMAGES/('Town_'+name+'.png');shutil.copy2(source,target)
    manifest['screenshots'][name]={'path':target.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'dimensions':[1920,1080],'source':'Genuine Unreal PIE HighResShot'}
for name in ('imports','house_variants','trees','geometry','identity','materials','lighting','petals'):
    data=json.loads((LOCAL/(name+'.json')).read_text(encoding='utf-8'))
    assert data['passed'], name+' did not pass'
    target=DEST/(name+'.json');target.write_text(json.dumps(relative_values(data),indent=2,ensure_ascii=False),encoding='utf-8')
    manifest['evidence'][name]=target.relative_to(ROOT).as_posix()
for stage in ('geometry','identity','materials','lighting','final'):
    data=json.loads((LOCAL/('PIE_'+stage)/'validation.json').read_text(encoding='utf-8'))
    assert data['passed'], stage+' PIE did not pass'
    target=DEST/('PIE_'+stage+'.json');target.write_text(json.dumps(relative_values(data),indent=2,ensure_ascii=False),encoding='utf-8')
    manifest['evidence']['PIE_'+stage]=target.relative_to(ROOT).as_posix()
manifest['saved_map_sha256']=hashlib.sha256((ROOT/'Content/SakuraDays/Maps/L_SakuraStreet.umap').read_bytes()).hexdigest()
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Published local evidence for '+str(len(manifest['screenshots']))+' genuine 1080p screenshots.')
