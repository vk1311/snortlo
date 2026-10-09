"""Long-form "stories to fall asleep to" renderer (YouTube / Facebook, 30-90 min).

    cd engine && python3 longform.py ../longform/<slug>.json ../media/long-<slug>.mp4 [--keep]

Input JSON:
    {"title": "...", "voice": "af_heart", "speed": 0.92, "intro": "text",
     "stories": [{"title": "...", "text": "paragraphs separated by blank lines"}],
     "outro": "text",
     # optional: "thumb_title": "SLEEPY STORIES", "thumb_subtitle": "...",
     #           "announce": true (narrate "Story two. <title>."), "rain": true}

Writes <out>.mp4 (1920x1080 H.264 + AAC, ~-18 LUFS), <out-stem>.chapters.txt and <out-stem>-thumb.png.

How it stays fast and small on a 2-core box:
  audio  - Kokoro TTS per sentence (2 worker processes, cached on disk), streamed to FLAC;
           ambient bed (rain + slow pad) synthesized in 30 s blocks and mixed while streaming;
           EBU R128 measurement + one linear gain (and a safety limiter) to -18 LUFS.
  video  - one seamless 60 s cairo loop is rendered once (lossless master), cut into 10 s
           sub-clips and encoded once each. The full timeline is a concat (stream copy) of those
           sub-clips; only the few sub-clips under a title card are re-encoded with the card
           overlaid. An hour of video costs ~1 minute of encoding.
"""
import hashlib, json, math, os, re, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, lfilter_zi
import cairocffi as cairo

from anim import rrect, line, text, hexc
import anim as _A
# softer outlines than the shorts: a muted lavender ink and ~30% thinner lines (owner feedback, Oct 8)
INKC = hexc("#4D4768")
def fill_stroke(c, fill, stroke=None, lw=8):
    _A.fill_stroke(c, fill, INKC if stroke is not None else None, lw * 0.7)

SR = 24000                 # Kokoro native rate; the mix is resampled to 48 kHz at the end
W, H = 1920, 1080
FPS = 15
LOOP = 60                  # seconds; every animation is periodic in LOOP -> seamless
SUB = 10                   # sub-clip length (s); LOOP must be a multiple
PAUSE_SENT, PAUSE_PARA, PAUSE_STORY = 0.45, 1.3, 4.0
CARD_LEN, CARD_FADE = 7.0, 1.2
TARGET_LUFS = -18.0
X264 = ["-c:v", "libx264", "-preset", "veryfast", "-tune", "animation", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(SUB * FPS), "-keyint_min", str(SUB * FPS),
        "-sc_threshold", "0", "-bf", "2", "-an"]

def log(*a): print(f"[longform {time.strftime('%H:%M:%S')}]", *a, flush=True)

def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *map(str, args)], check=True)

def nfrm(sec): return int(round(sec * FPS))

# ====================================================================== text
NUMW = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
       "sixteen seventeen eighteen nineteen twenty".split()
def numword(n):
    if n < len(NUMW): return NUMW[n]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty"][n // 10]
    return tens + ("-" + NUMW[n % 10] if n % 10 else "")

def clean(s):
    s = s.replace("…", "...").replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", s).strip()

def sentences(para):
    parts = re.split(r'(?<=[.!?])\s+|(?<=[.!?]["\')])\s+', clean(para))
    out = []
    for p in parts:
        p = p.strip()
        if not p: continue
        while len(p) > 320:                       # very long sentence: split at a comma/semicolon near the middle
            cuts = [m.end() for m in re.finditer(r"[,;:]\s", p)]
            if not cuts: break
            c = min(cuts, key=lambda x: abs(x - len(p) / 2)); out.append(("sub", p[:c].strip())); p = p[c:].strip()
        out.append(("sent", p))
    return out

def display_title(s):
    """Text for on-screen cards: cut at the first emoji or ' | ' (YouTube-style titles), drop odd glyphs."""
    s = re.split(r"\s\|\s|[\U0001F000-\U0001FFFF\u2600-\u27BF]", s)[0]
    return re.sub(r"\s+", " ", s).strip(" -:·")

def paragraphs(txt):
    return [p for p in re.split(r"\n\s*\n", txt or "") if p.strip()]

# ====================================================================== TTS (2 workers, disk cache)
_K = None
def _init_worker():
    global _K
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.inter_op_num_threads = 1
    sess = ort.InferenceSession("models/kokoro-v1.0.onnx", so, providers=["CPUExecutionProvider"])
    _K = Kokoro.from_session(sess, "models/voices-v1.0.bin")

