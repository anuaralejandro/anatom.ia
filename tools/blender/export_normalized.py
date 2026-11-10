"""
tools/blender/export_normalized.py
Pipeline de extracción, evaluación y normalización anatómica de pelvis para anatom.ia (M03).
Ejecutar exclusivamente en modo background:
  blender.exe --background --disable-autoexec <source.blend> --python tools/blender/export_normalized.py -- [opciones]
"""
import bpy
import json
import hashlib
import os
import struct
import sys
import time
from pathlib import Path

def parse_args():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    
    fixture_path = "reports/pelvis-fixture-candidate.json"
    crosswalk_path = "reports/pelvis-ta2-crosswalk.json"
    out_glb = "build/atlas/staging/pelvis-normalized.glb"
    out_report = "build/atlas/staging/normalization-report.json"
    
    i = 0
    while i < len(args):
        if args[i] == "--fixture" and i + 1 < len(args):
            fixture_path = args[i + 1]
            i += 2
        elif args[i] == "--crosswalk" and i + 1 < len(args):
            crosswalk_path = args[i + 1]
            i += 2
        elif args[i] == "--out" and i + 1 < len(args):
            out_glb = args[i + 1]
            i += 2
        elif args[i] == "--report" and i + 1 < len(args):
            out_report = args[i + 1]
            i += 2
        else:
            i += 1
            
    return Path(fixture_path), Path(crosswalk_path), Path(out_glb), Path(out_report)

def apply_pbr_core_in_place(glb_path):
    """
    Ajusta materiales a glTF PBR Core estándar:
    - metallicFactor = 0.0
    - roughnessFactor determinista por tipo de tejido
    - elimina KHR_materials_specular y KHR_materials_ior
    - conserva colores base, alphaMode, doubleSided y el buffer binario idéntico.
    """
    raw = glb_path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total != len(raw):
        raise ValueError("Archivo GLB inválido")
        
    cursor = 12
    chunks = []
    while cursor < len(raw):
        chunk_len, chunk_type = struct.unpack_from("<II", raw, cursor)
        cursor += 8
        chunks.append((chunk_type, raw[cursor:cursor + chunk_len]))
        cursor += chunk_len
        
    doc = json.loads(chunks[0][1].decode("utf-8").rstrip(" \x00"))
    
    rough_table = {
        "bone": 0.73,
        "cartilage": 0.57,
        "organ": 0.64,
        "gland": 0.58,
        "mucosa": 0.53,
        "ligament": 0.77,
        "muscle": 0.73,
        "artery": 0.57,
        "vein": 0.61,
        "nerve": 0.70
    }
    
    for m in doc.get("materials", []):
        name = m.get("name", "").lower()
        cat = next((k for k in rough_table if k in name), "organ")
        pbr = m.setdefault("pbrMetallicRoughness", {})
        pbr["metallicFactor"] = 0.0
        pbr["roughnessFactor"] = rough_table[cat]
        
        if "extensions" in m:
            m["extensions"].pop("KHR_materials_specular", None)
            m["extensions"].pop("KHR_materials_ior", None)
            if not m["extensions"]:
                m.pop("extensions", None)
                
    doc.pop("extensionsUsed", None)
    doc.pop("extensionsRequired", None)
    
    new_json_bytes = json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    new_json_bytes += b" " * ((-len(new_json_bytes)) % 4)
    
    out_chunks = [(0x4E4F534A, new_json_bytes)] + chunks[1:]
    total_len = 12 + sum(8 + len(buf) for _, buf in out_chunks)
    
    out = bytearray(struct.pack("<4sII", b"glTF", 2, total_len))
    for c_type, buf in out_chunks:
        out.extend(struct.pack("<II", len(buf), c_type))
        out.extend(buf)
        
    glb_path.write_bytes(out)
    return len(doc.get("nodes", [])), len(doc.get("materials", []))

