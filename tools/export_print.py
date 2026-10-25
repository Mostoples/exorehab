"""Export print files: poster A0 (PDF + PNG) and trifold brochure (PDF + PNG per side).
usage: python tools/export_print.py [poster] [brochure] [--preview]"""
import pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
which = [a for a in sys.argv[1:] if not a.startswith("--")] or ["poster", "brochure"]
preview = "--preview" in sys.argv

with sync_playwright() as p:
    b = p.chromium.launch()
    if "poster" in which:
        pg = b.new_page(viewport={"width": 3179, "height": 4494}, device_scale_factor=1)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto((ROOT / "print" / "poster-a0.html").as_uri()); pg.wait_for_timeout(2500)
        print("poster overflow px:", pg.evaluate("document.body.scrollHeight - 4494"), errs)
        if preview:
            pg.screenshot(path=str(OUT / "_poster_full.png"))
        else:
            pg.screenshot(path=str(OUT / "ExoRehab_Poster_A0.png"))
            pg.pdf(path=str(OUT / "ExoRehab_Poster_A0.pdf"), width="841mm", height="1189mm", print_background=True)
    if "brochure" in which:
        pg = b.new_page(viewport={"width": 1123, "height": 794}, device_scale_factor=3)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto((ROOT / "print" / "brochure-trifold.html").as_uri()); pg.wait_for_timeout(2500)
        print("brochure errors:", errs)
        for i, side in enumerate(["outside", "inside"]):
            pg.locator(".sheet").nth(i).screenshot(path=str(OUT / f"{'_' if preview else ''}ExoRehab_Brochure_{side}.png"))
        if not preview:
            pg.pdf(path=str(OUT / "ExoRehab_Brochure_Trifold_A4.pdf"), width="297mm", height="210mm", print_background=True)
    b.close()
print("done")