def _tts(job):
    path, txt, voice, speed = job
    if os.path.exists(path): return path
    s, _ = _K.create(txt, voice=voice, speed=speed, lang="en-us")
    s = np.asarray(s, np.float32)
    nz = np.where(np.abs(s) > 0.008)[0]
    if len(nz): s = s[max(nz[0] - int(.04 * SR), 0): nz[-1] + int(.15 * SR)]
    f = min(len(s) // 2, int(.012 * SR))         # 12 ms fades: no clicks at chunk edges
    if f:
        s[:f] *= np.linspace(0, 1, f, dtype=np.float32); s[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    np.save(path + ".tmp.npy", s); os.replace(path + ".tmp.npy", path)
    return path

# ====================================================================== audio synthesis
def chime():
    """Soft two-note bell, ~2.8 s, very quiet (peak ~0.1)."""
    n = int(2.8 * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for f0, t0, a0 in ((783.99, 0.0, 1.0), (587.33, 0.42, 0.8)):
        tt = np.clip(t - t0, 0, None); on = (t >= t0)
        for ratio, amp, tau in ((1, 1, 1.1), (2.01, .22, .5), (2.76, .10, .35), (4.07, .04, .2)):
            out += on * a0 * amp * np.sin(2 * np.pi * f0 * ratio * tt) * np.exp(-tt / tau) * np.minimum(tt / .008, 1)
    out *= np.minimum(1, (t[-1] - t) / 0.6)            # fade to silence inside the block
    return (out / np.abs(out).max() * 0.10).astype(np.float32)

# ---- tiny, sleep-safe room sounds: slow attacks, low-passed, very quiet, sparse (one every ~40-90 s)
def _env(n, att, rel):
    t = np.arange(n) / SR; e = np.minimum(1, t / att) * np.minimum(1, (t[-1] - t) / rel)
    return np.clip(e, 0, 1)

def _lp(x, f):
    b, a = butter(2, f / (SR / 2), "low"); return lfilter(b, a, x)

def snd_windchime(rng):
    n = int(4.5 * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for k in range(rng.integers(2, 5)):
        f = rng.choice([1046.5, 1174.7, 1318.5, 1568.0, 1760.0]); t0 = rng.uniform(0, 1.6); tt = np.clip(t - t0, 0, None)
        out += (t >= t0) * np.sin(2 * np.pi * f * tt) * np.exp(-tt / 1.4) * np.minimum(tt / .03, 1) * rng.uniform(.5, 1)
    return _lp(out, 2600) * _env(n, .05, 1.0) * 0.022

def snd_owl(rng):
    out = []
    for f, d in ((392, .55), (0, .25), (370, .9)):
        n = int(d * SR); t = np.arange(n) / SR
        out.append(np.zeros(n) if not f else (np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)) * _env(n, .18, .3))
    return _lp(np.concatenate(out), 1200) * 0.016

def snd_purr(rng):
    n = int(3.2 * SR); t = np.arange(n) / SR
    x = _lp(rng.standard_normal(n), 220) * (0.55 + 0.45 * np.sin(2 * np.pi * 24 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * .7 * t))
    return x / (np.abs(x).max() + 1e-9) * _env(n, .8, 1.0) * 0.03

def snd_page(rng):
    n = int(0.9 * SR); t = np.arange(n) / SR
    b, a = butter(2, [900 / (SR / 2), 3800 / (SR / 2)], "band")
    x = lfilter(b, a, rng.standard_normal(n)) * np.sin(np.pi * t / t[-1]) ** 2
    return x / (np.abs(x).max() + 1e-9) * 0.018

def snd_thunder(rng):
    n = int(6 * SR); t = np.arange(n) / SR
    x = _lp(rng.standard_normal(n), 110) * np.sin(np.pi * t / t[-1]) ** 3
    return x / (np.abs(x).max() + 1e-9) * 0.05

def snd_spoon(rng):
    n = int(1.2 * SR); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / .25) for f in (2350, 3120)) * np.minimum(t / .004, 1)
    return _lp(x, 3000) * 0.008

ROOM_SOUNDS = [snd_windchime, snd_owl, snd_purr, snd_page, snd_spoon, snd_thunder]

class Bed:
    """Rain (filtered noise, stereo-decorrelated, slow swells) + very soft two-chord pad.
    Generated block by block with carried filter state, so any length costs O(block) memory."""
    def __init__(self, total, rain=True, seed=11):
        self.total, self.rain, self.rng = total, rain, np.random.default_rng(seed)
        self.bb, self.ba = butter(2, [350 / (SR / 2), 5200 / (SR / 2)], "band")
        self.lb, self.la = butter(1, 180 / (SR / 2), "low")
        self.pb, self.pa = butter(2, 1400 / (SR / 2), "low")
        zb, zl, zp = lfilter_zi(self.bb, self.ba), lfilter_zi(self.lb, self.la), lfilter_zi(self.pb, self.pa)
        self.zb = [zb * 0, zb * 0]; self.zl = [zl * 0, zl * 0]; self.zp = zp * 0
        er = np.random.default_rng(seed + 1); self.events, at = [], 25.0
        while at < total - 20:
            fn = ROOM_SOUNDS[er.integers(len(ROOM_SOUNDS) - (0 if rain else 1))]
            x = fn(er).astype(np.float64); pan = er.uniform(.3, .7)
            self.events.append((int(at * SR), np.stack([x * (1 - pan) * 1.4, x * pan * 1.4], 1)))
            at += er.uniform(40, 90)
        self.chA = [146.83, 220.00, 277.18, 329.63]          # Dmaj7-ish
        self.chB = [123.47, 185.00, 246.94, 293.66]          # Bm

    def block(self, i0, n):
        t = (i0 + np.arange(n)) / SR
        out = np.zeros((n, 2))
        if self.rain:
            swell = 0.82 + 0.10 * np.sin(2 * np.pi * t / 47) + 0.08 * np.sin(2 * np.pi * t / 29 + 1.3)
            for ch in range(2):
                w = self.rng.standard_normal(n)
                hiss, self.zb[ch] = lfilter(self.bb, self.ba, w, zi=self.zb[ch])
                drops = np.zeros(n); k = self.rng.poisson(90 * n / SR)
                drops[self.rng.integers(0, n, k)] = self.rng.exponential(1.0, k) * self.rng.choice([-1, 1], k)
                drops, _ = lfilter(self.bb, self.ba, drops, zi=self.zb[ch] * 0)
                rumble, self.zl[ch] = lfilter(self.lb, self.la, self.rng.standard_normal(n), zi=self.zl[ch])
                out[:, ch] = ((hiss * 0.060 + drops * 0.035) * swell + rumble * 0.18) * 0.19
        wa = 0.5 + 0.5 * np.cos(2 * np.pi * t / 96)
        pad = np.zeros(n)
        for chord, wgt in ((self.chA, wa), (self.chB, 1 - wa)):
            for f in chord:
                v = np.sin(2 * np.pi * (f - .06) * t) + np.sin(2 * np.pi * (f + .06) * t) + .25 * np.sin(2 * np.pi * 2 * f * t)
                pad += v * wgt
        pad, self.zp = lfilter(self.pb, self.pa, pad, zi=self.zp)
        pad *= 0.0019
        out[:, 0] += pad; out[:, 1] += pad
        for st, x in self.events:   # sparse room sounds that overlap this block
            a, b = max(st, i0), min(st + len(x), i0 + n)
            if a < b: out[a - i0:b - i0] += x[a - st:b - st]
        fade = np.minimum(1, np.minimum(t / 6.0, (self.total - t) / 9.0)).clip(0, 1)
        return out * fade[:, None]

# ====================================================================== scene (cairo)
WIN = (540, 140, 760, 560)       # window x, y, w, h (glass area)
SKY_TOP, SKY_BOT = hexc("#0E1433"), hexc("#2A3466")

def _rng_list(n, seed, f):
    r = np.random.default_rng(seed); return [f(r) for _ in range(n)]

STARS = _rng_list(70, 3, lambda r: (r.uniform(0, 1), r.uniform(0, .62), r.uniform(.8, 2.4), int(r.integers(1, 6)), r.uniform(0, 6.28)))
BIGSTARS = [(.13, .14, 2, 0.3), (.47, .08, 3, 2.1), (.83, .30, 1, 4.0), (.30, .40, 2, 1.0), (.64, .20, 1, 5.2)]
CLOUDS = [(0.0, 120, 1.0, 1), (0.37, 250, 0.8, 1), (0.66, 70, 1.25, 1)]   # phase, y, scale, laps per loop
RAIN = _rng_list(80, 5, lambda r: (r.uniform(0, 1), r.uniform(0, 1), r.uniform(18, 46), int(r.integers(22, 34)), r.uniform(.10, .26)))
FAIRY = 15

def _cloud(c, x, y, s, col):
    c.set_source_rgba(*col)
    for dx, dy, r in ((0, 0, 46), (52, -22, 58), (112, -4, 50), (160, 8, 38), (64, 14, 44), (-40, 12, 32)):
        c.new_path(); c.arc(x + dx * s, y + dy * s, r * s, 0, 2 * math.pi); c.fill()

def draw_sky(c, t, rain=True):
    """Everything seen through the glass. Periodic in LOOP."""
    x0, y0, w, h = WIN
    c.save(); c.rectangle(x0, y0, w, h); c.clip()
    g = cairo.LinearGradient(0, y0, 0, y0 + h); g.add_color_stop_rgb(0, *SKY_TOP); g.add_color_stop_rgb(1, *SKY_BOT)
    c.set_source(g); c.paint()
    ph = 2 * math.pi * t / LOOP
    for (u, v, r, k, p) in STARS:
        a = 0.45 + 0.4 * math.sin(k * ph + p)
        c.set_source_rgba(1, .96, .85, a); c.new_path(); c.arc(x0 + u * w, y0 + v * h, r, 0, 2 * math.pi); c.fill()
    for (u, v, k, p) in BIGSTARS:
        s = 7 + 3.5 * math.sin(k * ph + p); x, y = x0 + u * w, y0 + v * h
        c.set_source_rgba(1, .93, .7, .85); c.new_path()
        c.move_to(x, y - s); c.line_to(x + s * .25, y - s * .25); c.line_to(x + s, y); c.line_to(x + s * .25, y + s * .25)
        c.line_to(x, y + s); c.line_to(x - s * .25, y + s * .25); c.line_to(x - s, y); c.line_to(x - s * .25, y - s * .25)
        c.close_path(); c.fill()
    # moon with halo
    mx, my = x0 + w * .72, y0 + h * .27
    halo = cairo.RadialGradient(mx, my, 40, mx, my, 230)
    halo.add_color_stop_rgba(0, 1, .95, .78, .30); halo.add_color_stop_rgba(1, 1, .95, .78, 0); c.set_source(halo); c.paint()
    c.new_path(); c.arc(mx, my, 62, 0, 2 * math.pi); c.set_source_rgb(*hexc("#FFF3C9")); c.fill()
    c.set_source_rgba(*hexc("#E9D9A6"), .8)
    for dx, dy, r in ((-18, -14, 11), (20, 8, 15), (-6, 26, 7), (26, -24, 6)):
        c.new_path(); c.arc(mx + dx, my + dy, r, 0, 2 * math.pi); c.fill()
    # drifting clouds (wrap distance = window width + cloud width)
    span = w + 420
    for (p, cy, s, laps) in CLOUDS:
        x = x0 - 260 + ((p + laps * t / LOOP) % 1.0) * span
        _cloud(c, x, y0 + cy, s, (*hexc("#3B4679"), .88))
    # distant hills + village
    c.set_source_rgb(*hexc("#141A38")); c.new_path(); c.move_to(x0, y0 + h)
    for i in range(0, w + 41, 40): c.line_to(x0 + i, y0 + h - 95 - 38 * math.sin(i / 130) - 18 * math.sin(i / 47))
    c.line_to(x0 + w, y0 + h); c.close_path(); c.fill()
    for i, (hx, hw, hh) in enumerate(((60, 70, 60), (150, 54, 82), (420, 80, 66), (520, 60, 92), (640, 72, 58))):
        bx, by = x0 + hx, y0 + h - 70 - hh
        c.set_source_rgb(*hexc("#1A2147")); c.rectangle(bx, by, hw, hh + 80); c.fill()
        c.new_path(); c.move_to(bx - 8, by); c.line_to(bx + hw / 2, by - 30); c.line_to(bx + hw + 8, by); c.close_path(); c.fill()
        if i % 2 == 0 or i == 3:
            c.set_source_rgba(*hexc("#FFD98A"), .9); c.rectangle(bx + hw * .3, by + hh * .3, 14, 16); c.fill()
    # rain streaks on the glass
    if rain:
        c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_width(2.2)
        for (u, p, ln, laps, a) in RAIN:
            y = y0 - 60 + ((p + laps * t / LOOP) % 1.0) * (h + 120)
            x = x0 + u * w + (y - y0) * .06
            c.set_source_rgba(.78, .86, 1, a); c.move_to(x, y); c.line_to(x - ln * .06, y - ln); c.stroke()
    # glass reflection
    c.set_source_rgba(1, 1, 1, .035); c.new_path(); c.move_to(x0 + 60, y0); c.line_to(x0 + 220, y0); c.line_to(x0 + 40, y0 + h); c.line_to(x0 - 120, y0 + h); c.close_path(); c.fill()
    c.restore()

def draw_room(c):
    """Static room drawn over the sky (the glass area is left untouched)."""
    x0, y0, w, h = WIN
    FLOOR = 905
    # wall with soft stripes, window cut out
    c.save(); c.new_path(); c.rectangle(-2000, -500, W + 4000, H + 1000); c.rectangle(x0, y0, w, h)
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); c.clip()
    c.set_source_rgb(*hexc("#222A52")); c.paint()
    c.set_source_rgba(0, 0, .05, .12)
    for sx in range(-2000, W + 2000, 120): c.rectangle(sx, 0, 46, FLOOR); c.fill()
    c.restore()
    # floor
    c.set_source_rgb(*hexc("#2C2442")); c.rectangle(-2000, FLOOR, W + 4000, 800); c.fill()
    c.set_source_rgba(0, 0, 0, .18); c.set_line_width(3)
    for i, fy in enumerate(range(FLOOR + 40, H + 40, 46)): c.move_to(-2000, fy); c.line_to(W + 2000, fy); c.stroke()
    line(c, (-2000, FLOOR), (W + 2000, FLOOR), 8)
    # rug
    c.save(); c.translate(960, 1010); c.scale(1, .22); c.new_path(); c.arc(0, 0, 520, 0, 2 * math.pi); c.restore()
    fill_stroke(c, "#4A3566", INKC, 7)
    c.save(); c.translate(960, 1010); c.scale(1, .22); c.new_path(); c.arc(0, 0, 430, 0, 2 * math.pi); c.restore()
    c.set_source_rgba(1, .85, .6, .12); c.set_line_width(5); c.stroke()
    # window frame + mullions + sill
    frame = "#5A4670"
    rrect(c, x0 - 28, y0 - 28, w + 56, h + 56, 14); c.set_source_rgb(*hexc(frame)); c.set_line_width(1)
    c.new_path(); c.rectangle(x0 - 28, y0 - 28, w + 56, h + 56); c.rectangle(x0, y0, w, h)
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD); c.fill(); c.set_fill_rule(cairo.FILL_RULE_WINDING)
    for r in ((x0 - 28, y0 - 28, w + 56, h + 56), (x0, y0, w, h)):
        c.new_path(); c.rectangle(*r); c.set_source_rgb(*INKC); c.set_line_width(8); c.stroke()
    for a, b in (((x0 + w / 2, y0), (x0 + w / 2, y0 + h)), ((x0, y0 + h * .48), (x0 + w, y0 + h * .48))):
        line(c, a, b, 22, hexc(frame));
    for dx in (-11, 11): line(c, (x0 + w / 2 + dx, y0), (x0 + w / 2 + dx, y0 + h), 4)
    for dy in (-11, 11): line(c, (x0, y0 + h * .48 + dy), (x0 + w, y0 + h * .48 + dy), 4)
    rrect(c, x0 - 70, y0 + h + 22, w + 140, 34, 8); fill_stroke(c, "#6A5584", INKC, 7)
    # curtain rod + curtains
    line(c, (x0 - 170, y0 - 70), (x0 + w + 170, y0 - 70), 14, hexc("#B08A5A"))
    for cx in (x0 - 170, x0 + w + 170): c.new_path(); c.arc(cx, y0 - 70, 16, 0, 2 * math.pi); fill_stroke(c, "#B08A5A", INKC, 5)
    for side in (-1, 1):
        ox = x0 - 165 if side < 0 else x0 + w + 165
        inner = ox + side * -1 * 205
        c.new_path(); c.move_to(ox, y0 - 70); c.line_to(inner, y0 - 70)
        c.curve_to(inner + side * 30, y0 + 200, ox + side * -60, y0 + 330, ox + side * -55, y0 + 420)
        c.curve_to(ox + side * -40, y0 + 560, ox + side * -70, y0 + 700, ox + side * -80, FLOOR - 6)
        c.line_to(ox, FLOOR - 6); c.close_path(); fill_stroke(c, "#5B3F72", INKC, 7)
        for k in range(1, 4):
            fx = ox + side * -1 * 34 * k
            c.set_source_rgba(0, 0, 0, .18); c.set_line_width(5); c.move_to(fx, y0 - 60); c.curve_to(fx, y0 + 250, fx + side * 10, y0 + 500, fx + side * 14, FLOOR - 10); c.stroke()
        tx = ox + side * -50
        rrect(c, tx - 26, y0 + 390, 52, 22, 10); fill_stroke(c, "#C9A36A", INKC, 5)
    # fairy-light string above the window (bulbs drawn per frame)
    # armchair + blanket (left)
    ax = 95
    rrect(c, ax, 600, 320, 300, 40); fill_stroke(c, "#2F5E6B", INKC, 8)          # back
    rrect(c, ax - 30, 720, 90, 190, 30); fill_stroke(c, "#28515D", INKC, 8)      # arm L
    rrect(c, ax + 270, 720, 90, 190, 30); fill_stroke(c, "#28515D", INKC, 8)     # arm R
    rrect(c, ax + 40, 760, 250, 100, 22); fill_stroke(c, "#356B79", INKC, 7)     # seat
    c.new_path(); c.move_to(ax + 120, 640); c.curve_to(ax + 260, 630, ax + 300, 720, ax + 250, 860)
    c.line_to(ax + 160, 870); c.curve_to(ax + 190, 760, ax + 140, 700, ax + 120, 640); c.close_path(); fill_stroke(c, "#C76B5A", INKC, 6)
    for k in range(4): c.set_source_rgba(1, 1, 1, .18); c.set_line_width(4); c.move_to(ax + 150 + k * 22, 660 + k * 8); c.line_to(ax + 175 + k * 20, 860); c.stroke()
    for lx in (ax + 10, ax + 300): line(c, (lx, 900), (lx, 930), 12, hexc("#4A3A2E"))
    # plant on the sill (left) and books stack
    px, py = x0 + 40, y0 + h + 22
    for ang, ln in ((-0.9, 70), (-0.4, 95), (0.1, 105), (0.6, 85), (1.0, 60)):
        ex, ey = px + 30 + math.sin(ang) * ln, py - 40 - math.cos(ang) * ln
        c.new_path(); c.move_to(px + 30, py - 40); c.curve_to(px + 30, py - 70, ex - math.sin(ang) * 20, ey + 20, ex, ey)
        c.set_source_rgb(*hexc("#3F8A6A")); c.set_line_width(14); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
    rrect(c, px, py - 46, 60, 48, 8); fill_stroke(c, "#B5654A", INKC, 6)
    # nightstand + lamp + books + mug (right)
    nx = 1500
    rrect(c, nx, 700, 260, 205, 10); fill_stroke(c, "#6B4E3D", INKC, 8)
    line(c, (nx + 10, 790), (nx + 250, 790), 6); rrect(c, nx + 110, 735, 40, 14, 6); fill_stroke(c, "#C9A36A", INKC, 4)
    for i, (bw, col) in enumerate(((150, "#3D6E8F"), (130, "#B85C5C"), (140, "#D9B45A"))):
        rrect(c, nx + 100 + (150 - bw) / 2, 700 - 22 * (i + 1), bw, 22, 4); fill_stroke(c, col, INKC, 5)
    lx = nx + 70
    rrect(c, lx - 34, 680, 68, 22, 8); fill_stroke(c, "#8A6C9E", INKC, 6)       # lamp base
    line(c, (lx, 680), (lx, 560), 10)
    c.new_path(); c.move_to(lx - 48, 470); c.line_to(lx + 48, 470); c.line_to(lx + 78, 565); c.line_to(lx - 78, 565); c.close_path()
    fill_stroke(c, "#F4C878", INKC, 7)
    rrect(c, nx + 195, 640, 44, 44, 8); fill_stroke(c, "#E9E2D0", INKC, 5)     # mug
    c.new_path(); c.arc(nx + 243, 662, 13, -math.pi / 2, math.pi / 2); c.set_source_rgb(*INKC); c.set_line_width(5); c.stroke()
    # picture frame on wall (right)
    rrect(c, 1560, 210, 170, 210, 8); fill_stroke(c, "#B08A5A", INKC, 7)
    rrect(c, 1580, 230, 130, 170, 4); fill_stroke(c, "#2D3D6B", None)
    c.new_path(); c.arc(1645, 300, 24, 0, 2 * math.pi); c.set_source_rgb(*hexc("#FFF3C9")); c.fill()
    c.set_source_rgb(*hexc("#1B2650")); c.new_path(); c.move_to(1580, 400); c.line_to(1625, 340); c.line_to(1660, 380); c.line_to(1690, 350); c.line_to(1710, 400); c.close_path(); c.fill()

