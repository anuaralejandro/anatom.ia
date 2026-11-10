#!/usr/bin/env python3
"""Produce deterministic baseline glTF core PBR fixture, preserving ALL binary geometry.

- Only adjusts material metallic/roughness and strips optional specular/ior extensions.
- Keeps base colors, alpha modes, double sided, nodes, mesh extras and binary chunks.
- For local compatibility testing ONLY; not an anatomy/visual QA or commercial release.
"""
import hashlib,json,struct
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
src=ROOT/"reports"/"experimental"/"pelvis-baseline-uncompressed.glb"
dst=ROOT/"reports"/"experimental"/"pelvis-pbr-core-compat.glb"
raw=src.read_bytes()
magic,version,total=struct.unpack_from("<4sII",raw)
assert magic==b"glTF" and version==2 and total==len(raw)
cursor=12;chunks=[]
while cursor<len(raw):
    n,t=struct.unpack_from("<II",raw,cursor)
    cursor+=8
    assert n%4==0 and cursor+n<=len(raw)
    chunks.append((t,raw[cursor:cursor+n]))
    cursor+=n
assert chunks[0][0]==0x4e4f534a
doc=json.loads(chunks[0][1].decode("utf-8").rstrip(" \x00"))
# Stable PBR grade per anatomy category. No baked metallic shaders for biological tissues.
rough={
 "bone":0.73,"cartilage":0.57,"organ":0.64,"gland":0.58,
 "mucosa":0.53,"ligament":0.77,"orbicularis":0.73,
 "artery":0.57,"vein":0.61,"nerve":0.70
}
changes=[]
for m in doc.get("materials",[]):
    name=m.get("name","").lower()
    category=next((k for k in rough if k in name),"organ")
    pbr=m.setdefault("pbrMetallicRoughness",{})
    before={"metallic":pbr.get("metallicFactor",1.0),"roughness":pbr.get("roughnessFactor",1.0),"extensions":sorted((m.get("extensions") or {}).keys())}
    pbr["metallicFactor"]=0.0
    pbr["roughnessFactor"]=rough[category]
    for extension in ("KHR_materials_specular","KHR_materials_ior"):
        if "extensions" in m: m["extensions"].pop(extension,None)
    if not m.get("extensions"):m.pop("extensions",None)
    changes.append({"name":m.get("name"),"category":category,"before":before,"after":{"metallic":0.0,"roughness":rough[category]}})
# Other user extensions are not expected in this reference.
used=sorted(set(key for m in doc.get("materials",[]) for key in (m.get("extensions") or {})))
assert not used, "Unexpected material extensions remain"
doc.pop("extensionsUsed",None)
doc.pop("extensionsRequired",None)
assert not any("extensions" in n for n in doc.get("nodes",[]))
newjson=json.dumps(doc,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode("utf-8")
newjson+=b" "*((-len(newjson))%4)
outchunks=[(0x4e4f534a,newjson)]+chunks[1:]
out=bytearray(struct.pack("<4sII",b"glTF",2,12+sum(8+len(buf) for _,buf in outchunks)))
for t,buf in outchunks:
    out.extend(struct.pack("<II",len(buf),t))
    out.extend(buf)
dst.write_bytes(out)
assert len(out)==struct.unpack_from("<I",out,8)[0]
original_bin_sha=hashlib.sha256(b"".join(v for t,v in chunks if t==0x004e4942)).hexdigest()
new_bin_sha=hashlib.sha256(b"".join(v for t,v in outchunks if t==0x004e4942)).hexdigest()
assert original_bin_sha==new_bin_sha
orig_ids=sorted(n.get("extras",{}).get("atlas_id") for n in json.loads(chunks[0][1].decode("utf-8").rstrip(" \x00")).get("nodes",[]) if n.get("extras",{}).get("atlas_id"))
new_ids=sorted(n.get("extras",{}).get("atlas_id") for n in doc.get("nodes",[]) if n.get("extras",{}).get("atlas_id"))
assert orig_ids==new_ids and len(orig_ids)==26
report={
 "status":"experimental_only_not_licensed_for_distribution",
 "input":str(src),"output":str(dst),"input_bytes":len(raw),"output_bytes":len(out),
 "input_sha256":hashlib.sha256(raw).hexdigest(),"output_sha256":hashlib.sha256(out).hexdigest(),
 "binary_payload_preserved_sha256":original_bin_sha,
 "anatomy_ids_preserved":len(new_ids),
 "materials_graded":changes,
 "required_extensions":[],"used_extensions":[],
 "notes":"Only material JSON modified; GLB binary payload byte-for-byte unchanged. Equivalent appearance not claimed. No GPU render test, no LOD."
}
report_path=ROOT/"reports"/"pelvis-pbr-compat-report.json"
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("PBR_CORE_COMPAT",dst,"bytes",len(out),"IDs",len(new_ids),"binary_match",original_bin_sha==new_bin_sha,"materials",len(changes))
