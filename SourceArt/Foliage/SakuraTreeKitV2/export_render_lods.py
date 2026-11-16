"""Re-export existing LOD1/2 meshes without collision; source blend unchanged."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SakuraTreeKit.blend'))
for kind in ('Hero','Spread','Weeping'):
    for lod in (1,2):
        obj=bpy.data.objects[f'SM_Sakura_{kind}_LOD{lod}']
        bpy.ops.object.select_all(action='DESELECT')
        obj.hide_set(False);obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.export_scene.fbx(filepath=str(ROOT/'Exports'/(obj.name+'.fbx')),
            use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',
            use_mesh_modifiers=True,mesh_smooth_type='FACE',use_triangles=True,
            bake_anim=False,path_mode='RELATIVE',use_custom_props=True,colors_type='SRGB')
        obj.hide_set(True)
