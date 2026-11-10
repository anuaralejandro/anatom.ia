#!/usr/bin/env python3
"""M05-A independent, nondestructive browser audit; Vite server must be running on port 3000.
No pass is inferred from a previous report. Chrome device emulation != iOS/Android hardware.
"""
from pathlib import Path
import json,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"reports"/"audit"/"m05a-independent-browser.json"
def check(ctx, url="http://127.0.0.1:3000/"):
    p=ctx.new_page()
    errors=[]
    p.on("pageerror",lambda e:errors.append(str(e)))
    p.goto(url,wait_until="domcontentloaded",timeout=20000)
    p.wait_for_selector(".atlas-stage",timeout=15000)
    return p,errors
results={"scope":"independent browser inspection on existing running Vite dev server","environment":"Chrome headless Windows; not native iOS, Android or Safari","checks":{}}
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
    try:
        # Desktop baseline and misleading backend badge.
        ctx=b.new_context(viewport={"width":1536,"height":960})
        p,errs=check(ctx)
        results["checks"]["desktop"] = p.evaluate("""() => ({
          layout:document.querySelector('.atlas-app').dataset.layout,
          stage:document.querySelector('.atlas-stage').getBoundingClientRect().toJSON(),
          canvas2d:!!document.querySelector('.atlas-canvas').getContext('2d'),
          headerBackendBadge:document.querySelector('.atlas-topbar-center')?.textContent.trim(),
          hasWebGpuContext:!!document.querySelector('.atlas-canvas').getContext('webgpu'),
          overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1
        })""")
        results["checks"]["desktop"]["pageErrors"]=errs
        ctx.close()
        # Reduced motion must not keep continuous frame loop.
        ctx=b.new_context(viewport={"width":390,"height":844},reduced_motion="reduce",is_mobile=True,has_touch=True)
        ctx.add_init_script("""(() => {window.__rafCount=0;const old=window.requestAnimationFrame.bind(window);window.requestAnimationFrame=cb=>old(ts=>{window.__rafCount++;cb(ts)});})();""")
        p,errs=check(ctx)
        p.wait_for_timeout(250)
        start=p.evaluate("window.__rafCount")
        p.wait_for_timeout(750)
        end=p.evaluate("window.__rafCount")
        sizes=p.evaluate("""() => ({
            topbar:[...document.querySelectorAll('.atlas-topbar button')].filter(e=>getComputedStyle(e).display!=='none').map(e=>({label:e.getAttribute('aria-label'),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,rect:e.getBoundingClientRect().toJSON()})),
            sheetHandle:document.querySelector('.atlas-sheet-handle-row')?.getBoundingClientRect().toJSON(),
            sheetButton:document.querySelector('.atlas-sheet button')?.getBoundingClientRect().toJSON(),
            camera:[...document.querySelectorAll('.atlas-camera-toolbar button')].map(e=>({label:e.getAttribute('aria-label'),w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height}))
        })""")
        results["checks"]["mobile_reduced_motion"]={"rafIn750ms":end-start,"touchTargets":sizes,"pageErrors":errs}
        # Test direct interaction on mobile: click sheet handle and compare state, then search.
        p.locator(".atlas-sheet-handle-row").click()
        expanded=p.locator(".atlas-sheet").get_attribute("style")
        results["checks"]["mobile_sheet"]={"afterClickStyle":expanded}
        ctx.close()
        # Laptop drawer keyboard trap, focus should not leak outside while modal opened.
        ctx=b.new_context(viewport={"width":1024,"height":768})
        p,errs=check(ctx)
        p.locator('button[aria-label="Abrir explorador"]').click()
        p.wait_for_selector(".atlas-drawer-left")
        focused_before=p.evaluate("document.activeElement?.outerHTML.slice(0,160)")
        for _ in range(12):p.keyboard.press("Tab")
        focused_after=p.evaluate("""() => ({
          tag:document.activeElement?.tagName,
          cls:document.activeElement?.className,
          insideDrawer:!!document.activeElement?.closest('.atlas-drawer-left'),
          outsideNavigation:!!document.activeElement?.closest('.atlas-topbar')
        })""")
        results["checks"]["drawer_focus"]={"initial":focused_before,"after12Tabs":focused_after,"pageErrors":errs}
        ctx.close()
        # Narrow landscape layout guard and touch target contract.
        ctx=b.new_context(viewport={"width":844,"height":390},is_mobile=True,has_touch=True)
        p,errs=check(ctx)
        results["checks"]["short_landscape"] = p.evaluate("""() => ({
          layout:document.querySelector('.atlas-app').dataset.layout,
          viewport:[innerWidth,innerHeight],
          stage:document.querySelector('.atlas-stage').getBoundingClientRect().toJSON(),
          horizontalOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1
        })""")
        results["checks"]["short_landscape"]["pageErrors"]=errs
        ctx.close()
    finally:b.close()
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
for k,v in results["checks"].items():print(k,json.dumps(v,ensure_ascii=False)[:460],flush=True)
print("SAVED",OUT,flush=True)
