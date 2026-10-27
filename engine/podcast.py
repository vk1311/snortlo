"""Keegix Podcast / Staffkin Podcast renderer: two AI voices + brand motion graphics, 20+ minute episodes.

    cd engine && python3 podcast.py ../podcasts/<brand>/<slug>.json ../media/pod-<slug>.mp4 [--res 1280x720] [--test 12]

Writes next to the mp4:
    <stem>.timeline.json     every sentence with start/end/speaker (podcast_shorts.py cuts Shorts from it)
    <stem>.description.txt   YouTube description: script description + chapters + sources + photo credits
    <stem>.chapters.txt      chapters only
    <stem>-thumb.png         1280x720 thumbnail

Script format: PODCAST_FORMAT.md. Brand looks and hosts: podcast_brands.py.

How it works (fast on a 2-core box):
  audio   voice_backend (Qwen3-TTS on Kaggle's GPU, Chatterbox/Kokoro fail-safe) per sentence, placed on a host track and a guest
          track, plus a soft synthesized sting at the start, a chime between chapters and an outro pad.
  video   a seamless 20 s background loop (soft moving glows in brand colours, made in numpy, no stock video),
          one transparent overlay PNG per sentence (seats, captions, cards, CC0 photos) shown through the
          ffmpeg concat demuxer, and two live waveforms (one per voice) drawn by ffmpeg's showwaves.
          Everything is composited and encoded in a single ffmpeg pass.
"""
import hashlib, json, math, os, re, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from podcast_brands import BRANDS
import broll

SR = 24000
FPS = 24
LOOP = 20
DW, DH = 1920, 1080                     # design canvas; overlays are drawn here and scaled to the output size
GAP_SENT, GAP_LINE, GAP_TURN, GAP_SEG = 0.20, 0.30, 0.42, 1.25
STING_LEN, SPEECH_START, OUTRO_LEN = 3.2, 2.6, 7.0
CACHE = "/tmp/snortlo-podcast"

def log(*a): print(f"[podcast {time.strftime('%H:%M:%S')}]", *a, flush=True)

def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *map(str, args)], check=True)

def hexrgb(h, a=255):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)

# ====================================================================== text
def clean(s):
    s = s.replace("…", "...").replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", s).strip()

def sentences(txt):
    parts = re.split(r'(?<=[.!?])\s+|(?<=[.!?]["\')])\s+', clean(txt))
    out = []
    for p in parts:
        p = p.strip()
        while len(p) > 260:                    # very long sentence: split at a comma near the middle
            cuts = [m.end() for m in re.finditer(r"[,;:]\s", p)]
            if not cuts: break
            c = min(cuts, key=lambda x: abs(x - len(p) / 2)); out.append(p[:c].strip()); p = p[c:].strip()
        if p: out.append(p)
    return out

def display_text(s):
    """Spoken text -> on-screen caption: "A I" -> "AI", "W H O" -> "WHO", "B C" -> "BC", "dot com" -> ".com"."""
    s = re.sub(r"(?<![\w'])([A-Z])((?: [A-Z])+)(?![\w'])", lambda m: (m.group(1) + m.group(2)).replace(" ", ""), s)
    s = re.sub(r" dot (com|ca)\b", r".\1", s)
    return re.sub(r"\.(com|ca) slash ([\w-]+)", r".\1/\2", s)

def fmt_ts(t):
    t = int(t); h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