def draw_cat(c, t):
    """Sleeping cat on the window sill (breathes slowly)."""
    x0, y0, w, h = WIN
    cx, cy = x0 + w - 170, y0 + h + 22
    br = 1 + 0.035 * math.sin(2 * math.pi * 12 * t / LOOP)          # 5 s breaths
    c.save(); c.translate(cx, cy); c.scale(1, br)
    c.new_path(); c.save(); c.scale(1, .55); c.arc(0, -70, 82, math.pi, 2 * math.pi); c.restore(); c.close_path()
    fill_stroke(c, "#E9A15B", INKC, 7)
    c.new_path(); c.move_to(70, -4); c.curve_to(120, -6, 120, -40, 92, -46); c.set_source_rgb(*INKC); c.set_line_width(20); c.set_line_cap(cairo.LINE_CAP_ROUND); c.stroke()
    c.move_to(70, -4); c.curve_to(120, -6, 120, -40, 92, -46); c.set_source_rgb(*hexc("#E9A15B")); c.set_line_width(9); c.stroke()
    for sx in (-30, 0, 30):
        c.set_source_rgba(.6, .3, .12, .55); c.set_line_width(6); c.move_to(sx, -78); c.line_to(sx + 6, -50); c.stroke()
    c.restore()
    hx, hy = cx - 72, cy - 34
    for ex in (-26, 22):
        c.new_path(); c.move_to(hx + ex, hy - 22); c.line_to(hx + ex + 6, hy - 50); c.line_to(hx + ex + 24, hy - 26); c.close_path(); fill_stroke(c, "#E9A15B", INKC, 6)
    c.new_path(); c.arc(hx, hy, 40, 0, 2 * math.pi); fill_stroke(c, "#E9A15B", INKC, 7)
    for ex in (-15, 15):
        c.new_path(); c.arc(hx + ex, hy - 2, 8, 0.15 * math.pi, 0.85 * math.pi); c.set_source_rgb(*INKC); c.set_line_width(4.5); c.stroke()
    c.new_path(); c.arc(hx, hy + 12, 3.5, 0, 2 * math.pi); c.set_source_rgb(*hexc("#C2554A")); c.fill()
    # z's drifting up (periodic)
    for k in range(3):
        p = ((t / LOOP) * 6 + k / 3) % 1.0
        a = math.sin(math.pi * p) * .55
        c.set_source_rgba(1, .95, .85, a); c.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        c.set_font_size(18 + 16 * p); c.move_to(hx - 60 - 30 * p + 10 * math.sin(p * 6), hy - 50 - 120 * p); c.show_text("z")

