"""Read-only source/FBX verification; run using Blender --background --python.

Checks every prototype and the assembled export. Source UV0 islands intentionally
repeat across assembly instances; UV1 in the assembled FBX must be unique.
No project or source-art assets are saved by this script.
"""
import hashlib
import json
import math
import re
from pathlib import Path

import bpy
from mathutils import Vector
from io_scene_fbx import parse_fbx

ROOT = Path(__file__).resolve().parent
ERRORS = []


def check(condition, message):
    if not condition:
        ERRORS.append(message)


def bounds(obj):
    points = [obj.matrix_world @ Vector(point) for point in obj.bound_box]
    low = [min(point[a] for point in points) for a in range(3)]
    high = [max(point[a] for point in points) for a in range(3)]
    return {"min": low, "max": high, "dimensions": [b-a for a, b in zip(low, high)]}


def base_name(name):
    return re.sub(r"\.\d{3}$", "", name)


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def clipped_area(first, second):
    polygon = list(first)
    if cross(*second) < 0:
        second = list(reversed(second))
    for i in range(3):
        a, b = second[i], second[(i+1) % 3]
        output = []
        if not polygon:
            return 0.0
        for j, start in enumerate(polygon):
            end = polygon[(j+1) % len(polygon)]
            cs, ce = cross(a, b, start), cross(a, b, end)
            if cs >= -1e-13:
                output.append(start)
            if (cs > 0 and ce < 0) or (cs < 0 and ce > 0):
                factor = cs/(cs-ce)
                output.append((start[0]+factor*(end[0]-start[0]), start[1]+factor*(end[1]-start[1])))
        polygon = output
    return abs(sum(polygon[i][0]*polygon[(i+1) % len(polygon)][1]
                   - polygon[(i+1) % len(polygon)][0]*polygon[i][1]
                   for i in range(len(polygon))))*.5 if len(polygon) >= 3 else 0.0


def uv_overlap_count(mesh, layer):
    triangles = []
    for tri in mesh.loop_triangles:
        points = [tuple(layer.data[i].uv) for i in tri.loops]
        bbox = (min(p[0] for p in points), max(p[0] for p in points),
                min(p[1] for p in points), max(p[1] for p in points))
        triangles.append((points, bbox))
    triangles.sort(key=lambda t: t[1][0])
    count = 0
    for index, (a, ab) in enumerate(triangles):
        for next_index in range(index+1, len(triangles)):
            b, bb = triangles[next_index]
            if bb[0] >= ab[1]-1e-12:
                break
            if bb[3] <= ab[2]+1e-12 or bb[2] >= ab[3]-1e-12:
                continue
            if clipped_area(a, b) > 1e-10:
                count += 1
    return count


def inspect_mesh(obj, label, overlap_channels=()):
    mesh = obj.data
    mesh.calc_loop_triangles()
    transform_error = max(abs(obj.matrix_world[r][c] - (1 if r == c else 0))
                          for r in range(4) for c in range(4))
    check(transform_error < 1e-5, label + ": nonidentity export pivot/transform")
    check(len(mesh.vertices) > 0 and len(mesh.polygons) > 0, label + ": empty geometry")
    check(all(math.isfinite(c) for vert in mesh.vertices for c in vert.co), label + ": nonfinite geometry")
    check(all(p.material_index < len(mesh.materials) for p in mesh.polygons), label + ": invalid material indices")
    slots = [base_name(material.name) if material else None for material in mesh.materials]
    check(all(slots), label + ": empty material slot")
    degenerate = 0
    for tri in mesh.loop_triangles:
        a, b, c = (mesh.vertices[i].co for i in tri.vertices)
        if (b-a).cross(c-a).length < 1e-12:
            degenerate += 1
    check(degenerate == 0, label + ": degenerate geometry triangles: " + str(degenerate))
    check(len(mesh.uv_layers) == 2, label + ": expected UV0 and UV1")
    uv_report = {}
    for index, layer in enumerate(mesh.uv_layers):
        invalid = sum(not all(math.isfinite(c) and -.00001 <= c <= 1.00001 for c in item.uv)
                      for item in layer.data)
        collapsed = sum(abs(cross(*(tuple(layer.data[i].uv) for i in tri.loops))) < 1e-14
                        for tri in mesh.loop_triangles)
        report = {"invalid_coordinate_loops": invalid, "degenerate_triangles": collapsed}
        check(invalid == 0 and collapsed == 0, label + ": invalid/collapsed UVs on " + layer.name)
        if index in overlap_channels:
            overlaps = uv_overlap_count(mesh, layer)
            report["overlapping_triangle_pairs"] = overlaps
            check(overlaps == 0, label + ": overlapping " + layer.name + " triangles: " + str(overlaps))
        uv_report[layer.name] = report
    return {"vertices": len(mesh.vertices), "triangles": len(mesh.loop_triangles),
            "bounds_m": bounds(obj), "material_slots": slots,
            "uv_channels": [layer.name for layer in mesh.uv_layers], "uv_checks": uv_report,
            "identity_transform_error": transform_error, "degenerate_geometry_triangles": degenerate}


