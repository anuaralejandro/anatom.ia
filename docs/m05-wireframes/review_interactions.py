from pathlib import Path
import json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent
url=(root/"index.html").as_uri()
g=(root/"gallery.html").as_uri()
results={}
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
 try:
  desktop=b.new_page(viewport={"width":1536,"height":960})
  desktop.goto(url)
  desktop.locator('[data-name="Próstata"]').first.click()
  results["desktop_selection"]=(desktop.locator("#inspectorName").inner_text()=="Próstata")
  desktop.locator('#anatomySearch').fill("vejiga")
  results["search_filters"]=(desktop.locator('.explorer-panel .anatomy-row:not([hidden])').count()==1)
  desktop.locator('[data-action="theme"]').first.click()
  results["theme_toggle"]=desktop.locator('html').get_attribute('data-theme')=='light'
  desktop.close()
  laptop=b.new_page(viewport={"width":1280,"height":800})
  laptop.goto(url)
  laptop.locator('.side-rail [data-action="inspector"]').click()
  results["laptop_inspector_open"]=laptop.locator('.atlas-app').get_attribute('data-inspector-open')=='true'
  laptop.keyboard.press("Escape")
  results["laptop_escape_close"]=laptop.locator('.atlas-app').get_attribute('data-inspector-open')=='false'
  laptop.close()
  phone=b.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
  phone.goto(url)
  phone.locator('.mobile-menu').click()
  results["phone_explorer_sheet"]=phone.locator('.atlas-app').get_attribute('data-sheet')=='mid' and phone.locator('.sheet-tab[data-sheet-tab="explorer"]').get_attribute('class').endswith('active')
  phone.locator('.sheet-content .anatomy-row[data-name="Vejiga urinaria"]').click()
  results["phone_selects_inspector"]=phone.locator('#sheetSelected').inner_text()=='Vejiga urinaria' and 'active' in (phone.locator('.sheet-tab[data-sheet-tab="inspector"]').get_attribute('class') or '')
  phone.locator(".sheet-handle").click()
  results["phone_sheet_expands"]=phone.locator('.atlas-app').get_attribute('data-sheet')=='max'
  phone.close()
  gallery=b.new_page(viewport={"width":1200,"height":800})
  gallery.goto(g)
  results["gallery_images_resolve"]=gallery.evaluate("()=>[...document.images].every(i=>i.complete&&i.naturalWidth>0)")
  gallery.close()
 finally:b.close()
out=root/"review"/"interactions-results.json"
out.write_text(json.dumps({"result":"PASS" if all(results.values()) else "FAIL","checks":results},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
for k,v in results.items(): print(("PASS" if v else "FAIL")+" "+k)
print("M05_MOCK_INTERACTIONS", "PASS" if all(results.values()) else "FAIL")
