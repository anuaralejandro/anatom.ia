#!/usr/bin/env python3
"""Independent M04 read-only browser adversarial checks; no code mutation."""
import json,threading,http.server,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))
from serve_probe import DualWasmHandler
PORT=8099
out=ROOT/"reports"/"audit"/"m04-pre-fix-adversarial.json"
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",PORT),DualWasmHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    findings={}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True,args=["--enable-unsafe-webgpu","--use-angle=d3d11","--disable-gpu-sandbox"])
            try:
                for test in ["legacy_glb","legacy_cube","forged_load_plan","real_offline_reload","manifest_catalog_integrity"]:
                    ctx=browser.new_context(viewport={"width":1280,"height":800})
                    pg=ctx.new_page()
                    errors=[]
                    pg.on("pageerror",lambda e:errors.append(str(e)))
                    try:
                        pg.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgl2&scene=pelvis",wait_until="domcontentloaded",timeout=25000)
                        pg.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"',timeout=30000)
                        if test=="legacy_glb":
                            result=pg.evaluate("""async () => { const resp=await fetch('./pelvis-base-lod0.glb'); const bytes=new Uint8Array(await resp.arrayBuffer());const e=window.__atlasEngine();try{const x=e.loadGlbBytes(bytes);return {result:'OK',nodes:e.getStats().total_nodes,generation:e.currentGeneration(),memory_generation:e.getMemoryStats().currentGeneration}}catch(ex){return {result:'ERR',error:String(ex)}}}""")
                        elif test=="legacy_cube":
                            result=pg.evaluate("""() => {const e=window.__atlasEngine();try{e.loadSyntheticCube();return {result:'OK',nodes:e.getStats().total_nodes,generation:e.currentGeneration(),memory_generation:e.getMemoryStats().currentGeneration}}catch(ex){return {result:'ERR',error:String(ex)}}}""")
                        elif test=="forged_load_plan":
                            result=pg.evaluate("""async () => {const e=window.__atlasEngine();const p=e.createLoadPlan('pelvis','male-adult',0);const orig=p.variant_id;p.variant_id='female-adult';const b=new Uint8Array(await(await fetch('./pelvis-base-lod0.glb')).arrayBuffer());const gen=e.nextGeneration(555);try{const x=e.applyPackageBytes(b,p,555,gen);return {result:'ACCEPTED',reported_variant:x.variant,actual_variant:e.getSceneSnapshot().variant,plan_variant:p.variant_id,original_variant:orig}}catch(ex){return {result:'REJECTED',error:ex?.code||String(ex)}}}""")
                        elif test=="real_offline_reload":
                            ctx.set_offline(True)
                            try:
                                pg.reload(wait_until="domcontentloaded",timeout=10000)
                                pg.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"',timeout=8000)
                                result={"result":"RELOADED_OFFLINE"}
                            except Exception as ex:
                                result={"result":"FAILED_RELOAD","reason":str(ex)[:150]}
                            ctx.set_offline(False)
                        else:
                            result=pg.evaluate("""() => {const sm=window.__atlasStreamManager;return {manifest_loaded:!!sm.manifest,catalog_reference:sm.manifest?.catalog?.url,structure_list_count:document.querySelectorAll('.structure-item').length,manifest_catalog_digest_verified_in_manager:/catalog.*sha|expected_catalog_sha256/.test(sm.initManifest.toString()),app_has_separate_catalog_loader:typeof window.__atlasState==='object'}}""")
                        findings[test]={"result":result,"page_errors":errors}
                    except Exception as e:
                        findings[test]={"fatal":str(e)[:250],"page_errors":errors}
                    finally:
                        ctx.close()
                    print(test,json.dumps(findings[test],ensure_ascii=False)[:420],flush=True)
            finally:browser.close()
    finally:server.shutdown()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"results":findings,"note":"Adversarial audit: results are observations, not automatically PASS."},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SAVED",out)
if __name__=="__main__":main()
