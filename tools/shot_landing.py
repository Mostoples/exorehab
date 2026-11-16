import pathlib, sys
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[1]
w = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": w, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto((ROOT / "web" / "index.html").as_uri() + "?static"); pg.wait_for_timeout(1200)
    H = pg.evaluate("document.documentElement.scrollHeight")
    for y in range(0, H, 700): pg.evaluate(f"scrollTo(0,{y})"); pg.wait_for_timeout(120)
    pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(1500)
    out = ROOT / "output" / f"_landing_{w}.png"; pg.screenshot(path=str(out), full_page=True)
    print("errors:", errs, "scrollW", pg.evaluate("document.documentElement.scrollWidth")); b.close()
im = Image.open(out); print(im.size)
cols = 2; ch = (im.height + cols - 1) // cols
s = Image.new("RGB", (im.width * cols + 20, ch), "white")
for i in range(cols): s.paste(im.crop((0, i * ch, im.width, min(im.height, (i + 1) * ch))), (i * (im.width + 20), 0))
s.thumbnail((1000 if w > 600 else 700, 2000)); s.save(ROOT / "output" / f"_lsheet_{w}.jpg", quality=85); print(s.size)
