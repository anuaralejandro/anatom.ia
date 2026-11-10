#!/usr/bin/env python3
"""Consistency checks for Stage 6 renderer DESIGN documents and verified fixture.

Not a GPU compatibility test.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def j(path):return json.loads((ROOT/path).read_text(encoding="utf-8"))
profile=j("contracts/render-profile-v1.json")
quality=j("contracts/quality-profiles-v1.json")
accept=j("contracts/renderer-acceptance-v1.json")
graphics=j("reports/graphics-baseline-audit.json")
lod=j("reports/pelvis-lod-policy-proposal.json")
validation=j("reports/pelvis-baseline-validation.json")
compat=j("reports/pelvis-pbr-compat-validation.json")
cat=j("reports/pelvis-catalog-candidate.json")
checks={
 "profiles_have_schema_v1":all(x.get("schemaVersion")==1 for x in (profile,quality,accept)),
 "backend_pair":set(profile["bundles"])>=set(["webgpu","webgl2"]),
 "downlevel_webgl2_guardrails":profile["webgl2Guardrails"]["storageBuffers"] is False and profile["webgl2Guardrails"]["computeShaders"] is False,
 "real_base_glb_26_structures":validation["pass"] and validation["identified_in_glb"]==26,
 "core_compat_geometry_unchanged":compat["pass"] and compat["geometry_identical"],
 "core_compat_no_extensions":profile["contract"]["materialExtensionsInBaseline"]==[],
 "metadata_actual_triangles":graphics["triangles_indexed_nominal"]==lod["total_triangles_nominal"]==38605,
 "data_actual_primitives":graphics["primitives"]==profile["fixture"]["primitives"]==27,
 "catalog_26_unique_ids":len({x["id"] for x in cat["structures"]})==26,
 "lod_policy_complete":lod["objects"]==len(lod["policies"])==26,
 "runtime_tests_not_falsely_passed":all(x["state"]!="PASS" for x in accept["gates"] if x["id"] not in ["R00","R01"]),
 "quality_targets_provisional":quality["status"]=="provisional_targets_not_benchmarked"
}
report={
  "stage":"6-renderer-contract",
  "result":"PASS_DESIGN_ONLY" if all(checks.values()) else "FAIL",
  "checks":checks,
  "verified_passes":["R00","R01"],
  "not_proven":["shader_compile","webgpu_render","webgl2_render","picking","lod_generation","mobile_fps","commercial_licenses"],
  "tool":"tools/validate_stage6_contracts.py"
}
out=ROOT/"reports"/"stage6-contract-validation.json"
out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
for k,v in checks.items():print("PASS" if v else "FAIL",k)
print("STAGE6",report["result"])
sys.exit(0 if all(checks.values()) else 1)
