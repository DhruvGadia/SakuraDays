"""Render LOD comparisons from the saved kit; never save or change source files.

Run with Blender --background --python preview_lods.py. Each PNG shows the
same tree at LOD0/1/2 under the saved lineup lighting, camera and scale.
"""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "SakuraTreeKit.blend"))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

display = [bpy.data.objects['PREVIEW_' + kind] for kind in ('Hero', 'Spread', 'Weeping')]
labels = sorted((obj for obj in bpy.data.collections['03_PREVIEW_ONLY_never_export'].objects
                 if obj.type == 'FONT'), key=lambda obj: obj.name)
assert len(labels) == 8, 'Expected title, subtitle and six saved lineup captions'
labels[1].data.body = 'SAME CAMERA / SAME SCALE / THREE GEOMETRY LEVELS'

for kind in ('Hero', 'Spread', 'Weeping'):
    labels[0].data.body = 'S A K U R A D A Y S   /   ' + kind.upper() + '   L O D S'
    for lod, obj in enumerate(display):
        source = bpy.data.objects[f'SM_Sakura_{kind}_LOD{lod}']
        obj.data = source.data
        obj.hide_render = False
        source.data.calc_loop_triangles()
        triangles = len(source.data.loop_triangles)
        labels[2 + lod * 2].data.body = f'LOD {lod}'
        labels[3 + lod * 2].data.body = f'{triangles:,} TRIANGLES  /  2 MATERIALS'
    bpy.context.view_layer.update()
    scene.render.filepath = str(ROOT / 'Previews' / f'Sakura_{kind}_LODs.png')
    bpy.ops.render.render(write_still=True)
    print(f'SAKURA_LOD_PREVIEW_COMPLETE {kind}', flush=True)

# Intentional: no save_mainfile call. Original editable sources remain intact.
