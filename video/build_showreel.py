"""Render the ExoRehab showreel: reel.html frames (Playwright) + synth music (numpy) -> MP4 (FFmpeg).
usage: python video/build_showreel.py [--preview t1,t2,...] [--fps 30]"""
import glob, http.server, os, pathlib, shutil, socketserver, subprocess, sys, threading, wave
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"; FR = OUT / "_frames"
FPS = int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 30
DUR = 63
FF = shutil.which("ffmpeg") or (glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe")) or ["ffmpeg"])[0]

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
def serve():
    h = lambda *a, **k: Q(*a, directory=str(ROOT), **k)
    s = socketserver.TCPServer(("127.0.0.1", 0), h); threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, s.server_address[1]

def render(times, prefix):
    srv, port = serve()
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(f"http://127.0.0.1:{port}/video/reel.html"); pg.wait_for_timeout(2500)
        for i, t in enumerate(times):
            pg.evaluate(f"setTime({t})")
            pg.screenshot(path=str(prefix(i, t)), type="jpeg", quality=93)
            if i % 150 == 0: print("frame", i, "/", len(times), flush=True)
        b.close()
    srv.shutdown()

def music(path):
    sr = 44100; n = int(sr * DUR); t = np.arange(n) / sr; out = np.zeros(n)
    bpm = 96; beat = 60 / bpm; bar = 4 * beat
    f = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [[48, 55, 64, 71], [45, 52, 60, 67], [41, 48, 57, 64], [43, 50, 59, 62]]  # Cmaj7 Am7 Fmaj7 G6
    for bi in range(int(DUR / bar) + 1):
        ch = chords[bi % 4]; s0 = int(bi * bar * sr); s1 = min(n, int((bi + 1) * bar * sr + sr * .6))
        if s0 >= n: break
        tt = np.arange(s1 - s0) / sr; env = np.minimum(1, tt / .8) * np.exp(-tt / 9)
        for m in ch:
            for det in (-.08, .08):
                out[s0:s1] += .035 * env * np.sin(2 * np.pi * f(m + det) * tt + np.sin(2 * np.pi * .3 * tt))
        # pluck arpeggio from bar 1
        if bi >= 1:
            for k in range(8):
                st = int(s0 + k * beat / 2 * sr); L = int(sr * .5)
                if st + L > n: break
                m = ch[[0, 2, 1, 3, 2, 3, 1, 2][k]] + 12; tl = np.arange(L) / sr
                out[st:st + L] += .05 * np.exp(-tl * 7) * (np.sin(2 * np.pi * f(m) * tl) + .3 * np.sin(4 * np.pi * f(m) * tl))
        # soft kick + hat from bar 2
        if 2 <= bi < int(DUR / bar) - 1:
            for k in range(4):
                st = int(s0 + k * beat * sr); L = int(sr * .25); tl = np.arange(L) / sr
                if st + L > n: break
                out[st:st + L] += .22 * np.exp(-tl * 18) * np.sin(2 * np.pi * (50 + 80 * np.exp(-tl * 30)) * tl)
                hs = int(st + beat / 2 * sr); hl = int(sr * .05)
                if hs + hl < n: out[hs:hs + hl] += .025 * np.exp(-np.arange(hl) / sr * 80) * np.random.default_rng(k + bi).standard_normal(hl)
    fade = np.ones(n); fi = int(sr * 1.5); fo = int(sr * 3)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
    out *= fade; out /= np.max(np.abs(out)) * 1.1
    st = np.stack([out, np.roll(out, 300)], 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes((st * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    if "--preview" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        render(ts, lambda i, t: OUT / f"_reel_{t:05.1f}.jpg"); sys.exit()
    FR.mkdir(exist_ok=True)
    for old in FR.glob("*.jpg"): old.unlink()
    render([i / FPS for i in range(DUR * FPS)], lambda i, t: FR / f"f_{i:05d}.jpg")
    music(OUT / "_music.wav")
    mp4 = OUT / "ExoRehab_Showreel_1080p.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(FR / "f_%05d.jpg"), "-i", str(OUT / "_music.wav"),
                    "-af", "loudnorm=I=-17:TP=-1.5", "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)], check=True)
    web = ROOT / "web" / "assets"; web.mkdir(exist_ok=True)
    shutil.copy(mp4, web / "exorehab-showreel.mp4")
    shutil.copy(FR / f"f_{int(2.6 * FPS):05d}.jpg", web / "reel-poster.jpg")
    print("done", mp4)
