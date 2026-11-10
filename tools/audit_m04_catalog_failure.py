#!/usr/bin/env python3
"""Verify fail-closed catalog corruption on BOTH real WASM backends."""
import json,threading,http.server,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))
from serve_probe import DualWasmHandler
PORT=8100
srv=http.server.ThreadingHTTPServer(("127.0.0.1",PORT),DualWasmHandler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
out=ROOT/"reports"/"audit"/"m04-catalog-tamper.json"
cases=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True,args=["--enable-unsafe-webgpu","--use-angle=d3d11","--disable-gpu-sandbox"])
  try:
   for backend in ("webgpu","webgl2"):
    ctx=b.new_context(viewport={"width":1100,"height":730})
    page=ctx.new_page()
    assets=[]
    page.on("request", lambda req: assets.append(req.url.rsplit("/",1)[-1]) if req.url.endswith(".glb") else None)
    page.route("**/catalog.json",lambda route:route.fulfill(status=200,content_type="application/json",body='{"structures":[]}'))
    result={"backend":backend}
    try:
     page.goto(f"http://127.0.0.1:{PORT}/index.html?backend={backend}&scene=pelvis",wait_until="domcontentloaded")
     page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "error"',timeout=16000)
     result["status"]="PASS" if len(assets)==0 else "FAIL"
     result["requested_glbs"]=assets
     result["visible_error"]=page.locator("#error-message").inner_text()
    except Exception as e:
     result["status"]="FAIL";result["exception"]=str(e)[:230]
    cases.append(result)
    print("TAMPER",backend,result["status"],"GLB_COUNT",len(assets),flush=True)
    ctx.close()
  finally:b.close()
finally:srv.shutdown()
result={"status":"PASS" if all(x["status"]=="PASS" for x in cases) else "FAIL","cases":cases}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("OUT",out,result["status"])
sys.exit(0 if result["status"]=="PASS" else 1)