def draw_live(c, t, glow):
    """Per-frame warm things: lamp glow (breathing), fairy lights, mug steam."""
    x0, y0, w, h = WIN
    ph = 2 * math.pi * t / LOOP
    c.set_source_surface(glow, 0, 0); c.paint_with_alpha(0.92 + 0.08 * math.sin(2 * ph))
    # fairy lights: sagging strings between rod ends
    pts = []
    for i in range(FAIRY + 1):
        u = i / FAIRY; px = x0 - 150 + u * (w + 300); py = y0 - 66 + 46 * math.sin(math.pi * ((u * 3) % 1))
        pts.append((px, py))
    c.set_source_rgba(.1, .1, .12, .9); c.set_line_width(3); c.move_to(*pts[0])
    for p in pts[1:]: c.line_to(*p)
    c.stroke()
    for i, (px, py) in enumerate(pts[1:-1]):
        a = 0.65 + 0.35 * math.sin((1 + i % 3) * ph + i * 1.7)
        col = ((1, .78, .42), (1, .62, .55), (.98, .9, .6))[i % 3]
        g = cairo.RadialGradient(px, py + 8, 1, px, py + 8, 34); g.add_color_stop_rgba(0, *col, .45 * a); g.add_color_stop_rgba(1, *col, 0)
        c.set_source(g); c.new_path(); c.arc(px, py + 8, 34, 0, 2 * math.pi); c.fill()
        c.new_path(); c.arc(px, py + 8, 7, 0, 2 * math.pi); c.set_source_rgba(*col, .55 + .45 * a); c.fill()
    # mug steam
    mx, my = 1500 + 217, 630
    c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_width(5)
    for k in range(3):
        p = ((t / LOOP) * 10 + k / 3) % 1.0
        c.set_source_rgba(1, 1, 1, .28 * math.sin(math.pi * p)); c.new_path()
        for j in range(12):
            q = j / 11; yy = my - 10 - 80 * p - 40 * q; xx = mx + (k - 1) * 9 + 8 * math.sin(q * 5 + p * 6 + k)
            (c.move_to if j == 0 else c.line_to)(xx, yy)
        c.stroke()

