#!/usr/bin/env python3
"""Read-only M04H scheduler behavior audit; mocks network inside Chrome."""
import json,threading,http.server,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))
from serve_probe import DualWasmHandler
PORT=8107
server=http.server.ThreadingHTTPServer(("127.0.0.1",PORT),DualWasmHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True,args=["--enable-unsafe-webgpu","--use-angle=d3d11","--disable-gpu-sandbox"])
  page=b.new_page()
  page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgl2&scene=cube",wait_until="domcontentloaded",timeout=20000)
  page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=20000)
  result=page.evaluate("""async () => {
    const {AssetStreamManager}=await import('/asset-stream-manager.js');
    const nativeFetch=window.fetch;
    const m = new AssetStreamManager({logger:()=>{}});
    m.cacheAvailable=false;
    m.manifest={atlasVersion:'audit-only'};
    let calls404=0;
    window.fetch=async()=>{calls404++;return new Response('missing',{status:404,statusText:'Not Found'});};
    let e404=null;
    try{await m.fetchWithRetry('https://local.test/not-found',{},2,500);}catch(err){e404=String(err);}
    window.fetch=nativeFetch;
    let abortCalls=0;
    const payload=new Uint8Array([97,98,99]).buffer;
    const bytes=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',payload))).map(v=>v.toString(16).padStart(2,'0')).join('');
    const plan={package_id:'audit',package_url:'https://local.test/asset.glb',expected_package_bytes:3,expected_package_sha256:bytes};
    window.fetch=(url,{signal}={})=>new Promise((resolve,reject)=>{
      abortCalls++;
      if(signal?.aborted)return reject(new DOMException('aborted','AbortError'));
      signal?.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')),{once:true});
      setTimeout(()=>resolve(new Response(payload,{status:200})),180);
    });
    const c1=new AbortController(),c2=new AbortController();
    const a=m.loadPackageBytes(plan,c1.signal).then(()=>({status:'resolved'}),e=>({status:'rejected',error:String(e)}));
    const bb=m.loadPackageBytes(plan,c2.signal).then(()=>({status:'resolved'}),e=>({status:'rejected',error:String(e)}));
    setTimeout(()=>c1.abort(),40);
    const shared=await Promise.all([a,bb]);
    window.fetch=nativeFetch;
    return {calls404,error404:e404,coalescedAbort:shared,fetchCallsForShared:abortCalls};
  }""")
  b.close()
finally:server.shutdown()
outfile=ROOT/"reports"/"audit"/"m04h-independent-scheduler.json"
outfile.parent.mkdir(parents=True,exist_ok=True)
outfile.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("RESULT",json.dumps(result,ensure_ascii=False))
print("SAVED",outfile)
