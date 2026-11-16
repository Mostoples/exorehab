"""Exolution 3D-character showreel: Blender shots + title cards + crossfades + synth music → MP4.
usage: python video/build_reel3d.py"""
import importlib.util, json, pathlib, shutil, subprocess, urllib.parse
from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "blender" / "render"; W = ROOT / "web"; T = ROOT / "output" / "_reel3d"; T.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("cl", ROOT / "tools" / "compose_loops.py"); CL = importlib.util.module_from_spec(spec)
import sys; argv = sys.argv; sys.argv = [argv[0], "none"]; spec.loader.exec_module(CL); sys.argv = argv
FF = CL.FF; FPS = 24; XF = 0.6

CARDS = {
    "A": dict(chip="Meet Exolution", l1="A smart hand", l2="exoskeleton.", p="3D-printed, heat-moulded to each patient, worn at home."),
    "B": dict(chip="Assist-as-needed", l1="Helps the hand", l2="open again.", p="Hinged finger rings and elastic cords support every repetition."),
    "C": dict(chip="AI adaptive", l1="Help that fades", l2="as strength returns.", p="Edge AI on an ESP32 reads effort and tunes the assistance.", right=True),
    "D": dict(chip="Sustainable build", l1="Five printed parts,", l2="one wearable hand.", p="Recycled PETG, print-in-place hinges, repair one part, not all."),
    "E": dict(chip="Wear it at home", l1="Therapy beyond", l2="the clinic.", p="Light enough for daily practice, between therapist visits."),
    "F": dict(chip="Real-time IoT", l1="Every session,", l2="live and shared.", p="Repetitions, effort and alerts stream to the family and therapist."),
}

def cards():
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
        base = (ROOT / "video" / "cards.html").as_uri()
        for name, spec_ in [("intro", {"kind": "intro"}), ("outro", {"kind": "outro"})] + [(k, v) for k, v in CARDS.items()]:
            pg.goto(base + "#" + urllib.parse.quote(json.dumps(spec_))); pg.reload(); pg.wait_for_timeout(1200)
            pg.screenshot(path=str(T / f"card_{name}.png"), omit_background=name not in ("intro", "outro"))
        # app phones (rec mode = deterministic data)
        ph = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        for scr, t in (("session", 7.3), ("progress", 6), ("monitor", 6)):
            ph.goto((W / "app.html").as_uri() + f"?rec&screen={scr}&t={t}"); ph.wait_for_timeout(700)
            ph.screenshot(path=str(T / f"app_{scr}.png"))
        b.close()

