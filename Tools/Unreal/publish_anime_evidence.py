"""Check and retain local Prompt 13 evidence; never uploads or edits images."""
import hashlib
import json
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / '.dream-loop/prompt13'
DEST = ROOT / 'Docs/Validation/AnimeRefinement'
IMAGES = ROOT / 'Docs/Images/AnimeRefinement'
LABELS = ('before', 'pass1', 'pass2', 'pass3')
VIEWS = ('MainStreet', 'Reference', 'Gameplay', 'Hana', 'Residential', 'Storefront', 'StreetSign', 'Noticeboard')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, str):
        return value.replace(str(ROOT), '<PROJECT>').replace(ROOT.as_posix(), '<PROJECT>')
    if isinstance(value, dict):
        return {clean(k): clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(data), indent=2, ensure_ascii=False), encoding='utf-8')


def main():
    baseline = json.loads((WORK/'before/scene_snapshot.json').read_text(encoding='utf-8'))
    manifest = {'map': baseline['map'], 'pre_refinement_checkpoint': '97822a7',
                'target_sha256': baseline['target_sha256'], 'iterations': {},
                'performance_scope': 'PIE functionality and screenshots; no packaged FPS or GPU performance claim.'}
    final_hash = None
    for label in LABELS:
        folder = WORK / label
        result = json.loads((folder/'validation.json').read_text(encoding='utf-8'))
        snapshot = json.loads((folder/'scene_snapshot.json').read_text(encoding='utf-8'))
        assert result['status'] == 'complete' and result['passed'], label
        assert len(result['checks']) == 32 and all(c['passed'] for c in result['checks']), label
        assert result['petals_runtime']['passed'], label
        assert snapshot['target_sha256'] == baseline['target_sha256'], 'Target changed'
        preserved = []
        for name, original in baseline['actors'].items():
            if 'mesh' not in original and not any(t in original['class'] for t in ('CameraActor', 'PlayerStart')):
                continue
            assert name in snapshot['actors'], 'Actor removed: ' + name
            current = snapshot['actors'][name]
            for prop in ('class', 'position', 'rotation', 'scale', 'mesh', 'collision_profile', 'collision_enabled'):
                assert current.get(prop) == original.get(prop), (label, name, prop)
            preserved.append(name)
        entry = {'passed_checks': len(result['checks']), 'errors': result['errors'],
                 'preserved_geometry_camera_spawn_actors': len(preserved),
                 'map_sha256': snapshot['saved_map_sha256'], 'screenshots': {}}
        for view in VIEWS:
            image = folder/(view+'.png')
            with image.open('rb') as handle:
                header = handle.read(24)
            assert header[:8] == b'\x89PNG\r\n\x1a\n'
            assert struct.unpack('>II', header[16:24]) == (1920, 1080)
            # Preserve all before/final views; retain two views of each middle pass.
            retain = label in ('before','pass3') or view in ('MainStreet','Reference')
            if retain:
                output = IMAGES/label/(view+'.png')
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image, output)
                path = output.relative_to(ROOT).as_posix()
            else:
                path = '<LOCAL_DREAM_LOOP>/'+label+'/'+view+'.png'
            entry['screenshots'][view] = {'path': path, 'sha256': sha(image),
                                         'dimensions': [1920,1080], 'permanent_copy': retain,
                                         'source': 'Genuine Unreal PIE HighResShot'}
        write(DEST/(label+'_PIE.json'), result)
        write(DEST/(label+'_preservation.json'), {'passed': True, 'actors_checked': preserved,
              'properties': ['class','position','rotation','scale','mesh','collision_profile','collision_enabled']})
        if label != 'before':
            applied = json.loads((ROOT/'Saved/AnimeRefinement'/label/'applied.json').read_text(encoding='utf-8'))
            assert applied.get('applied') and not applied.get('errors'), label+' authoring failed'
            write(DEST/(label+'_applied.json'), applied)
        manifest['iterations'][label] = entry
        final_hash = snapshot['saved_map_sha256']
    assert sha(ROOT/'Content/SakuraDays/Maps/L_SakuraStreet.umap') == final_hash, 'Map changed after final test'
    manifest['final_saved_map_sha256'] = final_hash
    write(DEST/'manifest.json', manifest)
    print('Verified four 32-check PIE runs, unchanged geometry/collision/cameras, and 32 genuine 1080p captures; retained 20 images locally.')


if __name__ == '__main__':
    main()
