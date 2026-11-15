"""Independently inspect the tree sources and round-trip every Unreal FBX.

Run with Blender --background --python validate_tree_kit.py. Does not save or
modify any blend/FBX asset. UV0 overlap is intentional for repeated foliage;
this validates UV coverage, finite coordinates and area, not a lightmap atlas.
"""
import json
import math
import hashlib
from pathlib import Path

import bpy
from mathutils import Vector
from io_scene_fbx import parse_fbx

ROOT = Path(__file__).resolve().parent
VARIANTS = ("Hero", "Spread", "Weeping")
EXPECTED = [f"SM_Sakura_{variant}_LOD{lod}" for variant in VARIANTS for lod in range(3)]
SLOTS = ["M_Sakura_Bark", "M_Sakura_Blossom"]
ERRORS = []
WARNINGS = []


def failure(condition, message):
    if condition:
        ERRORS.append(message)


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = [min(p[a] for p in points) for a in range(3)]
    high = [max(p[a] for p in points) for a in range(3)]
    return {"min": low, "max": high, "dimensions": [b - a for a, b in zip(low, high)]}


def inspect_mesh(obj, context, require_identity=True):
    mesh = obj.data
    mesh.calc_loop_triangles()
    prefix = context + ": " + obj.name
    result = {"vertices": len(mesh.vertices), "triangles": len(mesh.loop_triangles),
              "polygons": len(mesh.polygons), "bounds_m": bounds(obj),
              "material_slots": [m.name if m else None for m in mesh.materials],
              "uv_channels": [layer.name for layer in mesh.uv_layers]}
    failure(not mesh.vertices or not mesh.polygons, prefix + " has no usable geometry")
    transform_error = max(abs(obj.matrix_world[r][c] - (1 if r == c else 0))
                          for r in range(4) for c in range(4))
    result["identity_transform_error"] = transform_error
    if require_identity:
        failure(transform_error > 1e-5, prefix + " pivot/transform is not identity at origin")
    failure(len(mesh.materials) != 2, prefix + " must have exactly two render material slots")
    # Blender can append .001 during imports; compare base names when appropriate.
    actual_slots = [(m.name.split(".")[0] if m else None) for m in mesh.materials]
    failure(actual_slots != SLOTS, prefix + " unexpected material slot names/order")
    failure(any(p.material_index >= len(mesh.materials) for p in mesh.polygons),
            prefix + " invalid polygon material index")
    failure(not all(math.isfinite(v) for vert in mesh.vertices for v in vert.co),
            prefix + " non-finite geometry")
    degenerate_geometry = 0
    for tri in mesh.loop_triangles:
        a, b, c = (mesh.vertices[i].co for i in tri.vertices)
        if (b - a).cross(c - a).length < 1e-12:
            degenerate_geometry += 1
    result["degenerate_geometry_triangles"] = degenerate_geometry
    failure(degenerate_geometry > 0, prefix + " contains degenerate geometry")
    failure(not mesh.uv_layers, prefix + " missing UV0")
    uv_reports = {}
    for layer in mesh.uv_layers:
        coords = [tuple(item.uv) for item in layer.data]
        invalid = sum(not all(math.isfinite(x) for x in uv) for uv in coords)
        outside = sum(any(x < -1e-5 or x > 1.00001 for x in uv) for uv in coords)
        degenerate_uv = 0
        for tri in mesh.loop_triangles:
            a, b, c = (layer.data[i].uv for i in tri.loops)
            area2 = abs((b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x))
            if area2 < 1e-12:
                degenerate_uv += 1
        uv_reports[layer.name] = {"nonfinite_loops": invalid,
                                  "outside_unit_square_loops": outside,
                                  "degenerate_triangles": degenerate_uv}
        failure(invalid > 0 or outside > 0 or degenerate_uv > 0,
                prefix + " invalid " + layer.name + " coordinates/area")
    result["uv_checks"] = uv_reports
    color = mesh.color_attributes.get("Color")
    result["color_attribute"] = None
    failure(color is None, prefix + " missing Color vertex colors")
    if color is not None:
        values = [tuple(item.color) for item in color.data]
        invalid_colors = sum(any(not math.isfinite(x) or x < -1e-5 or x > 1.00001 for x in value)
                             for value in values)
        result["color_attribute"] = {"name": color.name, "domain": color.domain,
                                     "data_type": color.data_type, "elements": len(values),
                                     "invalid_elements": invalid_colors,
                                     "channel_min": [min(v[c] for v in values) for c in range(4)],
                                     "channel_max": [max(v[c] for v in values) for c in range(4)]}
        failure(invalid_colors > 0 or not values, prefix + " invalid Color values")
        wind_by_slot = {}
        for slot in range(2):
            ids = set()
            for polygon in mesh.polygons:
                if polygon.material_index == slot:
                    ids.update(polygon.vertices if color.domain == 'POINT' else polygon.loop_indices)
            weights = [values[index][3] for index in ids]
            wind_by_slot[SLOTS[slot]] = [min(weights), max(weights)] if weights else []
        result["wind_alpha_ranges"] = wind_by_slot
        bark_weights = wind_by_slot[SLOTS[0]]
        blossom_weights = wind_by_slot[SLOTS[1]]
        failure(not bark_weights or max(bark_weights) > .001, prefix + " bark must have zero wind weight")
        failure(not blossom_weights or min(blossom_weights) < .3, prefix + " foliage lacks expected wind weights")
    edge_uses = {}
    for poly in mesh.polygons:
        for edge in poly.edge_keys:
            edge_uses[edge] = edge_uses.get(edge, 0) + 1
    result["boundary_edges"] = sum(uses == 1 for uses in edge_uses.values())
    result["nonmanifold_edges_over_two_faces"] = sum(uses > 2 for uses in edge_uses.values())
    result["material_triangle_counts"] = {
        SLOTS[slot]: sum(t.material_index == slot for t in mesh.loop_triangles) for slot in range(2)}
    # A rooted tree should stand above its ground pivot; a few roots may dip
    # below ground by up to 10 cm to avoid visibly floating after placement.
    failure(result["bounds_m"]["min"][2] < -.1, prefix + " extends below ground by more than 10 cm")
    failure(result["bounds_m"]["min"][2] > .02, prefix + " floats above ground pivot")
    failure(result["bounds_m"]["dimensions"][2] < 2, prefix + " unexpectedly small tree")
    return result