def phone(img, w=430):
    s = Image.open(img).convert("RGB"); h = int(w * s.height / s.width); s = s.resize((w - 28, h - 28), Image.LANCZOS)
    fr = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(fr)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 62, fill=(248, 250, 254, 255), outline=(255, 255, 255, 255), width=2)
    m = Image.new("L", s.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, s.width - 1, s.height - 1), 50, fill=255)
    fr.paste(s, (14, 14), m)
    ImageDraw.Draw(fr).rounded_rectangle((w // 2 - 58, 30, w // 2 + 58, 58), 14, fill=(22, 35, 63, 255))
    return fr

def stills():
    bg = CL.backdrop(1920, 1080, 960, 540)
    # parts flat-lay
    im = bg.convert("RGBA"); fl = Image.open(W / "assets" / "3d" / "parts_flatlay.png").convert("RGBA"); fl.thumbnail((1500, 940))
    im.alpha_composite(fl, (1920 - fl.width - 40, (1080 - fl.height) // 2 - 40)); im.convert("RGB").save(T / "still_parts.png")
    # app phones
    im = CL.backdrop(1920, 1080, 1460, 540).convert("RGBA")
    for i, (scr, x, y) in enumerate((("monitor", 1240, 60),)):
        p = phone(T / f"app_{scr}.png", 440)
        sh = Image.new("RGBA", (p.width + 120, p.height + 120), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((60, 80, p.width + 60, p.height + 60), 60, fill=(30, 70, 160, 90))
        sh = sh.filter(ImageFilter.GaussianBlur(30)); im.alpha_composite(sh, (x - 60, y - 40)); im.alpha_composite(p, (x, y))
    im.convert("RGB").save(T / "still_app.png")
    for n in ("raise", "turn"):
        CL.backdrop(1600, 900, 800 if n == "turn" else 980, 450).save(T / f"bg_{n}.png")

def card_filter(src, card, dur, label="v"):
    """[src] + card → fade/slide-in lower third."""
    a, b_ = 0.7, dur - 0.9
    return (f"[{card}]format=rgba,fade=in:st={a}:d=0.5:alpha=1,fade=out:st={b_}:d=0.5:alpha=1[c{label}];"
            f"[{src}][c{label}]overlay=x=0:y='40*(1-min(max((t-{a})/0.7,0),1))':shortest=1[{label}]")

def clip(name, dur, kind, src, card=None):
    out = T / f"clip_{name}.mp4"
    base = ["-y", "-loglevel", "error"]
    if kind == "seq":    # RGBA frames over backdrop
        inp = ["-loop", "1", "-i", str(T / f"bg_{src}.png"), "-framerate", str(FPS), "-i", str(R / f"shot_{src}" / "f_%04d.png")]
        f = "[0][1]overlay=shortest=1,scale=1920:1080:flags=lanczos,setsar=1[s]"
    elif kind == "vid":
        inp = ["-stream_loop", "3", "-i", str(src)]
        f = "[0]scale=1920:1080:flags=lanczos,setsar=1,fps=24[s]"
    else:                # still with a slow push-in
        n = int(dur * FPS)
        inp = ["-loop", "1", "-i", str(src)]
        f = f"[0]scale=3840:-1,zoompan=z='1+0.07*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1920x1080:fps={FPS},setsar=1[s]"
    if card:
        inp += ["-loop", "1", "-i", str(T / f"card_{card}.png")]
        f += ";" + card_filter("s", f"{len([x for x in inp if x == '-i']) - 1}", dur)
        last = "v"
    else:
        last = "s"
    subprocess.run([FF, *base, *inp, "-filter_complex", f, "-map", f"[{last}]", "-t", str(dur), "-r", str(FPS),
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out, dur

def music(total):
    spec2 = importlib.util.spec_from_file_location("sr", ROOT / "video" / "build_showreel.py"); SR = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(SR); SR.DUR = int(total) + 1; SR.music(T / "music.wav")

if __name__ == "__main__":
    cards(); stills()
    plan = [clip("intro", 3.6, "still", T / "card_intro.png"),
            clip("A", 6.0, "seq", "raise", "A"),
            clip("B", 5.0, "vid", W / "assets" / "video" / "detail_loop.mp4", "B"),
            clip("C", 5.0, "vid", W / "assets" / "video" / "hero_loop.mp4", "C"),
            clip("D", 4.6, "still", T / "still_parts.png", "D"),
            clip("E", 5.0, "seq", "turn", "E"),
            clip("F", 4.8, "still", T / "still_app.png", "F"),
            clip("outro", 6.0, "still", T / "card_outro.png")]
    inputs, fc, prev, off = [], [], "0:v", 0.0
    for i, (p, d) in enumerate(plan):
        inputs += ["-i", str(p)]
        if i == 0: off = d - XF; continue
        lab = f"x{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition={'fadewhite' if i in (1, 7) else 'smoothleft' if i % 2 else 'fade'}:duration={XF}:offset={off:.3f}[{lab}]")
        prev = lab; off += d - XF
    total = off + XF
    music(total)
    out = ROOT / "output" / "Exolution_Showreel_3D_1080p.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", *inputs, "-i", str(T / "music.wav"), "-filter_complex", ";".join(fc) + f";[{len(plan)}:a]atrim=0:{total:.3f},afade=t=out:st={total - 2.5:.3f}:d=2.5,loudnorm=I=-17:TP=-1.5[a]",
                    "-map", f"[{prev}]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    vdir = W / "assets" / "video"; web = vdir / "showreel.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(out), "-vf", "scale=1280:-2", "-c:v", "libx264", "-crf", "24", "-preset", "slow",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(web)], check=True)
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", "10", "-i", str(out), "-frames:v", "1", "-vf", "scale=1280:-2", str(vdir / "showreel_poster.jpg")], check=True)
    print("done", out, round(total, 1), "s", out.stat().st_size // 1024, "KB; web", web.stat().st_size // 1024, "KB")
