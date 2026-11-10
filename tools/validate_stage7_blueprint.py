#!/usr/bin/env python3
"""Stage 7 architecture consistency checks. Does not compile or render anything."""
import json,sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))

plan=load("contracts/implementation-milestones-v1.json")
bridge=load("contracts/engine-bridge-v1.json")
render=load("contracts/render-profile-v1.json")
quality=load("contracts/quality-profiles-v1.json")
accept=load("contracts/renderer-acceptance-v1.json")
fixture=load("reports/pelvis-baseline-validation.json")
core=load("reports/pelvis-pbr-compat-validation.json")
catalog=load("reports/pelvis-catalog-candidate.json")
s6=load("reports/stage6-contract-validation.json")

m=plan["milestones"]
ids=[x["id"] for x in m]
deps={x["id"]:x["dependsOn"] for x in m}
def dag_ok():
    seen=set(); visiting=set()
    def dfs(n):
        if n in visiting:return False
        if n in seen:return True
        if n not in deps:return False
        visiting.add(n)
        for x in deps[n]:
            if not dfs(x):return False
        visiting.remove(n);seen.add(n);return True
    return all(dfs(n) for n in ids)
bridge_names=[x["name"] for x in bridge["api"]]
rids=[x["id"] for x in accept["gates"]]
checks={
 "schemas_v1":all(x["schemaVersion"]==1 for x in (plan,bridge,render,quality,accept)),
 "milestones_7_unique":ids==["M00","M01","M02","M03","M04","M05","M06"] and len(set(ids))==7,
 "milestone_dag_valid":dag_ok(),
 "milestone_gates_unique":len(set(x["gate"] for x in m))==len(m),
 "no_milestone_fake_pass":all(x["status"]=="NOT_STARTED" for x in m),
 "gate_states_not_fake_pass":set(plan["gateState"].values())=={"NOT_RUN"},
 "M01_depends_on_preflight":deps["M01"]==["M00"],
 "M02_depends_on_backend":deps["M02"]==["M01"],
 "M05_depends_on_robust_core":set(deps["M05"])=={"M02","M04"},
 "M06_release_last":deps["M06"]==["M05"],
 "bridge_commands_unique":len(bridge_names)==len(set(bridge_names)),
 "bridge_required_commands":set(["initialize","loadRegion","selectAt","selectStructure","focusStructure","setVisibility","isolateStructure","resetVisibility","resetCamera","getSceneSnapshot","getCapabilities","dispose"]).issubset(bridge_names),
 "bridge_owns_scene_in_rust":bridge["ownership"]["rust"].startswith("scene, camera"),
 "dual_backend_and_shader_contract":all(k in render["bundles"] for k in ("webgpu","webgl2")) and render["engine"]["graphics"]=="wgpu",
 "source_fixture_valid":fixture["pass"] and fixture["identified_in_glb"]==26 and len(catalog["structures"])==26,
 "pbr_geometry_identical":core["pass"] and core["geometry_identical"],
 "stage6_design_pass":s6["result"]=="PASS_DESIGN_ONLY",
 "only_R00_R01_prior_pass":set(x["id"] for x in accept["gates"] if x["state"]=="PASS")=={"R00","R01"},
 "rights_gate_still_blocked":next(x for x in accept["gates"] if x["id"]=="R13")["state"]=="BLOCKED",
 "documents_exist":all((ROOT/f).is_file() for f in ("docs/09_BLUEPRINT_IMPLEMENTACION.md","docs/10_ADR_GATES.md","docs/07_RENDERER_WGPU_SPEC.md","docs/08_LOD_PICKING_TEST_PLAN.md")),
 "fixture_exists":(ROOT/"reports/experimental/pelvis-pbr-core-compat.glb").is_file()
}
ok=all(checks.values())
report={"stage":"7-implementation-blueprint","result":"PASS_DESIGN_ONLY" if ok else "FAIL","checks":checks,"milestones":len(m),"bridge_commands":len(bridge_names),"unrun_gates":list(plan["gateState"].keys()),"remaining_blockers":["runtime shaders and GPU compatibility not tested","legal asset clearance R13 blocked","clinical review R14 pending","physical device benchmarks missing"],"note":"A green design checklist never implies production or implementation completion."}
path=ROOT/"reports"/"stage7-blueprint-validation.json"
path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
for key,value in checks.items(): print("PASS" if value else "FAIL",key)
print("STAGE7",report["result"],"CHECKS",len(checks))
sys.exit(0 if ok else 1)