def inspect_collision(obj, render_name, context):
    prefix = context + ": " + obj.name
    failure(not obj.name.startswith(("UCX_"+render_name+"_", "UBX_"+render_name+"_",
                                     "UCP_"+render_name+"_", "USP_"+render_name+"_")),
            prefix + " collision does not follow the Unreal naming convention")
    edge_uses = {}
    for poly in obj.data.polygons:
        for edge in poly.edge_keys:
            edge_uses[edge] = edge_uses.get(edge, 0) + 1
    closed = bool(edge_uses) and all(count == 2 for count in edge_uses.values())
    failure(not closed, prefix + " collision hull is not closed")
    # Convexity: for each outward face plane, every vertex must be on or behind it.
    convex = True
    for poly in obj.data.polygons:
        normal, center = poly.normal, poly.center
        if any(normal.dot(vertex.co - center) > 1e-4 for vertex in obj.data.vertices):
            convex = False
            break
    failure(not convex, prefix + " collision hull has concavity or flipped normals")
    return {"closed": closed, "convex": convex, "vertices": len(obj.data.vertices),
            "bounds_m": bounds(obj)}


def fbx_metadata(path):
    root, version = parse_fbx.parse(str(path))
    settings = next(e for e in root.elems if e.id == b"GlobalSettings")
    props = next(e for e in settings.elems if e.id == b"Properties70")
    wanted = (b"UnitScaleFactor", b"OriginalUnitScaleFactor", b"UpAxis", b"UpAxisSign",
              b"FrontAxis", b"FrontAxisSign", b"CoordAxis", b"CoordAxisSign")
    values = {e.props[0].decode(): e.props[-1] for e in props.elems
              if e.id == b"P" and e.props[0] in wanted}
    return version, values


bpy.ops.wm.open_mainfile(filepath=str(ROOT / "SakuraTreeKit.blend"))
source_scene = bpy.context.scene
unit_scale = source_scene.unit_settings.scale_length
failure(source_scene.unit_settings.system != "METRIC" or abs(unit_scale - 1) > 1e-8,
        "Source must use meters (METRIC, scale_length=1)")
