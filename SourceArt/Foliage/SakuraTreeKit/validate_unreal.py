"""Import the nine tree exports into an isolated test project, never SakuraDays.

Requires the successful Blender validation report. Import source meshes at scale
1 with scene units converted to Unreal centimeters and Blender -Y as UE +X.
This checks geometry, slots, UVs and custom collision, not the final material
appearance, automatic LOD transitions, packaged performance or gameplay.
"""
import json
import uuid
import hashlib
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parent
assert "SakuraTreeUEValidation" in unreal.Paths.project_dir(), "Use only the isolated SakuraTreeUEValidation project"
source = json.loads((ROOT / "validation_blender.json").read_text(encoding="utf-8"))
assert source["passed"], "Blender source/export validation must pass first"
for relative_path, digest in source.get("validated_sha256", {}).items():
    assert hashlib.sha256((ROOT/relative_path).read_bytes()).hexdigest() == digest, (
        "Source/export changed after Blender validation: " + relative_path)
destination = "/Game/SakuraTreeValidation/Check_" + uuid.uuid4().hex[:8]
tasks = []
for name in source["checks"]:
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.one_convex_hull_per_ucx = True
    data.generate_lightmap_u_vs = False
    data.convert_scene = True
    data.convert_scene_unit = True
    data.force_front_x_axis = True
    data.import_uniform_scale = 1.0
    data.vertex_color_import_option = unreal.VertexColorImportOption.REPLACE
    task = unreal.AssetImportTask()
    task.filename = str(ROOT / "Exports" / (name + ".fbx"))
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = False
    task.options = options
    task.factory = unreal.FbxFactory()
    tasks.append(task)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
if subsystem is None:
    # Python commandlets do not register editor subsystems. These read-only mesh
    # queries can use an explicitly instantiated subsystem in the isolated test.
    subsystem = unreal.StaticMeshEditorSubsystem()
results = {}
errors = []
for task in tasks:
    name = task.destination_name
    meshes = [obj for obj in task.get_objects() if isinstance(obj, unreal.StaticMesh)]
    if len(meshes) != 1:
        errors.append(name + " expected 1 static mesh, found " + str(len(meshes)))
        continue
    mesh = meshes[0]
    b = mesh.get_bounds()
    dims = [2*b.box_extent.x, 2*b.box_extent.y, 2*b.box_extent.z]
    desc = mesh.get_static_mesh_description(0)
    slots = [str(slot.material_slot_name) for slot in mesh.static_materials]
    convex_count = subsystem.get_convex_collision_count(mesh)
    uv_count = subsystem.get_num_uv_channels(mesh, 0)
    result = {"asset": mesh.get_path_name(), "dimensions_cm": dims,
              "bounds_center_cm": [b.origin.x, b.origin.y, b.origin.z],
              "material_slots": slots, "uv_channels": uv_count,
              "convex_collision_hulls": convex_count,
              "lods_in_individual_file": subsystem.get_lod_count(mesh),
              "source_triangles": desc.get_triangle_count() if desc else 0,
              "source_vertex_instances": desc.get_vertex_instance_count() if desc else 0}
    expected = source["checks"][name]
    expected_dims = expected["bounds_m"]["dimensions"]
    # Force Front X maps source -Y to Unreal +X, X to Unreal +Y, Z remains Z.
    converted_dims = [expected_dims[1]*100, expected_dims[0]*100, expected_dims[2]*100]
    result["expected_dimensions_cm"] = converted_dims
    result["max_dimensions_error_cm"] = max(abs(a-b) for a, b in zip(dims, converted_dims))
    if result["max_dimensions_error_cm"] > .1:
        errors.append(name + " centimeter scale/orientation mismatch")
    if slots != ["M_Sakura_Bark", "M_Sakura_Blossom"]:
        errors.append(name + " wrong material slots/order")
    if uv_count != len(expected["uv_channels"]):
        errors.append(name + " wrong UV channel count")
    if convex_count != len(source["source_collision"][name]):
        errors.append(name + " wrong custom collision hull count")
    if not desc:
        errors.append(name + " no source mesh description")
    else:
        if desc.get_triangle_count() != expected["triangles"]:
            errors.append(name + " triangle count changed in Unreal import")
        sample = desc.get_vertex_instance_uv(unreal.VertexInstanceID(0), 0)
        result["uv0_sample"] = [sample.x, sample.y]
    results[name] = result

report = {"engine": unreal.SystemLibrary.get_engine_version(),
          "isolated_project": unreal.Paths.project_dir(),
          "import_settings": {"force_front_x_axis": True, "convert_scene": True,
                              "convert_scene_unit": True, "import_uniform_scale": 1,
                              "combine_meshes": True, "auto_generate_collision": False,
                              "generate_lightmap_uvs": False, "vertex_color_import_option": "REPLACE"},
          "scope": "Fresh isolated static mesh imports; materials/LOD transitions/gameplay/performance not tested",
          "results": results, "errors": errors, "passed": not errors}
(ROOT / "validation_unreal.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
unreal.log("SAKURA_TREE_UE_VALIDATION " + json.dumps(report))
if errors:
    raise RuntimeError("Sakura tree Unreal import validation failed: " + str(errors))
