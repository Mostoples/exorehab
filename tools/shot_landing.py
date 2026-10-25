import pathlib, sys
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[1]
w = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":w,"height":900})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto((ROOT/"web"/"index.html").as_uri()+"?static"); pg.wait_for_timeout(1500)
    out = ROOT/"output"/f"_landing_{w}.png"; pg.screenshot(path=str(out), full_page=True)
    print("errors:", errs, "scrollW", pg.evaluate("document.documentElement.scrollWidth")); b.close()
im = Image.open(out); print(im.size)
# split into tiles for review
n = 0
for y in range(0, im.height, 1800):
    im.crop((0,y,im.width,min(im.height,y+1800))).resize((im.width//2, (min(im.height,y+1800)-y)//2)).save(ROOT/"output"/f"_l{w}_{n}.png"); n+=1
print(n)
