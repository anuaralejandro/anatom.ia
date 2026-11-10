#!/usr/bin/env python3
"""Validate experimental pelvis GLB structure, identifiers and source crosswalk.

No import of Blender required. Verifies GLB metadata and header, NOT anatomical fidelity.
"""
import json,struct,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
GLB=ROOT/"reports"/"experimental"/"pelvis-baseline-uncompressed.glb"
FIX=ROOT/"reports"/"pelvis-ta2-crosswalk.json"
OUT=ROOT/"reports"/"pelvis-baseline-validation.json"
def main():
    expected=json.loads(FIX.read_text(encoding="utf-8"))["objects"]
    expected_ids={row["anatomy_id_proposal"]: row["source_object"] for row in expected}
    raw=GLB.read_bytes()
    assert len(raw)>=20,"Not a GLB"
    magic,version,length=struct.unpack_from("<4sII",raw,0)
    assert magic==b"glTF" and version==2 and length==len(raw),"Bad GLB header"
    cursor=12
    chunks=[]
    while cursor<len(raw):
        n,kind=struct.unpack_from("<II",raw,cursor)
        cursor+=8
        assert n%4==0 and cursor+n<=len(raw),"GLB chunk invalid"
        chunks.append((kind,n,cursor))
        cursor+=n
    assert cursor==len(raw),"GLB trailing bytes"
    assert chunks and chunks[0][0]==0x4E4F534A,"First chunk is not JSON"
    gltf=json.loads(raw[chunks[0][2]:chunks[0][2]+chunks[0][1]].decode("utf-8").rstrip("\x00 "))
    nodes=gltf.get("nodes",[])
    ids={}
    missing_mesh=[]
    for node in nodes:
        extras=node.get("extras") or {}
        sid=extras.get("atlas_id")
        if sid:
            assert sid not in ids,"Duplicate anatomy ID: "+sid
            ids[sid]=node
            if "mesh" not in node:missing_mesh.append(sid)
    missing=sorted(set(expected_ids)-set(ids))
    extra=sorted(set(ids)-set(expected_ids))
    wrong_source=sorted(sid for sid,node in ids.items() if expected_ids.get(sid)!=node.get("extras",{}).get("source_object"))
    invalid_meshes=[]
    for sid,node in ids.items():
        index=node.get("mesh")
        if not isinstance(index,int) or not (0<=index<len(gltf.get("meshes",[]))):
            invalid_meshes.append(sid)
        elif not gltf["meshes"][index].get("primitives"):
            invalid_meshes.append(sid)
    passed=not any([missing,extra,wrong_source,invalid_meshes,missing_mesh]) and len(ids)==len(expected)
    report={
      "pass":passed,"expected":len(expected),"identified_in_glb":len(ids),
      "missing":missing,"extra":extra,"wrong_source":wrong_source,
      "invalid_meshes":invalid_meshes,"missing_mesh":missing_mesh,
      "glb_bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
      "nodes_total":len(nodes),"meshes_total":len(gltf.get("meshes",[])),
      "primitives_total":sum(len(x.get("primitives",[])) for x in gltf.get("meshes",[])),
      "extensions_used":gltf.get("extensionsUsed",[]),
      "materials":len(gltf.get("materials",[])),"textures":len(gltf.get("textures",[])),
      "notes":"Identity/GLB structural check only. No runtime rendering, mobile performance, source-license clearance, meshopt or LOD proven."
    }
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("VALIDATION", "PASS" if passed else "FAIL",json.dumps(report,ensure_ascii=False))
    return 0 if passed else 1
if __name__=="__main__":sys.exit(main())
