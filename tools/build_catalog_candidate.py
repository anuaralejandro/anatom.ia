#!/usr/bin/env python3
"""Join the audited Blender fixture and TA2 terminology into a REVIEW-REQUIRED catalog.

Never infers missing identifiers or clears license status.
"""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"sources"/"z-anatomy-upstream"/"TA2.csv"
rows=[]
with SOURCE.open(encoding="utf-8-sig",newline="") as f:
    reader=csv.DictReader((x.strip()[1:-1] if x.strip().startswith('"') and x.strip().endswith('"') else x for x in f if x.strip()),delimiter=";")
    rows=list(reader)
by_id={r["TA2ID"]:r for r in rows if r.get("TA2ID")}
fixture=json.loads((ROOT/"reports"/"pelvis-fixture-candidate.json").read_text(encoding="utf-8"))
cross=json.loads((ROOT/"reports"/"pelvis-ta2-crosswalk.json").read_text(encoding="utf-8"))
geo=json.loads((ROOT/"reports"/"pelvis-spatial-curve-audit.json").read_text(encoding="utf-8"))
cross_by={r["source_object"]:r for r in cross["objects"]}
geo_by={r["source_object"]:r for r in geo["items"]}
structures=[]; orientation_warnings=[]
for item in fixture["objects"]:
    name=item["source_object"]
    x=cross_by[name]; t=by_id[x["ta2_id"]]
    location=geo_by[name]["bounds_center"]
    side=x["laterality_suffix"]
    if side and (location[0]>0 if side=="left" else location[0]<0) is False:
        orientation_warnings.append({"source_object":name,"x":location[0],"suffix_side":side})
    structures.append({
        "id":x["anatomy_id_proposal"],"conceptId":"ta2:"+x["ta2_id"],
        "ta2Id":x["ta2_id"],
        "labels":{"es-MX":t["Español"],"en":t["English"],"la":t["Latin"]},
        "side":side or "unpaired_or_unspecified","variant":"male-adult",
        "source":{"repository":"Z-Anatomy/Models-of-human-anatomy","commit":fixture["source_commit"],"object":name,"objectType":item["source_object_type"]},
        "geometry":{"boundsCenterBlender":location,"sourceType":item["source_object_type"]},
        "licenseStatus":"pending_per_asset_review",
        "validationStatus":"lexical_exact_and_geometry_presence_only"
    })
assert len(set(x["id"] for x in structures))==len(structures),"Duplicate IDs"
out={"schemaVersion":0,"status":"draft_non_distributable",
     "source":"TA2.csv and Z-Anatomy Startup.blend",
     "warning":"Not for production: label matching is lexical, no anatomical clinician review or per-asset license clearance.",
     "orientationWarnings":orientation_warnings,"structures":structures}
dest=ROOT/"reports"/"pelvis-catalog-candidate.json"
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("CATALOG_CANDIDATE",len(structures),"orientation_warnings",len(orientation_warnings))
if orientation_warnings:print(json.dumps(orientation_warnings,ensure_ascii=False))
for v in structures[:8]:print(v["id"],v["labels"]["es-MX"])
