#!/usr/bin/env python3
"""Read-only graphics profile audit of experimental pelvis GLB."""
import json, struct, collections
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
path=ROOT/"reports"/"experimental"/"pelvis-baseline-uncompressed.glb"
with path.open("rb") as f:
    magic,version,size=struct.unpack("<4sII",f.read(12))
    assert magic==b"glTF" and version==2 and size==path.stat().st_size
    n,typ=struct.unpack("<II",f.read(8))
    assert typ==0x4e4f534a
    doc=json.loads(f.read(n).decode("utf-8").rstrip("\x00 "))
acc=doc.get("accessors",[])
mesh=doc.get("meshes",[])
mat=doc.get("materials",[])
attribute_names=collections.Counter()
component_types=collections.Counter()
topologies=collections.Counter()
index_component=collections.Counter()
triangles=0
primitives=0
for m in mesh:
    for p in m.get("primitives",[]):
        primitives+=1
        mode=p.get("mode",4)
        topologies[str(mode)]+=1
        for k,i in p.get("attributes",{}).items():
            attribute_names[k]+=1
            if i<len(acc): component_types[f"{k}:{acc[i].get('componentType')}:{acc[i].get('type')}"]+=1
        i=p.get("indices")
        if i is not None and i<len(acc):
            index_component[str(acc[i].get("componentType"))]+=1
            if mode==4:triangles+=acc[i].get("count",0)//3
        elif mode==4:
            pos=p.get("attributes",{}).get("POSITION")
            if pos is not None:triangles+=acc[pos].get("count",0)//3
materials=[]
for m in mat:
    pbr=m.get("pbrMetallicRoughness") or {}
    materials.append({
      "name":m.get("name"),"baseColorFactor":pbr.get("baseColorFactor",[1,1,1,1]),
      "metallicFactor":pbr.get("metallicFactor",1),
      "roughnessFactor":pbr.get("roughnessFactor",1),
      "doubleSided":m.get("doubleSided",False),
      "alphaMode":m.get("alphaMode","OPAQUE"),
      "alphaCutoff":m.get("alphaCutoff",0.5),
      "coreTextures":sorted([k for k in pbr if "Texture" in k]+[k for k in ("normalTexture","occlusionTexture","emissiveTexture") if k in m]),
      "extensions":sorted((m.get("extensions") or {}).keys()),
    })
report={
 "source_file":str(path),"bytes":size,"node_count":len(doc.get("nodes",[])),
 "mesh_count":len(mesh),"primitives":primitives,"triangles_indexed_nominal":triangles,
 "index_component_types":dict(index_component),
 "topology_modes":dict(topologies),
 "attributes":dict(attribute_names),
 "attribute_formats":dict(component_types),
 "materials":materials,"textures":len(doc.get("textures",[])),
 "extensionsUsed":doc.get("extensionsUsed",[]),
 "extensionsRequired":doc.get("extensionsRequired",[]),
 "bufferViews":len(doc.get("bufferViews",[])),
 "accessors":len(acc),
 "vertex_colors":bool(attribute_names.get("COLOR_0")),
 "skinned":bool(attribute_names.get("JOINTS_0")),
 "has_morph_targets":any("targets" in p for m in mesh for p in m.get("primitives",[])),
 "notes":"Static metadata audit; no GPU rendering, shader compilation or material equivalence validated."
}
out=ROOT/"reports"/"graphics-baseline-audit.json"
out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("GRAPHICS_AUDIT",out)
for k in ("bytes","node_count","mesh_count","primitives","triangles_indexed_nominal","topology_modes","attributes","index_component_types","textures","extensionsUsed","extensionsRequired","vertex_colors","skinned","has_morph_targets"):
 print(k,report[k])
for m in materials:print("MATERIAL",m["name"],"alpha",m["alphaMode"],"metal",m["metallicFactor"],"rough",m["roughnessFactor"],"doubleSided",m["doubleSided"],"extras",m["extensions"])
