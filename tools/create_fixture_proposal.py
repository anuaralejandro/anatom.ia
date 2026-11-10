#!/usr/bin/env python3
"""Create a real-object fixture *proposal* from the Blender read-only inventory."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = [
    "Sacrum", "Coccyx", "Pubic symphysis",
    "Urinary bladder", "Prostate",
    "Seminal gland.l", "Seminal gland.r",
    "Testis.l", "Testis.r",
    "Glans penis", "Corpus cavernosum of penis", "Corpus spongiosum of penis",
    "Sacrospinous ligament.l", "Sacrospinous ligament.r",
    "Sacrotuberous ligament.l", "Sacrotuberous ligament.r",
    "Coccygeus muscle.l", "Coccygeus muscle.r",
    "Common iliac artery.l", "Common iliac artery.r",
    "Internal iliac artery.l", "Internal iliac artery.r",
    "External iliac vein.l", "External iliac vein.r",
    "Femoral nerve.l", "Femoral nerve.r",
]
report = json.loads((ROOT / "reports" / "z-anatomy-blend-inventory.json").read_text(encoding="utf-8"))
available = {item["name"]: item for item in report["matched_anatomy_terms"]}
missing = sorted(set(NAMES) - set(available))
selected = []
for name in NAMES:
    if name in available:
        obj = available[name]
        selected.append({
            "source_object": name,
            "source_object_type": obj["type"],
            "source_polygons_nominal": obj["polygons"],
            "collection_candidates": obj["collections"],
            "anatomy_id": None,
            "role": "anatomy",
            "status": "candidate_requires_anatomy_id_and_licence_audit",
        })
result = {
    "status": "candidate_only_not_exported",
    "source_repository": "https://github.com/Z-Anatomy/Models-of-human-anatomy",
    "source_commit": "56016ea6da9de755ee4229f61fafc2b313db66ff",
    "source_blend": "sources/z-anatomy-template/Z-Anatomy/Startup.blend",
    "requested_objects": len(NAMES),
    "found_objects": len(selected),
    "missing_objects": missing,
    "mesh_objects": sum(x["source_object_type"] == "MESH" for x in selected),
    "curve_objects": sum(x["source_object_type"] == "CURVE" for x in selected),
    "mesh_polygons_nominal": sum(x["source_polygons_nominal"] or 0 for x in selected),
    "notes": [
        "No fixture has been exported; this only validates name/type existence.",
        "Anatomy IDs, coordinate checks, curve radii, bounds and licensing require inspection.",
        "Source mesh polygons exclude tessellation of CURVE objects.",
        "Some testis/penis structures are perineal rather than strictly intrapelvic."
    ],
    "objects": selected,
}
path = ROOT / "reports" / "pelvis-fixture-candidate.json"
path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"CANDIDATE_RESULT found={len(selected)} missing={len(missing)} mesh={result['mesh_objects']} curve={result['curve_objects']} polys={result['mesh_polygons_nominal']}")
if missing:
    print("MISSING: "+", ".join(missing))
    sys.exit(1)
print("OUTPUT="+str(path))