def compare(actual, expected, label):
    check(actual["triangles"] == expected["triangles"], label + ": triangle count mismatch")
    check(actual["material_slots"] == expected["material_slots"], label + ": material slot order mismatch")
    error = max(abs(actual["bounds_m"][key][axis] - expected["bounds_m"][key][axis])
                for key in ("min", "max") for axis in range(3))
    check(error < .0001, label + ": scale/orientation/bounds mismatch")
    return error


manifest = json.loads((ROOT / "build_manifest.json").read_text(encoding="utf-8"))
expected = dict(manifest["modules"])
expected["SM_Cafe01_Assembled"] = manifest["assembled"]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Cafe01.blend"))
check(abs(bpy.context.scene.unit_settings.scale_length-1.0) < 1e-6, "Source is not meter scale")
source_checks = {}
for name in manifest["modules"]:
    obj = bpy.data.objects.get(name)
    check(obj is not None and obj.type == 'MESH', "Missing source prototype " + name)
    if obj is None or obj.type != 'MESH':
        continue
    source_checks[name] = inspect_mesh(obj, "Source " + name, overlap_channels=(1,))
    compare(source_checks[name], expected[name], "Source " + name)

roundtrips = {}
checks = {}
for name in expected:
    path = ROOT / "Exports" / (name + ".fbx")
    check(path.exists(), "Missing FBX " + name)
    if not path.exists():
        continue
    root, version = parse_fbx.parse(str(path))
    global_settings = next(e for e in root.elems if e.id == b'GlobalSettings')
    properties = next(e for e in global_settings.elems if e.id == b'Properties70')
    metadata = {e.props[0].decode(): e.props[-1] for e in properties.elems
                if e.id == b'P' and e.props[0] in (b'UnitScaleFactor', b'UpAxis', b'UpAxisSign')}
    check(metadata.get('UpAxis') == 2 and metadata.get('UpAxisSign') == 1, name + ": FBX not Z up")
    check(abs(metadata.get('UnitScaleFactor', 0)-100) < .001, name + ": FBX not meter-based")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    bpy.context.view_layer.update()
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    check(len(objects) == 1, name + ": expected exactly one mesh in FBX")
    entry = {"fbx_version": version, "metadata": metadata, "mesh_count": len(objects)}
    if len(objects) == 1:
        actual = inspect_mesh(objects[0], "FBX " + name, overlap_channels=(1,) if name == 'SM_Cafe01_Assembled' else ())
        entry["mesh"] = actual
        entry["max_bounds_error_m"] = compare(actual, expected[name], "FBX " + name)
        checks[name] = actual
    roundtrips[name] = entry

paths = [ROOT/'Cafe01.blend', ROOT/'build_manifest.json'] + [ROOT/'Exports'/(name+'.fbx') for name in expected]
report = {"blender": bpy.app.version_string, "source_file": "Cafe01.blend",
          "source_module_checks": source_checks, "fbx_roundtrips": roundtrips, "checks": checks,
          "uv_overlap_policy": "Prototype UV1 and assembled exported UV1 tested for triangle overlap; assembled UV0 repetition intentional",
          "validated_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in paths if path.exists()},
          "errors": ERRORS, "passed": not ERRORS}
(ROOT/'validation_blender.json').write_text(json.dumps(report, indent=2), encoding="utf-8")
print('CAFE_VALIDATION ' + json.dumps({"passed": not ERRORS, "modules": len(source_checks),
                                     "fbx_files": len(roundtrips), "errors": ERRORS}), flush=True)
if ERRORS:
    raise RuntimeError('Cafe validation failed; see validation_blender.json')
