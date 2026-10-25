"""Export logo PNGs from brand/logo.html (transparent backgrounds)."""
import pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "logo"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1800, "height": 1400}, device_scale_factor=2)
    pg.goto((ROOT / "brand" / "logo.html").as_uri())
    pg.wait_for_timeout(600)
    if "--preview" in sys.argv:
        pg2 = b.new_page(viewport={"width": 1500, "height": 1200})
        pg2.goto((ROOT / "brand" / "logo.html").as_uri()); pg2.wait_for_timeout(500)
        pg2.evaluate("document.getElementById('mark').style.display='none'")
        pg2.screenshot(path=str(ROOT / "output" / "_preview_brand.png"), full_page=True)
    else:
        pg.locator("#mark").screenshot(path=str(OUT / "exorehab-mark-1024.png"), omit_background=True)
        pg.evaluate("document.getElementById('mark').style.display='none'")
        for i in ["lockup", "lockup-white", "stacked"]:
            pg.locator("#" + i).screenshot(path=str(OUT / f"exorehab-{i}.png"), omit_background=(i != "lockup-white"))
        for f in ["logo-mark.svg"]:
            (OUT / "exorehab-mark.svg").write_bytes((ROOT / "web" / "shared" / f).read_bytes())
    b.close()
print("ok")