# ====================================================================== TTS workers
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
    lang = "en-gb" if voice.startswith("b") else "en-us"
    s, _ = _K.create(txt, voice=voice, speed=speed, lang=lang)
    s = np.asarray(s, np.float32)
    nz = np.where(np.abs(s) > 0.008)[0]
    if len(nz): s = s[max(nz[0] - int(.03 * SR), 0): nz[-1] + int(.12 * SR)]
    f = min(len(s) // 2, int(.010 * SR))
    if f:
        s[:f] *= np.linspace(0, 1, f, dtype=np.float32); s[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    np.save(path + ".tmp.npy", s); os.replace(path + ".tmp.npy", path)
    return path

# ====================================================================== synthesized music (no samples, nothing to claim)
def _tone(freq, dur, amp, attack=0.02, decay=1.2, partials=((1, 1), (2, .3), (3, .12))):
    t = np.arange(int(dur * SR)) / SR
    env = np.minimum(t / attack, 1) * np.exp(-t / decay)
    return amp * env * sum(a * np.sin(2 * np.pi * freq * r * t) for r, a in partials)

def sting(seed):
    """Warm 3 s opening: a soft arpeggiated major-seven chord over a low pad."""
    rng = np.random.default_rng(seed)
    root = [220.0, 246.94, 261.63, 196.0][seed % 4]
    out = np.zeros(int(STING_LEN * SR))
    for i, r in enumerate([1, 1.25, 1.5, 1.875, 2.0]):
        s = _tone(root * r, STING_LEN - i * .14, .16, decay=1.4); o = int(i * .14 * SR); out[o:o + len(s)] += s
    t = np.arange(len(out)) / SR
    out += .07 * np.sin(2 * np.pi * root / 2 * t) * np.minimum(t / .6, 1) * np.minimum(1, (t[-1] - t) / 1.2)
    out *= np.minimum(1, (t[-1] - t) / .5)
    return (out / np.abs(out).max() * .32).astype(np.float32)

def chime():
    out = np.zeros(int(1.6 * SR))
    for f0, t0 in ((659.25, 0), (987.77, .12)):
        s = _tone(f0, 1.6 - t0, .5, attack=.005, decay=.45); o = int(t0 * SR); out[o:o + len(s)] += s
    return (out / np.abs(out).max() * .10).astype(np.float32)

def outro_pad(root=220.0):
    t = np.arange(int(OUTRO_LEN * SR)) / SR
    out = sum(a * np.sin(2 * np.pi * root * r * t) for r, a in ((.5, .5), (1, .35), (1.5, .2), (2, .1), (2.5, .06)))
    out *= np.minimum(t / 1.0, 1) * np.minimum(1, (t[-1] - t) / 2.5)
    return (out / np.abs(out).max() * .14).astype(np.float32)

# ====================================================================== fonts
_FC = {}
def font(spec, size):
    path, axes = spec; key = (path, tuple(sorted(axes.items())), size)
    if key not in _FC:
        f = ImageFont.truetype(path, size)
        try:
            names = [a["name"].decode() if isinstance(a["name"], bytes) else a["name"] for a in f.get_variation_axes()]
            f.set_variation_by_axes([axes.get(n, a["default"]) for n, a in zip(names, f.get_variation_axes())])
        except Exception:
            pass
        _FC[key] = f
    return _FC[key]

def wrap(draw, text, fnt, maxw, max_lines=None):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]; lines[-1] = lines[-1].rstrip(",.;:") + "…"
    return lines

def text_block(draw, xy, text, fnt, fill, maxw, spacing=1.18, max_lines=None, anchor="la"):
    x, y = xy; lines = wrap(draw, text, fnt, maxw, max_lines); lh = fnt.size * spacing
    for i, l in enumerate(lines):
        draw.text((x, y + i * lh), l, font=fnt, fill=fill, anchor=anchor)
    return y + len(lines) * lh

def tracked(draw, xy, text, fnt, fill, track=0.08, anchor="l"):
    """Uppercase kicker with letter spacing."""
    x, y = xy; sp = fnt.size * track
    w = sum(draw.textlength(ch, font=fnt) for ch in text) + sp * (len(text) - 1)
    if anchor == "r": x -= w
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="ls"); x += draw.textlength(ch, font=fnt) + sp
    return w

# ====================================================================== background loop
def background_loop(B, w, h, path):
    if os.path.exists(path): return path
    lw, lh = (384, 216) if w >= h else (216, 384)
    yy, xx = np.mgrid[0:lh, 0:lw].astype(np.float32)
    c0, c1 = np.array(hexrgb(B["bg"][0])[:3], np.float32), np.array(hexrgb(B["bg"][1])[:3], np.float32)
    k = np.clip((xx / lw * .45 + yy / lh * .55), 0, 1)[..., None]
    base = c0 * (1 - k) + c1 * k
    vig = 1 - .28 * (((xx / lw - .5) ** 2 + (yy / lh - .55) ** 2) * 2.2)[..., None]
    glows = [np.array(hexrgb(g)[:3], np.float32) for g in B["glows"]]
    spec = [  # (colour index, cx, cy, ax, ay, kx, ky, radius, strength)
        (0, .78, .30, .10, .08, 1, 2, .30, .16), (1, .20, .78, .12, .06, 2, 1, .36, .07),
        (2, .55, .65, .18, .12, 1, 1, .45, .35), (0, .10, .15, .06, .07, 3, 2, .22, .07)]
    p = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{lw}x{lh}", "-r", str(FPS), "-i", "-", "-vf", f"scale={w}:{h}:flags=bicubic",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                          "-g", str(FPS * LOOP), path], stdin=subprocess.PIPE)
    for f in range(FPS * LOOP):
        ph = 2 * math.pi * f / (FPS * LOOP)
        img = base.copy()
        for ci, cx, cy, ax, ay, kx, ky, r, st in spec:
            gx, gy = (cx + ax * math.sin(kx * ph)) * lw, (cy + ay * math.cos(ky * ph)) * lh
            d = ((xx - gx) ** 2 + (yy - gy) ** 2) / (r * lw) ** 2
            a = (st * np.exp(-d * 2.2))[..., None]
            img = img * (1 - a) + glows[ci] * a
        img = np.clip(img * vig, 0, 255).astype(np.uint8)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    return path

