#!/usr/bin/env python3
"""
tools/calculate_lod_metrics.py
Evaluador de métricas de calidad geométrica, silueta y reducción para LODs (M03).
"""
import json
import math
import struct
import sys
from pathlib import Path

def parse_glb_nodes_and_bounds(glb_path):
    raw = Path(glb_path).read_bytes()
    magic, ver, total = struct.unpack_from("<4sII", raw, 0)
    assert magic == b"glTF" and ver == 2
    cursor = 12
    chunks = []
    while cursor < len(raw):
        chunk_len, chunk_type = struct.unpack_from("<II", raw, cursor)
        cursor += 8
        chunks.append((chunk_type, raw[cursor:cursor + chunk_len]))
        cursor += chunk_len
        
    doc = json.loads(chunks[0][1].decode("utf-8").rstrip(" \x00"))
    bin_data = chunks[1][1] if len(chunks) > 1 else b""
    
    accessors = doc.get("accessors", [])
    buffer_views = doc.get("bufferViews", [])
    meshes = doc.get("meshes", [])
    nodes = doc.get("nodes", [])
    
    structures = {}
    
    for n in nodes:
        aid = n.get("extras", {}).get("atlas_id")
        m_idx = n.get("mesh")
        if not aid or m_idx is None or m_idx >= len(meshes):
            continue
            
        mesh = meshes[m_idx]
        total_tris = 0
        all_positions = []
        
        for prim in mesh.get("primitives", []):
            idx_acc = prim.get("indices")
            if idx_acc is not None and idx_acc < len(accessors):
                acc = accessors[idx_acc]
                count = acc.get("count", 0)
                total_tris += count // 3
                
            pos_acc = prim.get("attributes", {}).get("POSITION")
            if pos_acc is not None and pos_acc < len(accessors):
                acc = accessors[pos_acc]
                # min and max are in accessor
                if "min" in acc and "max" in acc:
                    all_positions.append((acc["min"], acc["max"]))
                    
        # Compute combined bounds
        if all_positions:
            b_min = [min(p[0][i] for p in all_positions) for i in range(3)]
            b_max = [max(p[1][i] for p in all_positions) for i in range(3)]
        else:
            b_min = [0, 0, 0]
            b_max = [0, 0, 0]
            
        b_center = [(b_min[i] + b_max[i]) * 0.5 for i in range(3)]
        b_extents = [b_max[i] - b_min[i] for i in range(3)]
        
        structures[aid] = {
            "name": n.get("name"),
            "anatomy_id": aid,
            "mesh_index": m_idx,
            "primitives_count": len(mesh.get("primitives", [])),
            "triangles": total_tris,
            "bounds_min": b_min,
            "bounds_max": b_max,
            "bounds_center": b_center,
            "bounds_extents": b_extents
        }
        
    return doc, structures

def project_to_screen(point, camera_preset, viewport_w=1280, viewport_h=720):
    # Proyección simple con presets 0, 1, 2
    # Preset 0: Anterior-Superior (azimuth 0, pitch ~14 deg)
    # Preset 1: Oblicuo (azimuth 45 deg, pitch ~14 deg)
    # Preset 2: Inferior (azimuth 0, pitch ~-28 deg)
    yaw, pitch, dist = camera_preset
    
    # Target central aproximado de pelvis
    target = [0.0, 0.88, 0.0]
    
    cos_p = math.cos(pitch)
    sin_p = math.sin(pitch)
    sin_y = math.sin(yaw)
    cos_y = math.cos(yaw)
    
    eye = [
        target[0] + dist * cos_p * sin_y,
        target[1] + dist * sin_p,
        target[2] + dist * cos_p * cos_y
    ]
    
    # Vector relativo a target
    fwd = [target[i] - eye[i] for i in range(3)]
    fwd_len = math.hypot(fwd[0], fwd[1], fwd[2])
    fwd = [v / fwd_len for v in fwd]
    
    up = [0.0, 1.0, 0.0]
    right = [
        fwd[1] * up[2] - fwd[2] * up[1],
        fwd[2] * up[0] - fwd[0] * up[2],
        fwd[0] * up[1] - fwd[1] * up[0]
    ]
    r_len = math.hypot(right[0], right[1], right[2])
    right = [v / r_len for v in right]
    
    up = [
        right[1] * fwd[2] - right[2] * fwd[1],
        right[2] * fwd[0] - right[0] * fwd[2],
        right[0] * fwd[1] - right[1] * fwd[0]
    ]
    
    # Punto en espacio de vista
    p_rel = [point[i] - eye[i] for i in range(3)]
    view_x = sum(p_rel[i] * right[i] for i in range(3))
    view_y = sum(p_rel[i] * up[i] for i in range(3))
    view_z = sum(p_rel[i] * fwd[i] for i in range(3))
    
    if view_z <= 0.01:
        return 0, 0
        
    fovy = math.pi / 4.0
    tan_half_fovy = math.tan(fovy * 0.5)
    aspect = viewport_w / viewport_h
    
    proj_x = view_x / (view_z * tan_half_fovy * aspect)
    proj_y = view_y / (view_z * tan_half_fovy)
    
    screen_x = (proj_x * 0.5 + 0.5) * viewport_w
    screen_y = (1.0 - (proj_y * 0.5 + 0.5)) * viewport_h
    return screen_x, screen_y

