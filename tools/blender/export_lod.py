"""
tools/blender/export_lod.py
Generación de paquetes LOD piloto para pelvis en anatom.ia (M03).
Aplica simplificación controlada exclusivamente a Sacro y Vejiga urinaria,
preservando intactas las 24 estructuras restantes.
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
    lod_level = 1
    out_glb = "build/atlas/staging/pelvis-lod1.glb"
    out_report = "build/atlas/staging/lod1-report.json"
    
    i = 0
    while i < len(args):
        if args[i] == "--fixture" and i + 1 < len(args):
            fixture_path = args[i + 1]
            i += 2
        elif args[i] == "--crosswalk" and i + 1 < len(args):
            crosswalk_path = args[i + 1]
            i += 2
        elif args[i] == "--lod" and i + 1 < len(args):
            lod_level = int(args[i + 1])
            i += 2
        elif args[i] == "--out" and i + 1 < len(args):
            out_glb = args[i + 1]
            i += 2
        elif args[i] == "--report" and i + 1 < len(args):
            out_report = args[i + 1]
            i += 2
        else:
            i += 1
            
    return Path(fixture_path), Path(crosswalk_path), lod_level, Path(out_glb), Path(out_report)

def apply_pbr_core_in_place(glb_path):
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

def main():
    t0 = time.perf_counter()
    fixture_path, crosswalk_path, lod_level, out_glb, out_report = parse_args()
    
    out_glb.parent.mkdir(parents=True, exist_ok=True)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    
    fix_data = json.loads(fixture_path.read_text(encoding="utf-8"))
    cw_data = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    by_source = {x["source_object"]: x for x in cw_data["objects"]}
    
    # Ratios de simplificación conservadores según pelvis-lod-policy-proposal.json
    # LOD1: Sacro ~0.65, Vejiga ~0.75, resto 1.0 (reuse_base)
    # LOD2: Sacro ~0.35, Vejiga reuse_lod1 (0.75), resto 1.0 (reuse_base)
    ratios = {}
    if lod_level == 1:
        ratios = {"Sacrum": 0.65, "Urinary bladder": 0.75}
    elif lod_level == 2:
        ratios = {"Sacrum": 0.35, "Urinary bladder": 0.75}
        
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.ops.object.select_all(action="DESELECT")
    
    duplicates = []
    records = []
    
    for item in fix_data["objects"]:
        name = item["source_object"]
        source = bpy.data.objects.get(name)
        term = by_source.get(name)
        
        if not source or not term:
            raise RuntimeError(f"Objeto no encontrado: {name}")
            
        ev = source.evaluated_get(dg)
        new_mesh = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        
        # Aplicar decimate si la estructura es candidata a este nivel de LOD
        target_ratio = ratios.get(name, 1.0)
        decimated = False
        
        temp_obj = bpy.data.objects.new("atlas_lod__" + source.name, new_mesh)
        bpy.context.scene.collection.objects.link(temp_obj)
        temp_obj.matrix_world = source.matrix_world.copy()
        
        if len(new_mesh.materials) == 0 and source.data and hasattr(source.data, "materials"):
            for mat in source.data.materials:
                if mat:
                    new_mesh.materials.append(mat)
                    
        if target_ratio < 1.0 and source.type == "MESH":
            mod = temp_obj.modifiers.new("Decimate_LOD", "DECIMATE")
            mod.ratio = target_ratio
            mod.use_collapse_triangulate = True
            
            # Evaluar el objeto con el modifier aplicado
            dg_temp = bpy.context.evaluated_depsgraph_get()
            ev_dec = temp_obj.evaluated_get(dg_temp)
            dec_mesh = bpy.data.meshes.new_from_object(ev_dec, preserve_all_data_layers=True, depsgraph=dg_temp)
            
            # Reemplazar la malla del objeto temporal
            bpy.data.objects.remove(temp_obj, do_unlink=True)
            bpy.data.meshes.remove(new_mesh)
            
            temp_obj = bpy.data.objects.new("atlas_lod__" + source.name, dec_mesh)
            bpy.context.scene.collection.objects.link(temp_obj)
            temp_obj.matrix_world = source.matrix_world.copy()
            new_mesh = dec_mesh
            decimated = True
            
        temp_obj["atlas_id"] = term["anatomy_id_proposal"]
        temp_obj["ta2_id"] = term["ta2_id"]
        temp_obj["source_object"] = source.name
        temp_obj["patient_side"] = term["laterality_suffix"] or "unpaired_or_unspecified"
        temp_obj["source_kind"] = source.type
        temp_obj["license_state"] = "review_required"
        temp_obj["lod_level"] = lod_level
        temp_obj["lod_ratio"] = target_ratio
        
        duplicates.append(temp_obj)
        records.append({
            "source_object": source.name,
            "atlas_id": term["anatomy_id_proposal"],
            "ta2_id": term["ta2_id"],
            "type": source.type,
            "lod_level": lod_level,
            "target_ratio": target_ratio,
            "was_decimated": decimated,
            "evaluated_vertices": len(new_mesh.vertices),
            "evaluated_polygons": len(new_mesh.polygons)
        })
        
    # Exportar GLB
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
    
    # Limpieza
    for obj in duplicates:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        
    if "FINISHED" not in export_res or not out_glb.exists():
        raise RuntimeError(f"Fallo en exportador glTF para LOD{lod_level}")
        
    apply_pbr_core_in_place(out_glb)
    
    file_bytes = out_glb.stat().st_size
    file_sha = hashlib.sha256(out_glb.read_bytes()).hexdigest()
    
    report = {
        "status": "PASS",
        "lod_level": lod_level,
        "output_glb": str(out_glb),
        "output_bytes": file_bytes,
        "output_sha256": file_sha,
        "structures_count": len(records),
        "decimated_structures_count": sum(1 for x in records if x["was_decimated"]),
        "total_polygons": sum(x["evaluated_polygons"] for x in records),
        "total_vertices": sum(x["evaluated_vertices"] for x in records),
        "export_seconds": round(t_export, 3),
        "records": records
    }
    
    out_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[EXPORT_LOD{lod_level}] OK -> {out_glb} ({file_bytes} bytes, polygons={report['total_polygons']}, SHA={file_sha})", flush=True)

if __name__ == "__main__":
    main()
