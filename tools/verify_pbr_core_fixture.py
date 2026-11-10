#!/usr/bin/env python3
"""Validate core PBR test fixture equivalence to the original pelvis baseline.

This is a metadata/geometry preservation check, not a visual/medical/GPU pass.
"""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
original=ROOT/"reports"/"experimental"/"pelvis-baseline-uncompressed.glb"
compat=ROOT/"reports"/"experimental"/"pelvis-pbr-core-compat.glb"

def load(p):
    raw=p.read_bytes()
    assert len(raw)>=20
    magic,ver,n=struct.unpack_from("<4sII",raw,0)
    assert magic==b"glTF" and ver==2 and n==len(raw)
    chunks=[];c=12
    while c<len(raw):
        n,typ=struct.unpack_from("<II",raw,c);c+=8
        assert n%4==0 and c+n<=len(raw)
        chunks.append((typ,raw[c:c+n]));c+=n
    assert c==len(raw) and chunks[0][0]==0x4e4f534a
    return json.loads(chunks[0][1].decode("utf-8").rstrip("\x00 ")),chunks

base,a=load(original);core,b=load(compat)
errors=[]
def check(cond,msg):
    if not cond: errors.append(msg)
check([(k,n.get(k)) for n in base.get("nodes",[]) for k in ("name","mesh","extras")]==[(k,n.get(k)) for n in core.get("nodes",[]) for k in ("name","mesh","extras")],"node names/IDs/mesh links differ")
check(base.get("meshes")==core.get("meshes"),"mesh topology metadata changed")
check(base.get("accessors")==core.get("accessors"),"accessors changed")
check(base.get("bufferViews")==core.get("bufferViews"),"bufferViews changed")
check(base.get("buffers")==core.get("buffers"),"buffers changed")
check([(t,c) for t,c in a if t!=0x4e4f534a]==[(t,c) for t,c in b if t!=0x4e4f534a],"binary payload not identical")
check(len(base.get("materials",[]))==len(core.get("materials",[])),"material count differs")
check(not core.get("extensionsUsed") and not core.get("extensionsRequired"),"extensions remain declared")
check(all(not m.get("extensions") for m in core.get("materials",[])),"material extensions remain")
check(all(m.get("pbrMetallicRoughness",{}).get("metallicFactor")==0 for m in core.get("materials",[])),"non-zero metallic in core PBR")
check(all(0.0<=m.get("pbrMetallicRoughness",{}).get("roughnessFactor",1)<=1.0 for m in core.get("materials",[])),"roughness out of range")
check(all(m.get("pbrMetallicRoughness",{}).get("baseColorFactor",[1,1,1,1])==bm.get("pbrMetallicRoughness",{}).get("baseColorFactor",[1,1,1,1]) for m,bm in zip(core.get("materials",[]),base.get("materials",[]))),"base color changed")
check(all(m.get("alphaMode","OPAQUE")==bm.get("alphaMode","OPAQUE") and m.get("doubleSided",False)==bm.get("doubleSided",False) for m,bm in zip(core.get("materials",[]),base.get("materials",[]))),"alpha/doubleSided changed")
report={
  "pass":not errors,
  "errors":errors,"source":str(original),"core_pbr":str(compat),
  "geometry_identical":not any("payload" in e or "mesh" in e or "accessors" in e or "node" in e for e in errors),
  "output_bytes":compat.stat().st_size,
  "output_sha256":hashlib.sha256(compat.read_bytes()).hexdigest(),
  "notes":"No WGPU/WebGL2 rendering, shader compilation, perceptual accuracy or anatomical validation performed."
}
output=ROOT/"reports"/"pelvis-pbr-compat-validation.json"
output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("CORE_PBR_CHECK", "PASS" if not errors else "FAIL",json.dumps(report))
sys.exit(0 if not errors else 1)
