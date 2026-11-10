#!/usr/bin/env python
"""Design-only viewport and interaction QA. Chrome emulation != physical iOS/Android approval."""
import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
URL=(ROOT/"index.html").resolve().as_uri()
OUT=ROOT/"review";OUT.mkdir(exist_ok=True)
SIZES={
"desktop-pro":(1536,960),"macbook":(1280,800),
"ipad-portrait":(834,1194),"iphone-portrait":(390,844),
"iphone-landscape":(844,390),"ipad-landscape":(1194,834),
"android-compact":(360,800),"small-phone":(320,568),
"split-view":(600,800),"laptop-height":(1440,650),
"desktop-wide":(1920,1080),"tablet-1024":(1024,768)
}
CANDIDATE=["selected","empty","loading","error"]
summary={"status":"PENDING","cases":[],"limitations":["Chrome Windows headless emulation only","3D illustration is original and conceptual; no clinical geometry","No iOS Safari / Android Chrome native verification"]}
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
    try:
        for label,(width,height) in SIZES.items():
            ctx=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1)
            page=ctx.new_page()
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL+"?capture=1&state=selected",wait_until="load")
            page.wait_for_function("Boolean(window.__m05Preview)")
            metrics=page.evaluate("""() => {
               const root=document.querySelector('.atlas-app');
               const stage=document.querySelector('.viewport').getBoundingClientRect();
               const body=document.documentElement;
               const layout=root.dataset.layout;
               const explorer=document.querySelector('.explorer-panel');
               const inspector=document.querySelector('.inspector-panel');
               const visible=e=>getComputedStyle(e).display!=='none';
               const buttons=[...document.querySelectorAll('.topbar .icon-btn')].filter(visible);
               return {layout,stageWidth:stage.width,stageHeight:stage.height,
                 docWidth:body.scrollWidth,clientWidth:body.clientWidth,
                 explorerVisible:visible(explorer),inspectorVisible:visible(inspector),
                 topbarControls:buttons.map(b=>({label:b.getAttribute('aria-label'),width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height})),
                 illustrationOnly:window.__m05Preview.illustrationOnly,
                 engineInstantiated:window.__m05Preview.engineInstantiated
               }
            }""")
            expected="pro-wide" if width>=1536 and height>=650 else "workstation" if width>=1120 and width-352>=640 and height>=500 else "tablet" if width>=840 and height>=500 else "compact-wide" if width>=600 else "compact"
            if height<500:expected="compact" if width<600 else "compact-wide"
            result={
                "name":label,"viewport":[width,height],"expectedLayout":expected,
                "metrics":metrics,"errors":errors,
                "checks":{
                    "layout":metrics["layout"]==expected,
                    "noHorizontalOverflow":metrics["docWidth"]<=metrics["clientWidth"]+1,
                    "stageNotCollapsed":metrics["stageWidth"]>= min(width,320) and metrics["stageHeight"]>180,
                    "fixedExplorerOnlyWhereExpected":metrics["explorerVisible"]==(expected in ("workstation","pro-wide")),
                    "fixedInspectorOnlyOnPro":metrics["inspectorVisible"]==(expected=="pro-wide"),
                    "prototypeNotUsingEngine":metrics["illustrationOnly"] and not metrics["engineInstantiated"],
                    "noJsErrors":not errors,
                }
            }
            if label in ("desktop-pro","macbook","ipad-portrait","iphone-portrait","ipad-landscape","iphone-landscape"):
                path=OUT/f"{label}-selected-dark.png"
                page.screenshot(path=str(path),animations="disabled")
                result["screenshot"]=str(path)
            if label in ("desktop-pro","iphone-portrait"):
                page.goto(URL+"?capture=1&theme=light&state=selected",wait_until="load")
                page.screenshot(path=str(OUT/f"{label}-selected-light.png"),animations="disabled")
                for state in ("loading","error"):
                    page.goto(URL+f"?capture=1&state={state}",wait_until="load")
                    page.screenshot(path=str(OUT/f"{label}-{state}-dark.png"),animations="disabled")
                if label=="iphone-portrait":
                    page.goto(URL+"?capture=1&sheet=max",wait_until="load")
                    page.screenshot(path=str(OUT/"iphone-portrait-sheet-expanded.png"),animations="disabled")
            if label in ("ipad-portrait","macbook"):
                page.goto(URL+"?capture=1&panel=inspector",wait_until="load")
                page.screenshot(path=str(OUT/f"{label}-inspector-open.png"),animations="disabled")
            result["status"]="PASS" if all(result["checks"].values()) else "FAIL"
            summary["cases"].append(result)
            print(f'{label:<20} {result["status"]:<5} {metrics["layout"]:<13} stage={metrics["stageWidth"]:.0f}x{metrics["stageHeight"]:.0f}',flush=True)
            ctx.close()
    finally:
        browser.close()
summary["status"]="PASS" if all(x["status"]=="PASS" for x in summary["cases"]) else "FAIL"
(OUT/"design-review-results.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("DESIGN_REVIEW",summary["status"],len(summary["cases"]),flush=True)
sys.exit(0 if summary["status"]=="PASS" else 1)
