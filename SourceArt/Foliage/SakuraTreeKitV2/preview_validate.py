"""Read-only mesh QA and CPU preview of the already exported V2 kit.

Does not regenerate sources or FBX files. Run using Blender --background --python.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'SakuraTreeKit.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_percentage = 100
scene.render.resolution_x = 1000
scene.render.resolution_y = 640
scene.render.image_settings.file_format = 'PNG'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8

results = {'source': 'SakuraTreeKit.blend', 'checks': [], 'meshes': {}}
def check(name, result):
    results['checks'].append({'name': name, 'passed': bool(result)})

for kind in ('Hero', 'Spread', 'Weeping'):
    for lod in range(3):
        name = f'SM_Sakura_{kind}_LOD{lod}'
        obj = bpy.data.objects[name]
        mesh = obj.data
        mesh.calc_loop_triangles()
        uv = mesh.uv_layers.active
        attr = mesh.color_attributes.get('Color')
        nonfinite = sum(not math.isfinite(v) for p in mesh.vertices for v in p.co)
        degenerate = sum(t.area < 1e-10 for t in mesh.loop_triangles)
        bad_uv = sum(not math.isfinite(c) or c < -.0001 or c > 1.0001 for d in uv.data for c in d.uv)
        hulls = [o for o in bpy.data.objects if o.name.startswith('UCX_'+name+'_')]
        check(name+' origin/scale', obj.location.length < 1e-6 and (obj.scale - Vector((1,1,1))).length < 1e-6)
        check(name+' finite nondegenerate geometry', not nonfinite and not degenerate)
        check(name+' UV0 in zero-to-one atlas', not bad_uv)
        check(name+' two material slots', len(mesh.materials) == 2)
        check(name+' vertex color and wind weights', attr is not None and attr.domain == 'POINT')
        check(name+' three convex trunk proxies', len(hulls) == 3)
        dims = [max(v.co[i] for v in mesh.vertices)-min(v.co[i] for v in mesh.vertices) for i in range(3)]
        results['meshes'][name] = {'triangles': len(mesh.loop_triangles), 'dimensions_m': dims, 'foliage_cards': sum(p.material_index == 1 for p in mesh.polygons), 'degenerate_triangles': degenerate, 'uv_layers': [u.name for u in mesh.uv_layers], 'collision_hulls': len(hulls)}

results['passed'] = all(c['passed'] for c in results['checks'])
(ROOT/'Previews'/'source_validation.json').write_text(json.dumps(results, indent=2), encoding='utf-8')

scene.render.filepath = str(ROOT/'Previews'/'SakuraTreeKitV2_Lineup.png')
bpy.ops.render.render(write_still=True)

for obj in bpy.data.objects:
    if obj.name.startswith('PREVIEW_Label'):
        obj.hide_render = True
for kind in ('Hero', 'Spread', 'Weeping'):
    obj = bpy.data.objects['PREVIEW_'+kind]
    obj.hide_render = kind != 'Hero'
    obj.location = (0,0,0)
scene.camera.location = (11,-19,8.5)
scene.camera.rotation_euler = (Vector((0,0,3.8))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.ortho_scale = 14.0
scene.render.resolution_x = 1000
scene.render.resolution_y = 850
scene.render.filepath = str(ROOT/'Previews'/'Sakura_Hero_V2_ThreeQuarter.png')
bpy.ops.render.render(write_still=True)
print('V2_SOURCE_QA_PASS', results['passed'], flush=True)
