"""
tools/blender/inspect_blend.py
Inspector de proyectos Blender para anatom.ia (M03).
Ejecución en modo background seguro:
  blender.exe --background --disable-autoexec <source.blend> --python tools/blender/inspect_blend.py -- [opciones]
"""
import bpy
import json
import os
import sys
import time
from pathlib import Path
from mathutils import Vector

def parse_args():
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
    else:
        args = []
    
    out_path = "reports/experimental/blend-inspection.json"
    fixture_path = None
    
    i = 0
    while i < len(args):
        if args[i] == "--out" and i + 1 < len(args):
            out_path = args[i + 1]
            i += 2
        elif args[i] == "--fixture" and i + 1 < len(args):
            fixture_path = args[i + 1]
            i += 2
        else:
            i += 1
            
    return Path(out_path), Path(fixture_path) if fixture_path else None

def main():
    t0 = time.perf_counter()
    out_path, fixture_path = parse_args()
    
    objects = list(bpy.data.objects)
    type_counts = {}
    for o in objects:
        type_counts[o.type] = type_counts.get(o.type, 0) + 1
        
    empty_markers = []
    font_labels = []
    for o in objects:
        if o.type == "MESH" and len(o.data.polygons) == 0:
            empty_markers.append(o.name)
        elif o.type == "FONT":
            font_labels.append(o.name)
            
    fixture_results = []
    fixture_missing = []
    
    dg = bpy.context.evaluated_depsgraph_get()
    
    if fixture_path and fixture_path.exists():
        fix_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        req_objs = fix_data.get("objects", [])
        
        for item in req_objs:
            name = item.get("source_object")
            obj = bpy.data.objects.get(name)
            if not obj:
                fixture_missing.append(name)
                continue
                
            ev = obj.evaluated_get(dg)
            transient = ev.to_mesh(preserve_all_data_layers=False, depsgraph=dg)
            
            points = []
            if transient:
                for v in transient.vertices:
                    points.append(ev.matrix_world @ v.co)
            if not points:
                for corner in obj.bound_box:
                    points.append(obj.matrix_world @ Vector(corner))
                    
            mn = [min(p[i] for p in points) for i in range(3)] if points else [0, 0, 0]
            mx = [max(p[i] for p in points) for i in range(3)] if points else [0, 0, 0]
            center = [round((mn[i] + mx[i]) / 2.0, 6) for i in range(3)]
            dims = [round(mx[i] - mn[i], 6) for i in range(3)]
            
            evaluated_verts = len(transient.vertices) if transient else 0
            evaluated_polys = len(transient.polygons) if transient else 0
            
            obj_info = {
                "name": name,
                "type": obj.type,
                "evaluated_vertices": evaluated_verts,
                "evaluated_polygons": evaluated_polys,
                "materials": [m.name for m in obj.data.materials if m] if obj.data else [],
                "bounds_min": [round(v, 6) for v in mn],
                "bounds_max": [round(v, 6) for v in mx],
                "bounds_center": center,
                "dimensions": dims,
                "modifiers": [{"name": m.name, "type": m.type} for m in obj.modifiers]
            }
            
            if obj.type == "CURVE" and obj.data:
                cu = obj.data
                obj_info["curve_details"] = {
                    "bevel_depth": float(cu.bevel_depth),
                    "bevel_resolution": int(cu.bevel_resolution),
                    "resolution_u": int(cu.resolution_u),
                    "splines": len(cu.splines)
                }
                
            fixture_results.append(obj_info)
            if transient:
                ev.to_mesh_clear()
                
    elapsed = time.perf_counter() - t0
    
    report = {
        "status": "PASS" if not fixture_missing else "FAIL",
        "blender_version": bpy.app.version_string,
        "source_blend": bpy.data.filepath,
        "total_objects": len(objects),
        "object_types": type_counts,
        "collections_count": len(bpy.data.collections),
        "materials_count": len(bpy.data.materials),
        "empty_mesh_markers_count": len(empty_markers),
        "empty_mesh_markers_sample": empty_markers[:20],
        "font_labels_count": len(font_labels),
        "font_labels_sample": font_labels[:20],
        "fixture_inspected_count": len(fixture_results),
        "fixture_missing_count": len(fixture_missing),
        "fixture_missing": fixture_missing,
        "fixture_structures": fixture_results,
        "execution_seconds": round(elapsed, 3)
    }
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[INSPECT_BLEND] OK -> {out_path} ({len(fixture_results)} fixture objects inspected in {elapsed:.2f}s)", flush=True)

if __name__ == "__main__":
    main()
