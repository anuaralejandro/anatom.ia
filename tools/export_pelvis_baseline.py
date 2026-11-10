"""Export disposable uncompressed baseline of the 26 candidate structures.

Run with Blender --background --disable-autoexec Startup.blend --python ... .
NEVER saves or edits original source .blend. Converts evaluated MESH/CURVE to independent
temporary Blender meshes, adds stable atlas ID in glTF node extras, exports selected only.
No LOD, meshopt, commercial-license approval or anatomical geometry validation yet.
"""
import bpy,json,hashlib,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
fixture=json.loads((ROOT/"reports"/"pelvis-fixture-candidate.json").read_text(encoding="utf-8"))
crosswalk=json.loads((ROOT/"reports"/"pelvis-ta2-crosswalk.json").read_text(encoding="utf-8"))
by_source={x["source_object"]:x for x in crosswalk["objects"]}
target=ROOT/"reports"/"experimental"
target.mkdir(parents=True,exist_ok=True)
out=target/"pelvis-baseline-uncompressed.glb"
dg=bpy.context.evaluated_depsgraph_get()
bpy.ops.object.select_all(action="DESELECT")
duplicates=[]
records=[]
t0=time.perf_counter()
for item in fixture["objects"]:
    source=bpy.data.objects.get(item["source_object"])
    term=by_source.get(item["source_object"])
    if source is None or term is None or term["status"]!="unique_exact":raise RuntimeError("Missing/ambiguous "+item["source_object"])
    ev=source.evaluated_get(dg)
    new_mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
    if not new_mesh or not len(new_mesh.polygons):raise RuntimeError("Evaluated geometry empty "+source.name)
    # The evaluated mesh may not retain material slots: explicitly ensure they exist.
    if len(new_mesh.materials)==0:
        for mat in source.data.materials:
            if mat: new_mesh.materials.append(mat)
    obj=bpy.data.objects.new("atlas__"+source.name,new_mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world=source.matrix_world.copy()
    obj["atlas_id"]=term["anatomy_id_proposal"]
    obj["ta2_id"]=term["ta2_id"]
    obj["source_object"]=source.name
    obj["patient_side"]=term["laterality_suffix"] or "midline_or_unspecified"
    obj["source_kind"]=source.type
    obj["license_state"]="review_required"
    duplicates.append(obj)
    records.append({
      "source":source.name,"atlas_id":term["anatomy_id_proposal"],"type":source.type,
      "evaluated_vertices":len(new_mesh.vertices),"evaluated_polygons":len(new_mesh.polygons),
      "materials":len(new_mesh.materials)
    })
# Must explicitly unselect everything except temp duplicates.
bpy.ops.object.select_all(action="DESELECT")
for obj in duplicates:obj.select_set(True)
bpy.context.view_layer.objects.active=duplicates[0]
t1=time.perf_counter()
result=bpy.ops.export_scene.gltf(
    filepath=str(out),export_format="GLB",check_existing=False,
    use_selection=True,export_extras=True,export_yup=True,export_apply=False,
    export_animations=False,export_cameras=False,export_lights=False,
    export_texcoords=False,export_normals=True,export_materials="EXPORT",
    export_draco_mesh_compression_enable=False,export_tangents=False)
if "FINISHED" not in result or not out.exists(): raise RuntimeError("GLB exporter did not finish")
size=out.stat().st_size
sha=hashlib.sha256(out.read_bytes()).hexdigest()
t2=time.perf_counter()
report={
    "status":"experimental_uncompressed_source_not_licensed_for_distribution",
    "source_commit":fixture["source_commit"],"source_blend":fixture["source_blend"],
    "object_count":len(records),"mesh_count":sum(x["type"]=="MESH" for x in records),
    "curve_count":sum(x["type"]=="CURVE" for x in records),
    "total_evaluated_polygons":sum(x["evaluated_polygons"] for x in records),
    "total_evaluated_vertices":sum(x["evaluated_vertices"] for x in records),
    "output":str(out),"output_bytes":size,"sha256":sha,
    "prepare_seconds":round(t1-t0,3),"export_seconds":round(t2-t1,3),
    "contains_lods":False,"contains_meshopt":False,
    "glb_coordinate_target":"glTF +Y up; original Blender +Z up; +X patient left; raw -Y anterior maps to glTF +Z",
    "records":records
}
path=ROOT/"reports"/"pelvis-baseline-export-report.json"
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("EXPORTED",out,"BYTES",size,"OBJECTS",len(records),"POLYGONS",report["total_evaluated_polygons"],"SHA256",sha,flush=True)
print("TIMES",report["prepare_seconds"],report["export_seconds"],flush=True)
