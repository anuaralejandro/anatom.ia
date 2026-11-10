"""Read-only Z-Anatomy Blender inventory. Use Blender --disable-autoexec --background file --python script -- output.json."""
import bpy
import json
import collections
import re
import sys
from pathlib import Path

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = Path(args[0]) if args else Path("blend-inventory.json")
objects = list(bpy.data.objects)
meshes = [o for o in objects if o.type == "MESH"]
terms = re.compile(r"pelv|iliac|ilium|ischi|pubi|sacr|coccy|rect|bladd|uter|ovari|vagin|testi|penis|prostat|mamma|breast|clitor|female|femoral|perine|ovary|seminal|cervix|fallopian|uterine", re.I)
matched = []
for o in objects:
    if terms.search(o.name):
        matched.append({
            "name": o.name,
            "type": o.type,
            "vertices": len(o.data.vertices) if o.type == "MESH" else None,
            "polygons": len(o.data.polygons) if o.type == "MESH" else None,
            "collections": [c.name for c in o.users_collection]
        })
grouped = collections.Counter(o.type for o in objects)
colls = collections.Counter(c.name for c in bpy.data.collections)
mesh_vertex_total = sum(len(o.data.vertices) for o in meshes)
mesh_faces_total = sum(len(o.data.polygons) for o in meshes)
sample = []
for o in objects[:80]:
    sample.append({
        "name": o.name,
        "type": o.type,
        "collections": [c.name for c in o.users_collection][:5],
        "custom_properties": {str(k): str(o[k])[:120] for k in o.keys() if not k.startswith("_")} 
    })
top_meshes = sorted(meshes, key=lambda o: len(o.data.polygons), reverse=True)[:25]
data = {
    "blender_version": bpy.app.version_string,
    "source_blend": bpy.data.filepath,
    "scene_names": [s.name for s in bpy.data.scenes],
    "object_count": len(objects),
    "object_types": dict(grouped),
    "mesh_count": len(meshes),
    "mesh_vertices_nominal": mesh_vertex_total,
    "mesh_polygons_nominal": mesh_faces_total,
    "collections_count": len(bpy.data.collections),
    "collections": sorted(colls),
    "materials_count": len(bpy.data.materials),
    "images_count": len(bpy.data.images),
    "texts_count": len(bpy.data.texts),
    "text_names": [t.name for t in bpy.data.texts][:100],
    "matched_anatomy_terms_count": len(matched),
    "matched_anatomy_terms": matched[:500],
    "object_names_sample": sample,
    "largest_meshes": [{"name": o.name,"faces":len(o.data.polygons),"verts":len(o.data.vertices)} for o in top_meshes]
}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print("INVENTORY_SUCCESS="+str(out))
print("OBJECTS="+str(len(objects))+" MESHES="+str(len(meshes))+" FACES="+str(mesh_faces_total)+" MATCHES="+str(len(matched)))
print("COLLECTIONS="+str(len(bpy.data.collections))+" MATERIALS="+str(len(bpy.data.materials)))