# ====================================================================== overlay drawing
class Painter:
    def __init__(self, B, ep, guest, broll_imgs, ow, oh):
        self.B, self.ep, self.guest, self.broll, self.ow, self.oh = B, ep, guest, broll_imgs, ow, oh
        self.logo = Image.open(B["logo"]).convert("RGBA")
        lh = 50; self.logo = self.logo.resize((int(self.logo.width * lh / self.logo.height), lh), Image.LANCZOS)
        self.n_seg = len(ep["segments"])
        self._photo_cache = {}

    def c(self, key, a=255): return hexrgb(self.B[key], a)

    def canvas(self):
        im = Image.new("RGBA", (DW, DH), (0, 0, 0, 0)); return im, ImageDraw.Draw(im)

    def out(self, im, path):
        if (self.ow, self.oh) != (DW, DH): im = im.resize((self.ow, self.oh), Image.LANCZOS)
        im.save(path, compress_level=3)

    # ---------------------------------------------------------------- pieces
    def chrome(self, im, d, seg_i):
        B = self.B
        im.alpha_composite(self.logo, (80, 52))
        tracked(d, (1840, 88), f"EPISODE {self.ep.get('episode', 1)}", font(B["ui_bold"], 22), self.c("on_dark_muted"), anchor="r")
        d.text((80, DH - 34), B["footer"], font=font(B["ui"], 21), fill=self.c("on_dark_muted"), anchor="ls")
        d.text((1840, DH - 34), B["show"], font=font(B["ui"], 21), fill=self.c("on_dark_muted"), anchor="rs")
        if seg_i is not None:
            heading = self.ep["segments"][seg_i]["heading"]
            tracked(d, (780, 150), f"CHAPTER {seg_i + 1} OF {self.n_seg}", font(B["ui_bold"], 20), self.c("accent"))
            kt, kf = f"CHAPTER {seg_i + 1} OF {self.n_seg}", font(B["ui_bold"], 20)
            kw = sum(d.textlength(ch, font=kf) for ch in kt) + kf.size * .08 * (len(kt) - 1)
            hf = font(B["ui"], 24); room = 1840 - (780 + kw + 22)
            if d.textlength(heading, font=hf) > room:
                while heading and d.textlength(heading + "…", font=hf) > room: heading = heading[:-1]
                heading = heading.rstrip(" ,:;") + "…"
            d.text((780 + kw + 22, 150), heading, font=hf, fill=self.c("on_dark"), anchor="ls")

    def seat(self, im, d, cy, person, active, is_host):
        B = self.B; x0, r = 170, 82
        lay = Image.new("RGBA", (680, 230), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        ax, ay = x0 - 80 + 0, 115
        if active:
            ld.ellipse((ax - r - 12, ay - r - 12, ax + r + 12, ay + r + 12), outline=self.c("accent"), width=7)
        fill = self.c("accent") if is_host else self.c("panel_alt")
        ld.ellipse((ax - r, ay - r, ax + r, ay + r), fill=fill)
        ld.text((ax, ay + 4), person["name"][0].upper(), font=font(B["head"], 96), fill=self.c("ink"), anchor="mm")
        ld.text((210, 88), person["name"], font=font(B["ui_bold"], 44), fill=self.c("on_dark"), anchor="ls")
        rf = font(B["ui"], 25)
        if ld.textlength(person["role"], font=rf) > 440: rf = font(B["ui"], 21)
        for i, rl in enumerate(wrap(ld, person["role"], rf, 450, 2)):
            ld.text((210, 124 + i * 28), rl, font=rf, fill=self.c("on_dark_muted"), anchor="ls")
        if not active:
            a = lay.getchannel("A").point(lambda v: int(v * .5)); lay.putalpha(a)
        im.alpha_composite(lay, (80, cy - 115))

    def caption(self, im, d, who, text):
        B = self.B
        name = (B["host"] if who == "host" else self.guest)["name"]
        f, lh = font(B["caption"], 44), 54
        lines = wrap(d, text, f, 1700)
        if len(lines) > 3: f, lh = font(B["caption"], 38), 46; lines = wrap(d, text, f, 1740, 3)
        y = {1: 900, 2: 872}.get(len(lines), 850)
        d.text((80, y - 50), name.upper(), font=font(B["ui_bold"], 22), fill=self.c("accent"), anchor="ls")
        for i, l in enumerate(lines):
            d.text((82, y + i * lh + 2), l, font=f, fill=(0, 0, 0, 110), anchor="ls")
            d.text((80, y + i * lh), l, font=f, fill=self.c("on_dark"), anchor="ls")

    def panel_box(self, im, fill=None):
        x0, y0, x1, y1 = 780, 180, 1840, 800
        sh = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10, x1, y1 + 10), 30, fill=(0, 0, 0, 70))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
        ImageDraw.Draw(im).rounded_rectangle((x0, y0, x1, y1), 30, fill=fill or self.c("panel"))
        return x0, y0, x1, y1

    def photo(self, seg_i):
        if seg_i in self._photo_cache: return self._photo_cache[seg_i]
        path, credit = self.broll.get(seg_i, (None, None))
        res = None
        if path:
            pw, ph = 1060, 620
            src = Image.open(path).convert("RGB")
            s = max(pw / src.width, ph / src.height)
            src = src.resize((int(src.width * s) + 1, int(src.height * s) + 1), Image.LANCZOS)
            l, t = (src.width - pw) // 2, (src.height - ph) // 2
            src = src.crop((l, t, l + pw, t + ph)).convert("RGBA")
            grad = Image.new("L", (1, ph)); grad.putdata([int(200 * max(0, (y / ph - .35) / .65) ** 1.3) for y in range(ph)])
            dark = Image.new("RGBA", (pw, ph), hexrgb(self.B["bg"][1])); dark.putalpha(grad.resize((pw, ph)))
            src.alpha_composite(dark)
            mask = Image.new("L", (pw, ph), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), 30, fill=255)
            src.putalpha(mask)
            res = (src, credit)
        self._photo_cache[seg_i] = res
        return res

    def panel_default(self, im, d, seg_i):
        B = self.B; heading = self.ep["segments"][seg_i]["heading"]
        ph = self.photo(seg_i)
        if ph:
            src, credit = ph
            sh = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((780, 190, 1840, 810), 30, fill=(0, 0, 0, 70))
            im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
            im.alpha_composite(src, (780, 180))
            cr = f"Photo: {credit['creator'][:40]} · {credit['license']}"; cf = font(B["ui"], 18)
            cw = d.textlength(cr, font=cf)
            d.rounded_rectangle((1820 - cw - 16, 198, 1828, 230), 10, fill=(0, 0, 0, 120))
            d.text((1820, 206), cr, font=cf, fill=(255, 255, 255, 230), anchor="ra")
            text_block(d, (830, 640), heading, font(B["head"], 62), self.c("on_dark"), 960, 1.08, 2)
        else:
            x0, y0, x1, y1 = self.panel_box(im, self.c("panel_alt"))
            tracked(d, (840, 300), f"CHAPTER {seg_i + 1}", font(B["ui_bold"], 26), self.c("muted"))
            d.rectangle((840, 330, 940, 338), fill=self.c("accent"))
            text_block(d, (840, 380), heading, font(B["head"], 84), self.c("ink"), 940, 1.06, 4)

    def panel_card(self, im, d, card):
        B = self.B; ink, muted = self.c("ink"), self.c("muted")
        x0, y0, x1, y1 = self.panel_box(im)
        X, W = x0 + 70, x1 - x0 - 140
        t = card.get("type")
        src = card.get("source")
        if t == "stat":
            big = str(card.get("big", ""))
            size = 190 if len(big) <= 6 else 150 if len(big) <= 10 else 110
            d.text((X, y0 + 90 + size * .8), big, font=font(B["head"], size), fill=ink, anchor="ls")
            d.rectangle((X, y0 + 120 + size * .8, X + 120, y0 + 128 + size * .8), fill=self.c("accent"))
            text_block(d, (X, y0 + 170 + size * .8), card.get("label", ""), font(B["ui"], 38), muted, W, 1.25, 4)
        elif t == "list":
            y = text_block(d, (X, y0 + 70), card.get("title", ""), font(B["head"], 58), ink, W, 1.08, 2) + 28
            for it in card.get("items", [])[:4]:
                d.ellipse((X, y + 14, X + 18, y + 32), fill=self.c("accent"))
                y = text_block(d, (X + 44, y), it, font(B["ui"], 40), ink, W - 44, 1.2, 2) + 22
        elif t == "point":
            d.rectangle((X, y0 + 110, X + 10, y1 - 110), fill=self.c("accent"))
            fnt = font(B["head_italic"], 70)
            lines = wrap(d, card.get("text", ""), fnt, W - 50)
            if len(lines) > 4: fnt = font(B["head_italic"], 56); lines = wrap(d, card.get("text", ""), fnt, W - 50)
            ty = (y0 + y1) / 2 - len(lines) * fnt.size * 1.12 / 2
            for i, l in enumerate(lines): d.text((X + 50, ty + i * fnt.size * 1.12), l, font=fnt, fill=ink)
        elif t == "compare":
            cw = (W - 60) / 2
            for k, (tt, body) in enumerate(((card.get("left_title"), card.get("left")), (card.get("right_title"), card.get("right")))):
                cx = X + k * (cw + 60)
                if k: d.line((cx - 30, y0 + 80, cx - 30, y1 - 80), fill=hexrgb(B["muted"], 70), width=3)
                tracked(d, (cx, y0 + 120), str(tt or "").upper(), font(B["ui_bold"], 26), muted)
                d.rectangle((cx, y0 + 140, cx + 70, y0 + 147), fill=self.c("accent"))
                text_block(d, (cx, y0 + 180), str(body or ""), font(B["head"], 50), ink, cw, 1.12, 6)
        elif t == "rule":
            tracked(d, (X, y0 + 110), str(card.get("title", "")).upper(), font(B["ui_bold"], 28), muted)
            d.rectangle((X, y0 + 132, X + 90, y0 + 140), fill=self.c("accent"))
            text_block(d, (X, y0 + 180), card.get("text", ""), font(B["head"], 58), ink, W, 1.12, 5)
            foot = " · ".join(x for x in (f"As of {card['as_of']}" if card.get("as_of") else "", "Not legal advice") if x)
            if src: d.text((X, y1 - 96), f"Source: {src}", font=font(B["ui"], 24), fill=muted, anchor="ls")
            d.text((X, y1 - 56), foot, font=font(B["ui"], 24), fill=muted, anchor="ls")
            src = None
        elif t == "history":
            d.text((X, y0 + 250), str(card.get("year", "")), font=font(B["head"], 200), fill=ink, anchor="ls")
            d.rectangle((X, y0 + 285, X + 140, y0 + 294), fill=self.c("accent"))
            text_block(d, (X, y0 + 340), card.get("text", ""), font(B["head"], 52), ink, W, 1.14, 4)
        if src:
            d.text((X, y1 - 56), f"Source: {src}", font=font(B["ui"], 24), fill=muted, anchor="ls")

    # ---------------------------------------------------------------- full frames
    def sentence_frame(self, ev, path):
        im, d = self.canvas()
        self.chrome(im, d, ev["seg"])
        host, guest = self.B["host"], self.guest
        self.seat(im, d, 360, host, ev["who"] == "host", True)
        self.seat(im, d, 640, guest, ev["who"] == "guest", False)
        if ev["card"]: self.panel_card(im, d, ev["card"])
        else: self.panel_default(im, d, ev["seg"])
        self.caption(im, d, ev["who"], display_text(ev["text"]))
        self.out(im, path)

    def title_frame(self, path):
        B = self.B; im, d = self.canvas()
        big = Image.open(B["logo"]).convert("RGBA"); h = 84
        big = big.resize((int(big.width * h / big.height), h), Image.LANCZOS)
        im.alpha_composite(big, ((DW - big.width) // 2, 250))
        tracked(d, (DW / 2 - 210, 420), f"{B['show'].upper()} · EPISODE {self.ep.get('episode', 1)}", font(B["ui_bold"], 26), self.c("accent"))
        lines = wrap(d, self.ep["card_title"], font(B["head"], 96), 1500)
        for i, l in enumerate(lines[:3]):
            d.text((DW / 2, 540 + i * 104), l, font=font(B["head"], 96), fill=self.c("on_dark"), anchor="mm")
        d.text((DW / 2, 560 + len(lines[:3]) * 104), f"with {B['host']['name']} and {self.guest['name']} · AI voices",
               font=font(B["ui"], 32), fill=self.c("on_dark_muted"), anchor="mm")
        self.out(im, path)

    def end_frame(self, path):
        B = self.B; im, d = self.canvas()
        big = Image.open(B["logo"]).convert("RGBA"); h = 96
        big = big.resize((int(big.width * h / big.height), h), Image.LANCZOS)
        im.alpha_composite(big, ((DW - big.width) // 2, 260))
        d.text((DW / 2, 520), B["cta"], font=font(B["head"], 84), fill=self.c("on_dark"), anchor="mm")
        d.rectangle((DW / 2 - 70, 590, DW / 2 + 70, 598), fill=self.c("accent"))
        d.text((DW / 2, 670), "Sources and chapters are in the description.", font=font(B["ui"], 36), fill=self.c("on_dark_muted"), anchor="mm")
        d.text((DW / 2, 730), f"New episodes every week on {B['show']}.", font=font(B["ui"], 36), fill=self.c("on_dark_muted"), anchor="mm")
        self.out(im, path)

    def thumbnail(self, bg_frame, path):
        B = self.B
        im = bg_frame.convert("RGBA").resize((DW, DH)); d = ImageDraw.Draw(im)
        im.alpha_composite(self.logo.resize((self.logo.width * 2, 100)) if False else self.logo, (80, 70))
        tracked(d, (80, 230), f"EPISODE {self.ep.get('episode', 1)}", font(B["ui_bold"], 40), self.c("accent"))
        fnt = font(B["head"], 150); lines = wrap(d, self.ep.get("thumb_title", self.ep["card_title"]), fnt, 1560)
        if len(lines) > 3: fnt = font(B["head"], 118); lines = wrap(d, self.ep.get("thumb_title", self.ep["card_title"]), fnt, 1600)
        for i, l in enumerate(lines[:4]):
            d.text((80, 300 + i * fnt.size * 1.04), l, font=fnt, fill=self.c("on_dark"), anchor="la")
        d.rectangle((80, DH - 120, 300, DH - 108), fill=self.c("accent"))
        d.text((80, DH - 60), B["show"], font=font(B["ui_bold"], 44), fill=self.c("on_dark_muted"), anchor="ls")
        im.convert("RGB").resize((1280, 720), Image.LANCZOS).save(path)

# ====================================================================== YouTube description (YouTube caps it at 5,000 characters)
YT_LIMIT = 4900
def make_description(ep, B, chap, credits):
    srcs = ep.get("sources", [])
    repo = f"https://github.com/vk1311/snortlo/blob/main/podcasts/{ep['brand']}/{ep['slug']}.json"
    def build(level):
        out = [ep.get("description", "").strip(), "", "Chapters", *chap, "", "Sources"]
        if level < 2: out += [f"- {s['label']}: {s['url']}" for s in srcs]
        else: out += [f"- {s['url']}" for s in srcs]
        if credits:
            if level == 0: out += ["", "Photos (CC0 / public domain)"] + [f"- {broll.credit_line(c)}" for c in credits]
            else: out += ["", "Photos: CC0 / public domain, credits at https://github.com/vk1311/snortlo/blob/main/podcasts/CREDITS.md"]
        out += ["", f"{B['show']} is made with AI voices. {B['cta']}."]
        return "\n".join(out) + "\n"
    for level in (0, 1, 2):
        txt = build(level)
        if len(txt) <= YT_LIMIT: return txt
    # still too long: keep as many sources as fit and point to the full list
    out = build(2).split("\n"); keep = []
    head = out[:out.index("Sources") + 1]; tail = out[out.index("Sources") + 1 + len(srcs):]
    more = f"- Full source list: {repo}"
    for s in srcs:
        cand = "\n".join(head + keep + [f"- {s['url']}", more] + tail)
        if len(cand) > YT_LIMIT: break
        keep.append(f"- {s['url']}")
    return "\n".join(head + keep + [more] + tail)

# ====================================================================== main
def build(script_path, out_mp4, res=(1920, 1080), test=None):
    ep = json.load(open(script_path))
    B = BRANDS[ep["brand"]]
    guest = ep["guest"]
    host = B["host"]
    assert guest["voice"] != host["voice"], "guest voice must differ from the host's"
    stem = os.path.splitext(out_mp4)[0]
    work = os.path.join(CACHE, ep["slug"]); os.makedirs(os.path.join(CACHE, "tts"), exist_ok=True)
    os.makedirs(os.path.join(work, "ov"), exist_ok=True)

    # ---- flatten to sentences
    events, card = [], None
    for si, seg in enumerate(ep["segments"]):
        card = None
        for li, ln in enumerate(seg["lines"]):
            if "card" in ln: card = None if ln["card"] in (None, "clear") else ln["card"]
            for sent in sentences(ln["text"]):
                events.append({"seg": si, "line": li, "who": ln["who"], "text": sent, "card": card})
    if test: events = events[:test]
    log(f"{len(events)} sentences, {sum(len(e['text'].split()) for e in events)} words")

    # ---- voices (voice_backend: Qwen3 on Kaggle -> Chatterbox -> Kokoro, 1.10x)
    from voice_backend import voice_lines
    lines = [((host if e["who"] == "host" else guest)["voice"], e["text"]) for e in events]
    t0 = time.time()
    arrays = voice_lines(lines, tempo=float(os.environ.get("VOICE_TEMPO", "1.10")))
    for i, (e, a) in enumerate(zip(events, arrays)):
        e["tts"] = os.path.join(work, f"v{i:04d}.npy"); np.save(e["tts"], a)
    log(f"TTS done in {time.time() - t0:.0f}s")

    # ---- timeline
    t = SPEECH_START; prev = None; seg_starts = {}
    for e in events:
        if prev is not None:
            if e["seg"] != prev["seg"]: t += GAP_SEG
            elif e["line"] != prev["line"]: t += GAP_TURN if e["who"] != prev["who"] else GAP_LINE
            else: t += GAP_SENT
        if e["seg"] not in seg_starts: seg_starts[e["seg"]] = t - (GAP_SEG * .6 if e["seg"] else SPEECH_START)
        n = len(np.load(e["tts"], mmap_mode="r"))
        e["start"], e["end"] = t, t + n / SR; t = e["end"]; prev = e
    speech_end = t
    total = speech_end + 0.9 + OUTRO_LEN
    N = int(math.ceil(total * SR))
    trk = {"host": np.zeros(N, np.float32), "guest": np.zeros(N, np.float32)}
    music = np.zeros(N, np.float32)
    for e in events:
        s = np.load(e["tts"]); o = int(e["start"] * SR); trk[e["who"]][o:o + len(s)] += s
    seed = int(hashlib.sha1(ep["slug"].encode()).hexdigest(), 16)
    st = sting(seed); music[:len(st)] += st
    ch = chime()
    for si, ts in seg_starts.items():
        if si: o = int(max(ts, 0) * SR); music[o:o + len(ch)] += ch[:N - o]
    op = outro_pad(); o = int((speech_end + .3) * SR); music[o:o + len(op)] += op[:N - o]
    mix = trk["host"] + trk["guest"] + music
    peak = np.abs(mix).max() + 1e-9
    for k in trk: trk[k] /= peak
    mix /= peak
    sf.write(os.path.join(work, "host.wav"), trk["host"], SR)
    sf.write(os.path.join(work, "guest.wav"), trk["guest"], SR)
    sf.write(os.path.join(work, "mix.wav"), mix * .95, SR)
    log(f"audio {total / 60:.1f} min")

    # ---- b-roll
    broll_imgs, used = {}, set()
    assets = os.path.join(os.path.dirname(os.path.abspath(script_path)), "assets")
    for si, seg in enumerate(ep["segments"]):
        q = seg.get("broll")
        if q:
            pth, cr = broll.fetch(q, assets, avoid=used)
            if pth: broll_imgs[si] = (pth, cr); used.add(cr["source"])
    log(f"b-roll: {len(broll_imgs)} photos")

    # ---- overlays
    ow, oh = res
    P = Painter(B, ep, guest, broll_imgs, ow, oh)
    ovd = os.path.join(work, "ov")
    for f in os.listdir(ovd): os.remove(os.path.join(ovd, f))
    seq = []
    P.title_frame(os.path.join(ovd, "title.png")); seq.append(("title.png", events[0]["start"]))
    for i, e in enumerate(events):
        name = f"s{i:04d}.png"; P.sentence_frame(e, os.path.join(ovd, name))
        nxt = events[i + 1]["start"] if i + 1 < len(events) else speech_end + 0.6
        if i + 1 < len(events) and events[i + 1]["seg"] != e["seg"]:
            nxt = seg_starts[events[i + 1]["seg"]]            # the next chapter's frame comes up with its chime
            events[i + 1]["show_from"] = nxt
        start = e.get("show_from", e["start"] if i else events[0]["start"])
        seq.append((name, nxt - start))
    P.end_frame(os.path.join(ovd, "end.png")); seq.append(("end.png", total - (speech_end + 0.6)))
    with open(os.path.join(work, "ov.txt"), "w") as f:
        for name, dur in seq: f.write(f"file '{os.path.join(ovd, name)}'\nduration {max(dur, 1 / FPS):.4f}\n")
        f.write(f"file '{os.path.join(ovd, seq[-1][0])}'\n")
    log(f"overlays: {len(seq)} frames")

    # ---- background + composite
    bg = background_loop(B, ow, oh, os.path.join(CACHE, f"bg-{ep['brand']}-{ow}x{oh}.mp4"))
    s = ow / DW
    ww, wh = int(400 * s) // 2 * 2, int(56 * s) // 2 * 2
    wx = int(290 * s); hy, gy = int((360 + 44) * s), int((640 + 44) * s)
    col = B["accent"].lstrip("#")
    fc = (f"[0:v]trim=duration={total:.3f},setpts=PTS-STARTPTS[bg];"
          f"[1:v]fps={FPS},format=rgba[ov];"
          f"[2:a]showwaves=s={ww}x{wh}:mode=cline:rate={FPS}:colors=0x{col}:scale=sqrt:draw=full,format=rgba[hw];"
          f"[3:a]showwaves=s={ww}x{wh}:mode=cline:rate={FPS}:colors=0x{col}:scale=sqrt:draw=full,format=rgba[gw];"
          f"[bg][ov]overlay=0:0:shortest=1[a];[a][hw]overlay={wx}:{hy}[b];[b][gw]overlay={wx}:{gy},format=yuv420p[v];"
          f"[4:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[au]")
    log("encoding...")
    t0 = time.time()
    ff("-stream_loop", "-1", "-i", bg, "-f", "concat", "-safe", "0", "-i", os.path.join(work, "ov.txt"),
       "-i", os.path.join(work, "host.wav"), "-i", os.path.join(work, "guest.wav"), "-i", os.path.join(work, "mix.wav"),
       "-filter_complex", fc, "-map", "[v]", "-map", "[au]", "-t", f"{total:.3f}",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", os.environ.get("CRF", "30"), "-tune", "stillimage",
       "-r", str(FPS), "-g", str(FPS * 10), "-c:a", "aac", "-b:a", "96k", "-ac", "1",
       "-movflags", "+faststart", out_mp4)
    log(f"encoded in {time.time() - t0:.0f}s -> {out_mp4} ({os.path.getsize(out_mp4) / 1048576:.1f} MB)")
    if os.path.getsize(out_mp4) > 95_000_000:      # Postiz pulls from raw.githubusercontent.com: files must stay under 100 MB
        log("over 95 MB, re-encoding at 1280x720")
        tmp = out_mp4 + ".720.mp4"
        ff("-i", out_mp4, "-vf", "scale=1280:720", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
           "-tune", "stillimage", "-g", str(FPS * 10), "-c:a", "copy", "-movflags", "+faststart", tmp)
        os.replace(tmp, out_mp4)
        log(f"now {os.path.getsize(out_mp4) / 1048576:.1f} MB")

    # ---- thumbnail, chapters, description, timeline
    frame = os.path.join(work, "bgframe.png")
    ff("-i", bg, "-frames:v", "1", frame)
    P.thumbnail(Image.open(frame), stem + "-thumb.png")
    chap = [f"{fmt_ts(0)} {ep['segments'][0]['heading']}"]
    for si in sorted(seg_starts):
        if si: chap.append(f"{fmt_ts(seg_starts[si])} {ep['segments'][si]['heading']}")
    open(stem + ".chapters.txt", "w").write("\n".join(chap) + "\n")
    open(stem + ".description.txt", "w").write(make_description(ep, B, chap, [c for _, c in broll_imgs.values()]))
    json.dump({"slug": ep["slug"], "brand": ep["brand"], "duration": total,
               "events": [{k: e[k] for k in ("seg", "line", "who", "text", "card", "start", "end")} for e in events]},
              open(stem + ".timeline.json", "w"), indent=0)
    log("done")


if __name__ == "__main__":
    args = sys.argv[1:]
    res, test = (1920, 1080), None
    if "--res" in args: i = args.index("--res"); res = tuple(map(int, args[i + 1].split("x"))); del args[i:i + 2]
    if "--test" in args: i = args.index("--test"); test = int(args[i + 1]); del args[i:i + 2]
    build(args[0], args[1], res, test)