def evaluate_quality(base_glb, lod_glb, lod_name="lod1"):
    base_doc, base_structs = parse_glb_nodes_and_bounds(base_glb)
    lod_doc, lod_structs = parse_glb_nodes_and_bounds(lod_glb)
    
    base_bytes = Path(base_glb).stat().st_size
    lod_bytes = Path(lod_glb).stat().st_size
    
    base_total_tris = sum(s["triangles"] for s in base_structs.values())
    lod_total_tris = sum(s["triangles"] for s in lod_structs.values())
    
    presets = [
        (0.0, 0.25, 0.8),    # Preset 0: Anterior-Superior
        (0.785, 0.25, 0.8),  # Preset 1: Oblicuo
        (0.0, -0.50, 0.8)    # Preset 2: Inferior
    ]
    
    evaluations = {}
    pixel_deviations = []
    
    for aid, b_info in base_structs.items():
        l_info = lod_structs.get(aid)
        if not l_info:
            evaluations[aid] = {"status": "MISSING_STRUCTURE"}
            continue
            
        b_tris = b_info["triangles"]
        l_tris = l_info["triangles"]
        tri_ratio = round(l_tris / b_tris, 4) if b_tris > 0 else 1.0
        
        # Center shift
        shift = math.hypot(
            b_info["bounds_center"][0] - l_info["bounds_center"][0],
            b_info["bounds_center"][1] - l_info["bounds_center"][1],
            b_info["bounds_center"][2] - l_info["bounds_center"][2]
        )
        
        # Silhouette bounds deviation across presets
        max_px_dev = 0.0
        for p_idx, preset in enumerate(presets):
            # Project min and max corners
            sx1_b, sy1_b = project_to_screen(b_info["bounds_min"], preset)
            sx2_b, sy2_b = project_to_screen(b_info["bounds_max"], preset)
            
            sx1_l, sy1_l = project_to_screen(l_info["bounds_min"], preset)
            sx2_l, sy2_l = project_to_screen(l_info["bounds_max"], preset)
            
            dev1 = math.hypot(sx1_b - sx1_l, sy1_b - sy1_l)
            dev2 = math.hypot(sx2_b - sx2_l, sy2_b - sy2_l)
            max_px_dev = max(max_px_dev, dev1, dev2)
            
        pixel_deviations.append(max_px_dev)
        
        evaluations[aid] = {
            "name": b_info["name"],
            "base_triangles": b_tris,
            "lod_triangles": l_tris,
            "triangle_ratio": tri_ratio,
            "center_shift_meters": round(shift, 6),
            "max_screen_pixel_deviation": round(max_px_dev, 2),
            "status": "PASS" if max_px_dev <= 2.0 and shift < 0.002 else "WARNING"
        }
        
    pixel_deviations.sort()
    p95_idx = int(math.ceil(0.95 * len(pixel_deviations))) - 1
    p95_dev = pixel_deviations[p95_idx] if pixel_deviations else 0.0
    
    return {
        "lod_name": lod_name,
        "base_file": str(base_glb),
        "lod_file": str(lod_glb),
        "base_bytes": base_bytes,
        "lod_bytes": lod_bytes,
        "byte_reduction_percent": round((1.0 - lod_bytes / base_bytes) * 100.0, 2),
        "base_total_triangles": base_total_tris,
        "lod_total_triangles": lod_total_tris,
        "triangle_reduction_percent": round((1.0 - lod_total_tris / base_total_tris) * 100.0, 2),
        # This is a bounding-box corner proxy, NOT rasterized triangle silhouettes.
        "p95_silhouette_pixel_deviation_720p": None,
        "bounds_corner_proxy_p95_px": round(p95_dev, 2),
        "quality_gate_p95_target": 2.0,
        "quality_verdict": "NOT_EVALUATED_REQUIRES_TRUE_SILHOUETTE",
        "structures": evaluations
    }

def main():
    if len(sys.argv) < 3:
        print("Uso: calculate_lod_metrics.py <base_glb> <lod1_glb> [lod2_glb] [--out <report.json>]")
        sys.exit(1)
        
    base_glb = sys.argv[1]
    lod1_glb = sys.argv[2]
    lod2_glb = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
    
    out_path = Path("reports/experimental/quality-report.json")
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])
        
    lod1_eval = evaluate_quality(base_glb, lod1_glb, "lod1")
    report = {
        "status": "NOT_EVALUATED_BOUNDING_BOX_PROXY_ONLY",
        "lod1": lod1_eval
    }
    
    if lod2_glb and Path(lod2_glb).exists():
        lod2_eval = evaluate_quality(base_glb, lod2_glb, "lod2")
        report["lod2"] = lod2_eval
        
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[QUALITY_PROXY_ONLY] {report['status']} -> {out_path} (LOD1 reduction: {lod1_eval['triangle_reduction_percent']}%, bounds-proxy p95: {lod1_eval['bounds_corner_proxy_p95_px']}px; no PASS allowed)")

if __name__ == "__main__":
    main()
