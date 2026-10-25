import pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type=="error" and errs.append(m.text))
    pg.goto((ROOT/"web"/"app.html").as_uri()+"?rec"); pg.wait_for_timeout(500)
    for i,s in enumerate(["home","session","progress","monitor","device"]):
        pg.evaluate(f"APP.go('{s}');APP.setTime(5.3)"); pg.wait_for_timeout(150)
        pg.screenshot(path=str(ROOT/"output"/f"_app_{i}.png"), full_page=True)
    print("errors:", errs); b.close()