def make_glow():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(s)
    lx, ly = 1570, 540
    g = cairo.RadialGradient(lx, ly, 30, lx, ly, 760)
    g.add_color_stop_rgba(0, 1, .80, .48, .40); g.add_color_stop_rgba(.35, 1, .72, .40, .14); g.add_color_stop_rgba(1, 1, .7, .4, 0)
    c.set_source(g); c.paint()
    g = cairo.RadialGradient(lx, ly + 10, 5, lx, ly + 10, 110); g.add_color_stop_rgba(0, 1, .95, .75, .65); g.add_color_stop_rgba(1, 1, .9, .7, 0)
    c.set_source(g); c.paint()
    return s

def make_vignette():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(s)
    c.translate(W / 2, H / 2); c.scale(1, H / W)
    g = cairo.RadialGradient(0, 0, W * .32, 0, 0, W * .78)
    g.add_color_stop_rgba(0, 0, 0, .04, 0); g.add_color_stop_rgba(1, 0, 0, .04, .55); c.set_source(g); c.paint()
    return s

class Scene:
    def __init__(self, rain=True, brand=True):
        self.rain, self.brand = rain, brand
        self.room = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); draw_room(cairo.Context(self.room))
        self.glow, self.vig = make_glow(), make_vignette()

    def draw(self, c, t):
        draw_sky(c, t, self.rain)
        c.set_source_surface(self.room, 0, 0); c.paint()
        draw_cat(c, t)
        draw_live(c, t, self.glow)
        c.set_source_surface(self.vig, 0, 0); c.paint()
        if self.brand:
            c.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(30)
            c.set_source_rgba(1, .95, .85, .5); c.move_to(W - 190, H - 44); c.show_text("Snortlo")
            c.new_path(); c.arc(W - 212, H - 54, 9, 0, 2 * math.pi); c.fill()
            c.set_source_rgb(*hexc("#1a1f40")); c.new_path(); c.arc(W - 207, H - 58, 8, 0, 2 * math.pi); c.fill()