atlas_path = ROOT / "Textures" / "T_Sakura_Blossom_Atlas.png"
atlas = bpy.data.images.get("T_Sakura_Blossom_Atlas")
atlas_report = {}
failure(not atlas_path.exists() or atlas is None, "Shared blossom atlas is missing")
if atlas is not None:
    width, height = atlas.size
    alpha = list(atlas.pixels)[3::4]
    coverage = []
    for quadrant in range(4):
        ox, oy = (quadrant % 2) * (width // 2), (quadrant // 2) * (height // 2)
        tile_values = [alpha[y*width+x] for y in range(oy, oy+height//2)
                       for x in range(ox, ox+width//2)]
        coverage.append(sum(value > .4 for value in tile_values) / len(tile_values))
    atlas_report = {"dimensions": [width, height], "packed_in_source": bool(atlas.packed_file),
                    "colorspace": atlas.colorspace_settings.name,
                    "masked_coverage_per_quadrant_at_0_4": coverage,
                    "min_alpha": min(alpha), "max_alpha": max(alpha)}
    failure(width != height or width not in (1024, 2048), "Expected a 1024 or 2048 square shared atlas")
    failure(not atlas.packed_file, "Source atlas must be packed for portable Blender editing")
    failure(atlas.colorspace_settings.name != "sRGB", "Blossom color atlas should use sRGB")
    failure(any(value < .15 or value > .85 for value in coverage), "Atlas quadrant mask coverage is unexpected")
sources = {}
collisions = {}
for name in EXPECTED:
    obj = bpy.data.objects.get(name)
    if not obj or obj.type != "MESH":
        ERRORS.append("Missing source export mesh " + name)
        continue
    sources[name] = inspect_mesh(obj, "Source")
    collisions[name] = {other.name: inspect_collision(other, name, "Source")
                        for other in bpy.data.objects if other.type == "MESH"
                        and other.name.startswith(tuple(p + name + "_" for p in ("UCX_", "UBX_", "UCP_", "USP_")))}

for variant in VARIANTS:
    names = [f"SM_Sakura_{variant}_LOD{lod}" for lod in range(3)]
    if all(name in sources for name in names):
        counts = [sources[name]["triangles"] for name in names]
        failure(not counts[0] > counts[1] > counts[2], variant + " LOD triangle counts are not descending")
        if counts[0] > 30000:
            WARNINGS.append(variant + " LOD0 exceeds the suggested 30k triangle review threshold")
        for lod in (1, 2):
            base = sources[names[0]]["bounds_m"]["dimensions"]
            simplified = sources[names[lod]]["bounds_m"]["dimensions"]
            if any(abs(a-b)/max(a, 1e-5) > .12 for a, b in zip(base, simplified)):
                WARNINGS.append(names[lod] + " silhouette dimensions differ more than 12% from LOD0")

roundtrips = {}
for name in EXPECTED:
    path = ROOT / "Exports" / (name + ".fbx")
    if not path.exists():
        ERRORS.append("Missing FBX " + path.name)
        continue
    version, metadata = fbx_metadata(path)
    failure(metadata.get("UpAxis") != 2 or metadata.get("UpAxisSign") != 1,
            name + " FBX is not +Z up")
    failure(abs(metadata.get("UnitScaleFactor", 0) - 100) > .001,
            name + " FBX units do not encode 100 centimeters per meter")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    bpy.context.view_layer.update()
    render_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"
                     and not o.name.startswith(("UCX_", "UBX_", "UCP_", "USP_"))]
    imported_hulls = [o for o in bpy.context.scene.objects if o.type == "MESH"
                      and o.name.startswith(("UCX_", "UBX_", "UCP_", "USP_"))]
    failure(len(render_meshes) != 1, name + " FBX must contain exactly one render mesh")
    entry = {"fbx_version": version, "metadata": metadata,
             "render_mesh_count": len(render_meshes), "collision_hull_count": len(imported_hulls)}
    if len(render_meshes) == 1:
        obj = render_meshes[0]
        entry["mesh"] = inspect_mesh(obj, "Roundtrip")
        if name in sources:
            expected = sources[name]
            actual = entry["mesh"]
            max_error = max(abs(expected["bounds_m"][key][axis] - actual["bounds_m"][key][axis])
                            for key in ("min", "max") for axis in range(3))
            entry["max_bounds_error_m"] = max_error
            failure(max_error > .0001, name + " roundtrip scale/orientation/bounds mismatch")
            failure(actual["triangles"] != expected["triangles"], name + " roundtrip triangle count mismatch")
            expected_colors = expected["color_attribute"]
            actual_colors = actual["color_attribute"]
            if expected_colors and actual_colors:
                color_error = max(abs(expected_colors[key][axis] - actual_colors[key][axis])
                                  for key in ("channel_min", "channel_max") for axis in range(4))
                entry["max_color_extrema_error_linear"] = color_error
                failure(color_error > .01, name + " vertex colors changed during roundtrip")
    entry["collision"] = {obj.name: inspect_collision(obj, name, "Roundtrip") for obj in imported_hulls}
    if name in collisions:
        failure(len(imported_hulls) != len(collisions[name]), name + " roundtrip collision hull count mismatch")
    roundtrips[name] = entry

report = {"blender_version": bpy.app.version_string, "source_file": "SakuraTreeKit.blend",
          "unit_scale_length": unit_scale, "uv0_overlap_policy": "Allowed: repeated foliage/bark UV islands; not a baked lightmap atlas",
          "checks": sources, "source_collision": collisions, "fbx_roundtrips": roundtrips, "blossom_atlas": atlas_report,
          "validated_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in [ROOT/"SakuraTreeKit.blend", atlas_path]
                                + [ROOT/"Exports"/(name+".fbx") for name in EXPECTED] if path.exists()},
          "warnings": WARNINGS, "errors": ERRORS, "passed": not ERRORS}
(ROOT / "validation_blender.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("SAKURA_TREE_VALIDATION " + json.dumps({"passed": not ERRORS, "source_meshes": len(sources),
      "fbx_files": len(roundtrips), "errors": ERRORS, "warnings": WARNINGS}))
if ERRORS:
    raise RuntimeError("Sakura tree validation failed; see validation_blender.json")
