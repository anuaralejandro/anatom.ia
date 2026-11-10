#!/usr/bin/env python3
"""Independent M03 browser smoke: load actual LOD0/LOD1 WASM on each backend."""
import json,threading,http.server,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))
from serve_probe import DualWasmHandler
PORT=8096
OUT=ROOT/"target"/"audit-m03-browser"
OUT.mkdir(parents=True,exist_ok=True)
def main():
 server=http.server.ThreadingHTTPServer(("127.0.0.1",PORT),DualWasmHandler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 results=[]
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True,args=["--enable-unsafe-webgpu","--use-angle=d3d11","--disable-gpu-sandbox"])
   try:
    for backend in ("webgl2","webgpu"):
     for scene in ("pelvis","pelvis-lod1"):
      case={"requested_backend":backend,"scene":scene,"requests":[],"console_errors":[]}
      ctx=browser.new_context(viewport={"width":1280,"height":800})
      page=ctx.new_page()
      page.on("response",lambda r:case["requests"].append({"url":r.url.split("/")[-1],"status":r.status}) if r.url.endswith(".glb") else None)
      page.on("pageerror",lambda e:case["console_errors"].append(str(e)))
      try:
       page.goto(f"http://127.0.0.1:{PORT}/index.html?backend={backend}&scene={scene}",wait_until="domcontentloaded",timeout=20000)
       page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"',timeout=30000)
       case["effective_backend"]=page.locator("html").get_attribute("data-atlas-backend")
       case["loaded_scene"]=page.locator("html").get_attribute("data-atlas-scene")
       case["visible_nodes"]=page.locator("#stat-nodes").inner_text()
       case["triangle_count"]=page.locator("#stat-tris").inner_text()
       case["list_rows"]=page.locator(".structure-item").count()
       expectedfile="pelvis-base-lod0.glb" if scene=="pelvis" else "pelvis-lod1.glb"
       case["expected_asset"]=expectedfile
       fetched=[x for x in case["requests"] if x["url"]==expectedfile and x["status"]==200]
       case["actual_asset_retrieved"]=bool(fetched)
       page.locator(".structure-item").first.click()
       page.locator("#btn-isolate").click()
       case["isolated_nodes"]=page.locator("#stat-nodes").inner_text()
       page.locator("#btn-reset-vis").click()
       case["restored_nodes"]=page.locator("#stat-nodes").inner_text()
       shot=OUT/f"{scene}-{backend}.png"
       page.screenshot(path=str(shot),full_page=True)
       case["status"]="PASS" if (
         case["effective_backend"]==backend and case["loaded_scene"]==scene and
         case["actual_asset_retrieved"] and case["list_rows"]==26 and
         case["visible_nodes"].replace(" ","").startswith("26/") and
         case["isolated_nodes"].replace(" ","").startswith("1/") and
         case["restored_nodes"].replace(" ","").startswith("26/") and
         not case["console_errors"] ) else "FAIL"
      except Exception as e:
       case["status"]="FAIL";case["error"]=str(e)[:300]
      finally:
       ctx.close()
      results.append(case)
      print("M03_BROWSE",backend,scene,case["status"],case.get("triangle_count"),case.get("actual_asset_retrieved"),flush=True)
   finally:browser.close()
 finally:server.shutdown()
 report={"status":"PASS" if all(c["status"]=="PASS" for c in results) else "FAIL","cases":results,
  "limitations":["Chrome Windows desktop headless only","No physical mobile, FPS or touch pinch benchmarking"]}
 reportpath=ROOT/"reports"/"audit"/"m03-dual-backend-browser.json"
 reportpath.parent.mkdir(parents=True,exist_ok=True);reportpath.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("RESULT",report["status"],reportpath)
 sys.exit(0 if report["status"]=="PASS" else 1)
if __name__=="__main__":main()