def render_master(path, rain=True):
    """Render one seamless LOOP seconds of the scene to a lossless master (FFV1)."""
    sc = Scene(rain)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); c = cairo.Context(surf)
    p = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "ffv1", "-level", "3", "-g", "1",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in range(LOOP * FPS):
        c.save(); sc.draw(c, f / FPS); c.restore(); surf.flush()
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close()
    if p.wait(): raise RuntimeError("master render failed")

def render_card(path, label, title):
    """Title card PNG (RGBA, just the panel)."""
    tmp = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10); tc = cairo.Context(tmp)
    tc.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); tc.set_font_size(54)
    size = 54
    while tc.text_extents(title)[2] > 1500 and size > 30: size -= 2; tc.set_font_size(size)
    tw = tc.text_extents(title)[2]
    pw, ph = int(max(tw + 120, 560)), 170 if label else 130
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, pw + 8, ph + 8); c = cairo.Context(s)
    rrect(c, 4, 4, pw, ph, 30); c.set_source_rgba(.04, .05, .14, .62); c.fill_preserve()
    c.set_source_rgba(1, .9, .7, .22); c.set_line_width(2.5); c.stroke()
    if label:
        c.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(26)
        lab = label.upper()
        ext = c.text_extents(lab); spacing = 4
        x = 4 + pw / 2 - (ext[2] + spacing * (len(lab) - 1)) / 2
        c.set_source_rgba(*hexc("#F4C878"), .95)
        for ch in lab:
            c.move_to(x, 4 + 58); c.show_text(ch); x += c.text_extents(ch)[4] + spacing
        text(c, title, 4 + pw / 2, 4 + 112, size, hexc("#FFF3DE"))
    else:
        text(c, title, 4 + pw / 2, 4 + ph / 2, size, hexc("#FFF3DE"))
    s.write_to_png(path)
    return pw + 8, ph + 8

