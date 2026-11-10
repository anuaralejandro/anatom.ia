"""Read-only spatial and conversion audit of the 26 pelvis fixture objects.

Usage: blender --background --disable-autoexec Startup.blend --python inspect_fixture_spatial.py
Does NOT modify or save the original .blend. Evaluated CURVE->MESH occurs in memory only.
"""
import bpy,json,math,sys,statistics
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
fixture=json.loads((ROOT/"reports"/"pelvis-fixture-candidate.json").read_text(encoding="utf-8"))
dg=bpy.context.evaluated_depsgraph_get()
items=[]
for entry in fixture["objects"]:
    name=entry["source_object"]
    obj=bpy.data.objects.get(name)
    if not obj: raise RuntimeError("Missing Blender object: "+name)
    ev=obj.evaluated_get(dg)
    transient=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
    points=[]
    if transient is not None:
        for v in transient.vertices: points.append(ev.matrix_world @ v.co)
    if not points:
        for corner in obj.bound_box: points.append(obj.matrix_world @ Vector(corner))
    mn=[min(p[i] for p in points) for i in range(3)]
    mx=[max(p[i] for p in points) for i in range(3)]
    center=[round((mn[i]+mx[i])/2,6) for i in range(3)]
    size=[round(mx[i]-mn[i],6) for i in range(3)]
    data={
        "source_object":name,"type":obj.type,
        "location":[round(v,7) for v in obj.location],
        "scale":[round(v,7) for v in obj.scale],
        "rotation_euler":[round(v,7) for v in obj.rotation_euler],
        "matrix_world_determinant":round(obj.matrix_world.determinant(),7),
        "bounds_min":[round(v,6) for v in mn],
        "bounds_max":[round(v,6) for v in mx],
        "bounds_center":center,"dimensions_source_units":size,
        "source_mesh_verts":len(obj.data.vertices) if obj.type=="MESH" else None,
        "source_mesh_polygons":len(obj.data.polygons) if obj.type=="MESH" else None,
        "evaluated_mesh_verts":len(transient.vertices) if transient else None,
        "evaluated_mesh_polygons":len(transient.polygons) if transient else None,
        "modifiers":[{"name":m.name,"type":m.type} for m in obj.modifiers],
        "materials":[m.name for m in obj.data.materials if m] if obj.data else [],
        "collections":[c.name for c in obj.users_collection],
    }
    if obj.type=="CURVE":
        cu=obj.data
        data["curve_details"]={
           "dimensions":cu.dimensions,"bevel_depth":float(cu.bevel_depth),
           "bevel_resolution":int(cu.bevel_resolution),"resolution_u":int(cu.resolution_u),
           "bevel_mode":cu.bevel_mode,
           "splines":len(cu.splines),
           "spline_types":[sp.type for sp in cu.splines],
           "control_points":sum(len(sp.bezier_points) if sp.type=="BEZIER" else len(sp.points) for sp in cu.splines),
           "fill_mode":cu.fill_mode
        }
    items.append(data)
    if transient is not None: ev.to_mesh_clear()
source_unit=bpy.context.scene.unit_settings
female=[]
for coll in bpy.data.collections:
    if "female" in coll.name.casefold():
        ob=list(coll.objects)
        nested=list(coll.all_objects)
        female.append({"collection":coll.name,"direct_objects":len(ob),"all_objects":len(nested),"mesh_with_faces":sum(x.type=="MESH" and len(x.data.polygons)>0 for x in nested)})
result={
    "source_file":bpy.data.filepath,"scene_unit_system":source_unit.system,
    "scene_unit_scale":float(source_unit.scale_length),
    "scene_length_unit":source_unit.length_unit,
    "file_version":bpy.app.version_string,
    "items":items,
    "female_collections":female,
    "methodology":"evaluated to_mesh() in memory, world vertex coordinates; dimensions in raw Blender coordinate units, not proven meters; no source modifications",
}
out=ROOT/"reports"/"pelvis-spatial-curve-audit.json"
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
curves=[x for x in items if x["type"]=="CURVE"]
print("AUDIT_SAVED",str(out))
print("UNIT",source_unit.system,source_unit.scale_length,source_unit.length_unit)
print("CURVE_EVAL",len(curves),"polys_total",sum((x["evaluated_mesh_polygons"] or 0) for x in curves))
for x in curves: print("CURVE",x["source_object"],"faces",x["evaluated_mesh_polygons"],"bevel",x["curve_details"]["bevel_depth"],"dimensions",x["dimensions_source_units"],"center",x["bounds_center"])
for x in items:
    if x["source_object"] in ("Sacrum","Coccyx","Urinary bladder","Testis.l","Testis.r","Prostate","Glans penis","Internal iliac artery.l","Internal iliac artery.r"):
        print("ANCHOR",x["source_object"],"center",x["bounds_center"],"size",x["dimensions_source_units"])
print("FEMALE_COLLECTIONS",female)