def main():
    t0 = time.perf_counter()
    fixture_path, crosswalk_path, out_glb, out_report = parse_args()
    
    out_glb.parent.mkdir(parents=True, exist_ok=True)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    
    fix_data = json.loads(fixture_path.read_text(encoding="utf-8"))
    cw_data = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    
    by_source = {x["source_object"]: x for x in cw_data["objects"]}
    
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.ops.object.select_all(action="DESELECT")
    
    duplicates = []
    records = []
    
    for item in fix_data["objects"]:
        name = item["source_object"]
        source = bpy.data.objects.get(name)
        term = by_source.get(name)
        
        if not source or not term:
            raise RuntimeError(f"Objeto no encontrado en blend o crosswalk: {name}")
            
        ev = source.evaluated_get(dg)
        new_mesh = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        
        if not new_mesh or len(new_mesh.polygons) == 0:
            raise RuntimeError(f"Geometría evaluada vacía para: {name}")
            
        if len(new_mesh.materials) == 0 and source.data and hasattr(source.data, "materials"):
            for mat in source.data.materials:
                if mat:
                    new_mesh.materials.append(mat)
                    
        obj = bpy.data.objects.new("atlas__" + source.name, new_mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world = source.matrix_world.copy()
        
        obj["atlas_id"] = term["anatomy_id_proposal"]
        obj["ta2_id"] = term["ta2_id"]
        obj["source_object"] = source.name
        obj["patient_side"] = term["laterality_suffix"] or "unpaired_or_unspecified"
        obj["source_kind"] = source.type
        obj["license_state"] = "review_required"
        
        duplicates.append(obj)
        records.append({
            "source_object": source.name,
            "atlas_id": term["anatomy_id_proposal"],
            "ta2_id": term["ta2_id"],
            "type": source.type,
            "evaluated_vertices": len(new_mesh.vertices),
            "evaluated_polygons": len(new_mesh.polygons),
            "materials_count": len(new_mesh.materials),
            "patient_side": term["laterality_suffix"] or "unpaired_or_unspecified"
        })
        
    t_eval = time.perf_counter() - t0
    
    # Exportar solo duplicados temporales
    bpy.ops.object.select_all(action="DESELECT")
    for obj in duplicates:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = duplicates[0]
    
    t_export_start = time.perf_counter()
    export_res = bpy.ops.export_scene.gltf(
        filepath=str(out_glb),
        export_format="GLB",
        check_existing=False,
        use_selection=True,
        export_extras=True,
        export_yup=True,
        export_apply=False,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_texcoords=False,
        export_normals=True,
        export_materials="EXPORT",
        export_draco_mesh_compression_enable=False,
        export_tangents=False
    )
    t_export = time.perf_counter() - t_export_start
    
    # Limpieza de duplicados temporales de la memoria
    for obj in duplicates:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        
    if "FINISHED" not in export_res or not out_glb.exists():
        raise RuntimeError("Fallo en exportador glTF de Blender")
        
    # Normalizar materiales a Core PBR
    node_count, mat_count = apply_pbr_core_in_place(out_glb)
    
    file_bytes = out_glb.stat().st_size
    file_sha = hashlib.sha256(out_glb.read_bytes()).hexdigest()
    
    report = {
        "status": "PASS",
        "output_glb": str(out_glb),
        "output_bytes": file_bytes,
        "output_sha256": file_sha,
        "object_count": len(records),
        "mesh_objects": sum(1 for x in records if x["type"] == "MESH"),
        "curve_objects": sum(1 for x in records if x["type"] == "CURVE"),
        "total_evaluated_polygons": sum(x["evaluated_polygons"] for x in records),
        "total_evaluated_vertices": sum(x["evaluated_vertices"] for x in records),
        "materials_count": mat_count,
        "evaluation_seconds": round(t_eval, 3),
        "export_seconds": round(t_export, 3),
        "records": records
    }
    
    out_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[EXPORT_NORMALIZED] OK -> {out_glb} ({file_bytes} bytes, {len(records)} structures, SHA={file_sha})", flush=True)

if __name__ == "__main__":
    main()