def render_thumb(path, title, subtitle, badge):
    TW, TH = 1280, 720
    sc = Scene(rain=True, brand=False)
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, TW, TH); c = cairo.Context(s)
    c.save(); c.scale(.8, .8); c.translate(-240, -40); sc.draw(c, 7.0); c.restore()
    g = cairo.LinearGradient(0, 0, TW * .56, 0); g.add_color_stop_rgba(0, .02, .03, .10, .88); g.add_color_stop_rgba(.7, .02, .03, .10, .55)
    g.add_color_stop_rgba(1, .02, .03, .10, 0); c.set_source(g); c.paint()
    words = title.upper().split()
    lines = [" ".join(words[:len(words) // 2 or 1]), " ".join(words[len(words) // 2 or 1:])] if len(words) > 1 else [title.upper()]
    lines = [l for l in lines if l]
    size = 132
    c.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    while True:
        c.set_font_size(size)
        if max(c.text_extents(l)[2] for l in lines) < 640 or size < 60: break
        size -= 4
    y = 120 + size * .5
    for l in lines:
        text(c, l, 64, y, size, hexc("#FFF3DE"), anchor="l", outline=INKC); y += size * 1.02
    if subtitle:
        sz = 40; c.set_font_size(sz)
        while c.text_extents(subtitle)[2] > 620 and sz > 24: sz -= 2; c.set_font_size(sz)
        text(c, subtitle, 66, y + 10, sz, hexc("#F4C878"), anchor="l", outline=INKC)
    if badge:
        c.set_font_size(38); bw = c.text_extents(badge)[2] + 48
        rrect(c, 64, TH - 120, bw, 64, 32); fill_stroke(c, "#F4C878", INKC, 6)
        text(c, badge, 64 + bw / 2, TH - 88, 38, INKC)
    c.set_font_size(30); c.set_source_rgba(1, .95, .85, .7); c.move_to(TW - 170, TH - 40); c.show_text("Snortlo")
    s.write_to_png(path)

# ====================================================================== main
def fmt_ts(sec, long_):
    sec = int(sec); h, m, s = sec // 3600, sec // 60 % 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if long_ else f"{m}:{s:02d}"

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keep = "--keep" in sys.argv
    if len(args) != 2: sys.exit(__doc__)
    src, out = os.path.abspath(args[0]), os.path.abspath(args[1])
    os.chdir(os.path.dirname(os.path.abspath(__file__)))          # so models/ resolves
    cfg = json.load(open(src))
    slug = os.path.splitext(os.path.basename(out))[0]
    stem = out[:-4] if out.endswith(".mp4") else out
    work = os.path.join(os.environ.get("LONGFORM_WORK", tempfile.gettempdir()), "snortlo-longform", slug)
    tts_dir = os.path.join(tempfile.gettempdir(), "snortlo-longform", "tts-cache")
    os.makedirs(work, exist_ok=True); os.makedirs(tts_dir, exist_ok=True)
    voice, speed = cfg.get("voice", "af_heart"), float(cfg.get("speed", 0.92))
    rain = cfg.get("rain", True)
    T = {}; t_all = time.time()

    # ---------- 1. build the script: list of ("speech", text) / ("sil", sec) / ("chime",) / ("mark", name, card)
    plan = [("sil", 2.0)]
    if cfg.get("intro"):
        plan.append(("mark", "Intro", ("", display_title(cfg.get("card_title") or cfg.get("title") or "Sleepy Stories"))))
        for pi, para in enumerate(paragraphs(cfg["intro"])):
            if pi: plan.append(("sil", PAUSE_PARA))
            for si, (kind, s) in enumerate(sentences(para)):
                if si: plan.append(("sil", PAUSE_SENT if kind == "sent" else 0.25))
                plan.append(("speech", s))
    for i, st in enumerate(cfg["stories"], 1):
        title = display_title(clean(st["title"]))
        if len(plan) > 1: plan.append(("sil", PAUSE_STORY - 2.8))
        plan.append(("mark", title, (f"Story {i}", title)))
        plan += [("chime",)]
        if cfg.get("announce", True):
            plan += [("speech", f"Story {numword(i)}."), ("sil", 0.9), ("speech", title.rstrip(".") + "."), ("sil", 1.6)]
        for pi, para in enumerate(paragraphs(st["text"])):
            if pi: plan.append(("sil", PAUSE_PARA))
            for si, (kind, s) in enumerate(sentences(para)):
                if si: plan.append(("sil", PAUSE_SENT if kind == "sent" else 0.25))
                plan.append(("speech", s))
    if cfg.get("outro"):
        plan += [("sil", PAUSE_STORY - 2.8), ("mark", "Goodnight", None), ("chime",)]
        for pi, para in enumerate(paragraphs(cfg["outro"])):
            if pi: plan.append(("sil", PAUSE_PARA))
            for si, (kind, s) in enumerate(sentences(para)):
                if si: plan.append(("sil", PAUSE_SENT if kind == "sent" else 0.25))
                plan.append(("speech", s))
    plan.append(("sil", 9.0))

    # ---------- 2. narration -> narr.flac (streamed), TTS in worker processes
    t0 = time.time()
    jobs = []
    for p in plan:
        if p[0] == "speech":
            h = hashlib.sha1(f"{voice}|{speed}|{p[1]}".encode()).hexdigest()
            jobs.append((os.path.join(tts_dir, h + ".npy"), p[1], voice, speed))
    todo = [j for j in jobs if not os.path.exists(j[0])]
    log(f"{len(jobs)} speech chunks ({len(todo)} to synthesize), {len(cfg['stories'])} stories")
    if todo:
        nw = max(1, min(os.cpu_count() or 2, 4))
        with ProcessPoolExecutor(nw, initializer=_init_worker) as ex:
            for n, _ in enumerate(ex.map(_tts, todo, chunksize=1), 1):
                if n % 25 == 0 or n == len(todo): log(f"  tts {n}/{len(todo)}  ({time.time() - t0:.0f}s)")
    T["tts"] = time.time() - t0

    t0 = time.time()
    narr = os.path.join(work, "narr.flac"); marks = []; pos = 0; ch = chime()
    with sf.SoundFile(narr, "w", SR, 1, subtype="PCM_24") as f:
        ji = 0
        for p in plan:
            if p[0] == "sil": n = int(p[1] * SR); f.write(np.zeros(n, np.float32)); pos += n
            elif p[0] == "chime": f.write(ch); pos += len(ch)
            elif p[0] == "mark": marks.append((pos / SR, p[1], p[2]))
            else:
                a = np.load(jobs[ji][0]) * 0.75; ji += 1
                f.write(np.clip(a, -1, 1)); pos += len(a)
    total = pos / SR
    log(f"narration {total / 60:.1f} min")

    # ---------- 3. mix with ambient bed (block-streamed) -> mix.flac (stereo)
    mix = os.path.join(work, "mix.flac"); bed = Bed(total, rain); blk = SR * 30; i0 = 0
    with sf.SoundFile(mix, "w", SR, 2, subtype="PCM_24") as fo:
        for b in sf.blocks(narr, blocksize=blk, dtype="float32"):
            m = bed.block(i0, len(b)) + b[:, None]; i0 += len(b)
            fo.write(np.clip(m, -1, 1).astype(np.float32))
    # ---------- 4. loudness: measure (EBU R128) then one linear gain + safety limiter -> AAC.
    #             (ffmpeg loudnorm would do the same in linear mode but runs ~6x slower on long files)
    af = "highpass=f=45"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mix, "-af", af + ",ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True, check=True)
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])
    gain = TARGET_LUFS - lufs
    audio = os.path.join(work, "audio.m4a")
    ff("-i", mix, "-af", f"{af},volume={gain:.2f}dB,alimiter=limit=0.79:level=false:attack=5:release=80,aresample=48000",
       "-c:a", "aac", "-b:a", "128k", "-ar", "48000", audio)
    T["audio_mix"] = time.time() - t0
    log(f"audio done (mix {lufs:.1f} LUFS, gain {gain:+.1f} dB -> {TARGET_LUFS} LUFS)")

    # ---------- 5. video: master loop -> sub-clips -> concat
    t0 = time.time()
    # the loop + its plain sub-clips are shared by every video (cache keyed by this file's code + settings)
    lkey = hashlib.sha1(open(__file__, "rb").read() + f"{rain}{X264}".encode()).hexdigest()[:12]
    ldir = os.path.join(tempfile.gettempdir(), "snortlo-longform", f"loop-{lkey}"); os.makedirs(ldir, exist_ok=True)
    master = os.path.join(ldir, "master.mkv")
    if not os.path.exists(master + ".ok"):
        render_master(master, rain); open(master + ".ok", "w").close()
    T["loop_render"] = time.time() - t0
    t0 = time.time()
    M, SF = LOOP // SUB, SUB * FPS
    nframes = nfrm(total); J = math.ceil(nframes / SF)
    cards = []
    for k, (ts, name, card) in enumerate(marks):
        if card is None: continue
        png = os.path.join(work, f"card{k}.png"); cw, chh = render_card(png, *card)
        cards.append((ts + 0.3, png, (W - cw) // 2, 842 - chh // 2))
    plain = []
    for m in range(M):
        pth = os.path.join(ldir, f"plain{m}.mp4"); plain.append(pth)
        if not os.path.exists(pth):
            ff("-ss", m * SUB, "-i", master, "-frames:v", SF, *X264, pth + ".tmp.mp4"); os.replace(pth + ".tmp.mp4", pth)
    lst = []
    n_custom = 0
    for j in range(J):
        a, b = j * SUB, min((j + 1) * SUB, nframes / FPS)
        nf = min(SF, nframes - j * SF)
        hit = [cd for cd in cards if cd[0] < b and cd[0] + CARD_LEN > a]
        if not hit and nf == SF:
            lst.append(plain[j % M]); continue
        pth = os.path.join(work, f"seg{j}.mp4"); n_custom += 1
        inputs = ["-ss", (j % M) * SUB, "-i", master]; fg = []; last = "0:v"
        for q, (ts, png, cx, cy) in enumerate(hit):
            o = ts - a
            inputs += ["-loop", "1", "-framerate", FPS, "-t", SUB, "-i", png]
            al = f"alpha(X,Y)*clip(min((T-({o:.3f}))/{CARD_FADE},({o + CARD_LEN:.3f}-T)/{CARD_FADE}),0,1)"
            fg.append(f"[{q + 1}:v]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{al}'[c{q}]")
            fg.append(f"[{last}][c{q}]overlay={cx}:{cy}:format=yuv420:eof_action=pass[v{q}]"); last = f"v{q}"
        if fg:
            ff(*inputs, "-filter_complex", ";".join(fg), "-map", f"[{last}]", "-frames:v", nf, *X264, pth)
        else:
            ff(*inputs, "-frames:v", nf, *X264, pth)
        lst.append(pth)
    listf = os.path.join(work, "list.txt")
    with open(listf, "w") as f:
        for p in lst: f.write(f"file '{p}'\n")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ff("-f", "concat", "-safe", 0, "-i", listf, "-i", audio, "-map", "0:v", "-map", "1:a", "-c", "copy",
       "-movflags", "+faststart", out)
    T["video_encode"] = time.time() - t0

    # ---------- 6. chapters + thumbnail
    long_ = total >= 3600
    with open(stem + ".chapters.txt", "w") as f:
        for k, (ts, name, _) in enumerate(marks):
            f.write(f"{fmt_ts(0 if k == 0 else ts, long_)} {name}\n")
    mins = total / 60
    badge = f"{int(mins // 60)} HR {int(round(mins % 60))} MIN" if mins >= 60 else f"{int(round(mins))} MIN"
    if mins >= 60 and round(mins % 60) == 0: badge = f"{int(mins // 60)} HOUR" + ("S" if mins >= 120 else "")
    render_thumb(stem + "-thumb.png", cfg.get("thumb_title", "Sleepy Stories"),
                 cfg.get("thumb_subtitle", f"{len(cfg['stories'])} cozy stories to fall asleep to"), badge)
    if not keep:
        for fn in ("narr.flac", "mix.flac", "audio.m4a") + tuple(os.path.basename(p) for p in lst if "/seg" in p):
            try: os.remove(os.path.join(work, fn))
            except OSError: pass
    T["total"] = time.time() - t_all
    log(f"wrote {out}  ({total / 60:.1f} min, {os.path.getsize(out) / 1e6:.0f} MB, {n_custom} custom sub-clips)")
    log("timings: " + ", ".join(f"{k} {v:.1f}s" for k, v in T.items()))

if __name__ == "__main__":
    main()
