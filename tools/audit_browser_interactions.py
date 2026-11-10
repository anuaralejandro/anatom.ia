#!/usr/bin/env python3
"""Independent browser interaction audit for anatom.ia M00-M02.

Unlike screenshot-only smoke tests, this waits for a completed WASM frame, inspects
the effective backend, interacts with the actual DOM, and reports uncertainty.
No source assets are published, modified or uploaded.
"""
import http.server
import json
import pathlib
import sys
import threading
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools"))
from serve_probe import DualWasmHandler

PORT=8093
OUT=ROOT/"reports"/"audit"
OUT.mkdir(parents=True,exist_ok=True)
CHROME=pathlib.Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

def test_case(browser,backend,scene):
    case={"backend_requested":backend,"scene_requested":scene,"ready":False,"errors":[],"console_errors":[],"verified_actions":[]}
    context=browser.new_context(viewport={"width":1280,"height":800},device_scale_factor=1)
    page=context.new_page()
    page.on("pageerror",lambda err:case["errors"].append(str(err)))
    page.on("console",lambda msg: case["console_errors"].append(msg.text) if msg.type=="error" else None)
    try:
        page.goto(f"http://127.0.0.1:{PORT}/index.html?backend={backend}&scene={scene}",wait_until="domcontentloaded",timeout=15000)
        try:
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"',timeout=26000)
            case["ready"]=True
        except Exception as e:
            case["error"]="Timed out waiting for a successful WASM rendered frame: "+str(e)[:180]
        case["status"]=page.locator("html").get_attribute("data-atlas-probe-status")
        case["backend_effective"]=page.locator("html").get_attribute("data-atlas-backend")
        case["scene_effective"]=page.locator("html").get_attribute("data-atlas-scene")
        case["structure_rows"]=page.locator(".structure-item").count()
        case["logs"]=page.locator("#log-drawer").inner_text()[-1800:] if page.locator("#log-drawer").count() else None
        if case["ready"]:
            filename=f"{scene}-{backend}-ready.png"
            page.screenshot(path=str(OUT/filename),full_page=True)
            case["screenshot"]=str(OUT/filename)
        if case["ready"] and scene=="pelvis":
            page.locator(".structure-item").first.click()
            selected=page.locator("#stat-selected").inner_text()
            case["first_selected"]=selected
            case["verified_actions"].append("select-list" if "ta2:1071" in selected else "select-list-FAILED")
            page.locator("#btn-isolate").click()
            isolated=page.locator("#stat-nodes").inner_text()
            case["after_isolate"]=isolated
            case["verified_actions"].append("isolate" if isolated.startswith("1/") or isolated.startswith("1 /") else "isolate-FAILED")
            page.locator("#btn-reset-vis").click()
            restored=page.locator("#stat-nodes").inner_text()
            case["after_restore"]=restored
            case["verified_actions"].append("restore" if restored.startswith("26/") or restored.startswith("26 /") else "restore-FAILED")
            page.locator("#btn-focus").click()
            case["verified_actions"].append("focus-button-clicked")
            canvas=page.locator("#canvas").bounding_box()
            if canvas:
                page.mouse.move(canvas["x"]+canvas["width"]*0.5,canvas["y"]+canvas["height"]*0.4)
                page.mouse.down()
                page.mouse.move(canvas["x"]+canvas["width"]*0.6,canvas["y"]+canvas["height"]*0.5,steps=10)
                page.mouse.up()
                page.mouse.wheel(0,-120)
                case["verified_actions"].append("orbit-and-wheel-dispatched")
            case["stats"]=page.locator("#stat-tris").inner_text()
        elif case["ready"] and scene=="cube":
            case["stats"]=page.locator("#stat-tris").inner_text()
    except Exception as e:
        case["error"]=str(e)[:500]
    finally:
        context.close()
    return case

def main():
    httpd=http.server.ThreadingHTTPServer(("127.0.0.1",PORT),DualWasmHandler)
    t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
    report={"runner":"Playwright Chrome Headless actual browser", "tests":[],"limitations":["Headless WebGPU is not equivalent to user interactive browser on GPU","Clicks and mouse events do not validate touchscreen pinch gestures","No FPS benchmark implied by screenshots"]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=str(CHROME),headless=True,args=["--enable-unsafe-webgpu","--use-angle=d3d11","--disable-gpu-sandbox"])
            try:
                for backend,scene in [("webgl2","pelvis"),("auto","pelvis"),("webgl2","cube"),("webgpu","pelvis")]:
                    print("AUDIT_CASE",backend,scene,flush=True)
                    result=test_case(browser,backend,scene)
                    report["tests"].append(result)
                    print("RESULT",backend,scene,"ready",result["ready"],"active",result.get("backend_effective"),"actions",result["verified_actions"],flush=True)
            finally:
                browser.close()
    except Exception as e:
        report["runner_error"]=str(e)[:600]
    finally:
        httpd.shutdown()
    path=OUT/"browser-interactions.json"
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("AUDIT_REPORT",path,flush=True)

if __name__=="__main__":
    main()
