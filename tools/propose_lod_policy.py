#!/usr/bin/env python3
"""Propose per-structure LOD policy from actual indexed triangle counts, no simplification."""
import json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
path=ROOT/"reports"/"experimental"/"pelvis-pbr-core-compat.glb"
with path.open("rb") as f:
    f.read(12);n,kind=struct.unpack("<II",f.read(8))
    assert kind==0x4e4f534a
    gltf=json.loads(f.read(n).decode("utf-8").rstrip("\x00 "))
cross={x["anatomy_id_proposal"]:x for x in json.loads((ROOT/"reports"/"pelvis-ta2-crosswalk.json").read_text(encoding="utf-8"))["objects"]}
acc=gltf.get("accessors",[])
meshes=gltf.get("meshes",[])
items=[]
for node in gltf["nodes"]:
    sid=node.get("extras",{}).get("atlas_id")
    if not sid:continue
    source=node["extras"].get("source_object","")
    m=meshes[node["mesh"]]
    indices=sum(acc[p["indices"]]["count"] for p in m["primitives"] if "indices" in p)
    tris=indices//3
    kind=node["extras"].get("source_kind")
    if kind=="CURVE":
        category="thin_tubular"
        lod1="preserve"
        lod2="preserve_until_curve_topology_test"
    elif tris>=8000:
        category="large_surface"
        lod1="candidate_meshoptimizer_0.65_with_error_bound"
        lod2="candidate_meshoptimizer_0.35_with_error_bound"
    elif tris>=2500:
        category="mid_surface"
        lod1="candidate_meshoptimizer_0.75_with_error_bound"
        lod2="reuse_lod1_unless_measured_benefit"
    else:
        category="small_surface"
        lod1="reuse_base"
        lod2="reuse_base"
    items.append({
        "anatomy_id":sid,"source_object":source,"source_type":kind,
        "indexed_triangles_nominal":tris,"category":category,
        "lod0":"original_uncompressed_core_pbr",
        "lod1_policy":lod1,"lod2_policy":lod2,
        "must_preserve_source_identifiers":True,
        "selection_resident_must_use_highest_available_lod":True,
        "review_status":"proposal_not_generated"
    })
report={
 "status":"proposal_not_generated_or_benchmarked",
 "source_glb":str(path),
 "total_triangles_nominal":sum(x["indexed_triangles_nominal"] for x in items),
 "objects":len(items),
 "eligible_lod1":sum(x["lod1_policy"].startswith("candidate") for x in items),
 "eligible_lod2":sum(x["lod2_policy"].startswith("candidate") for x in items),
 "notes":["Small skeletal organs, nerves and vessels may cost less to leave intact than maintain extra LOD copies.","Screen-space error and bounds must be measured before approving generated LOD.","Tri count is indexed glTF primitive triangles (Blender quad polygons differ)."],
 "policies":items
}
dest=ROOT/"reports"/"pelvis-lod-policy-proposal.json"
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("LOD_POLICY",report["objects"],"tris",report["total_triangles_nominal"],"lod1_eligible",report["eligible_lod1"],"lod2_eligible",report["eligible_lod2"])
for x in items:print(x["indexed_triangles_nominal"],x["category"],x["source_object"],x["lod1_policy"])
