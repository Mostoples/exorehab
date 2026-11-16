"""Composite Blender RGBA frames over the brand background and encode web loops + stills.
usage: python tools/compose_loops.py [hero] [detail] [stills]"""
import glob, os, pathlib, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "blender" / "render"
OUTV = ROOT / "web" / "assets" / "video"; OUTV.mkdir(parents=True, exist_ok=True)
OUT3 = ROOT / "web" / "assets" / "3d"
FF = shutil.which("ffmpeg") or glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe"))[0]
BG = (233, 239, 247)

def backdrop(w, h, cx, cy):
    """Brand background with a soft white light pool and a faint blue aura behind the subject."""
    im = Image.new("RGB", (w, h), BG); d = ImageDraw.Draw(im)
    r = int(h * 0.62); d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(250, 252, 255))
    im = im.filter(ImageFilter.GaussianBlur(h * 0.18))
    m = Image.new("L", (w, h), 0); r2 = int(h * 0.30)
    ImageDraw.Draw(m).ellipse((cx - r2, cy - r2, cx + r2, cy + r2), fill=120)
    m = m.filter(ImageFilter.GaussianBlur(h * 0.16))
    return Image.composite(Image.new("RGB", (w, h), (214, 229, 252)), im, m)

def loop(name, src, cx=0.62, cy=0.5, crf=23):
    frames = sorted(glob.glob(str(R / src / "f_*.png")))
    assert frames, f"no frames in {src}"
    w, h = Image.open(frames[0]).size
    bg = backdrop(w, h, int(w * cx), int(h * cy)); bgp = R / f"_{name}_bg.png"; bg.save(bgp)
    out = OUTV / f"{name}_loop.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-loop", "1", "-i", str(bgp), "-framerate", "24", "-i", str(R / src / "f_%04d.png"),
                    "-filter_complex", "[0][1]overlay=shortest=1,format=yuv420p", "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
                    "-movflags", "+faststart", "-an", str(out)], check=True)
    mid = Image.open(frames[len(frames) // 4]).convert("RGBA"); base = bg.convert("RGBA"); base.alpha_composite(mid)
    base.convert("RGB").save(OUTV / f"{name}_poster.jpg", quality=86, optimize=True)
    print(name, out.stat().st_size // 1024, "KB", len(frames), "frames")

def still(src, dst, size=None, crop_square=False):
    im = Image.open(R / src).convert("RGBA")
    if crop_square:
        a = im.split()[3].point(lambda v: 255 if v > 20 else 0); x0, y0, x1, y1 = a.getbbox()
        s = max(x1 - x0, y1 - y0) + 60; cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        im = im.crop((cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2))
    if size: im.thumbnail((size, size), Image.LANCZOS)
    im.save(OUT3 / dst, "WEBP", quality=88, method=6); print(dst, im.size)

args = sys.argv[1:] or ["hero", "detail", "stills"]
if "hero" in args: loop("hero", "hero_light", 0.62, 0.5, 23)
if "detail" in args: loop("detail", "detail_light", 0.5, 0.5, 23)
if "stills" in args:
    if (R / "hand_detail.png").exists():
        im = Image.open(R / "hand_detail.png").convert("RGBA"); b = Image.new("RGBA", im.size, (250, 252, 255, 255)); b.alpha_composite(im)
        b.convert("RGB").resize((900, 900), Image.LANCZOS).save(OUT3 / "hand_detail.webp", "WEBP", quality=88, method=6); print("hand_detail.webp")
    if (R / "hand_grip.png").exists():
        im = Image.open(R / "hand_grip.png").convert("RGBA"); w, h = im.size
        im = im.crop((int(w * 0.30), 0, w, int(h * 0.92)))  # hand only, drop the torso
        m = Image.new("L", im.size, 0); cw, ch = im.size
        ImageDraw.Draw(m).ellipse((int(cw * 0.05), int(ch * 0.02), int(cw * 0.95), int(ch * 0.98)), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(cw * 0.08))
        a = Image.composite(im.split()[3], Image.new("L", im.size, 0), m); im.putalpha(a)
        im.thumbnail((1200, 1200), Image.LANCZOS); im.save(OUT3 / "hand_grip.webp", "WEBP", quality=88, method=6); print("hand_grip.webp", im.size)
