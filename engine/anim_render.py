"""Turns a story with stage directions into a finished vertical video.
Usage: python3 anim_render.py story.json out.mp4      (STILLS=1.5,10 for preview frames)"""
import json, math, os, subprocess, sys, random
import numpy as np, soundfile as sf
import cairocffi as cairo
import anim as A, sfx

STORY = sys.argv[1] if len(sys.argv) > 1 else "story.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out.mp4"
FPS, W, H = 30, A.W, A.H
story, timing = json.load(open(STORY)), json.load(open("timing.json"))
B, T = story["beats"], timing["beats"]
DUR = max(timing["duration"] + 0.4, story.get("min_seconds", 0))
N = int(DUR * FPS)
PUNCH = sfx.PUNCH
MEME = story.get("format") == "meme"
YOFF = 300 if MEME else 0  # memes: scene sits lower, classic white caption band on top
import zlib
SEED = zlib.crc32((os.path.basename(STORY) + json.dumps(story.get("beats", [])[:1])).encode())
rng_fx = np.random.default_rng(SEED)
# resolve random sound picks once, so voice gaps, camera punches and audio agree
for _b in story["beats"]:
    if str(_b.get("sfx", "")).startswith("random:"):
        _b["sfx"], _ = sfx.get(_b["sfx"], rng_fx)
YEL, WHITE = A.hexc("#FFD23F"), (1, 1, 1)

# voice energy -> mouth
v, vsr = sf.read("voice.wav"); hop = vsr // FPS
rms = np.array([np.sqrt(np.mean(v[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(v) else 0 for i in range(N)])
rms = np.clip(rms / ((np.percentile(rms[rms > 0], 92) if np.any(rms > 0) else 1.0) + 1e-6), 0, 1.3)  # fully silent memes have no voice

def beat_index(t):
    i = 0
    for k, tb in enumerate(T):
        if t >= tb["start"] - 0.12: i = k
    return i

chars = {n: A.Char(n, A.CAST_LOOKS[n]) for n in A.CAST_LOOKS}
state = dict(set=None, cam=[540.0, 820.0, 1.0], red={}, beat=-1)

def punch_at(b, tb):
    """Punchline sounds land after a spoken line; on a silent reaction shot they land as the shot appears."""
    return tb["start"] + 0.05 if not b.get("text", "").strip() else tb["end"] + 0.02

def walk_pose(base, ph, amt=1.0):
    p = dict(base); s = math.sin(ph)
    p.update(lF=24 * s * amt, lB=-24 * s * amt, kF=-38 * max(0, -s) * amt, kB=-38 * max(0, s) * amt,
             aF=base["aF"] - 26 * s * amt, aB=base["aB"] + 26 * s * amt, torso=base["torso"] + 4)
    return p

def frame(n, surf):
    t = n / FPS; c = cairo.Context(surf)
    bi = beat_index(t); b, tb = B[bi], T[bi]; bt = t - tb["start"]; blen = tb["end"] - tb["start"]
    new_beat = bi != state["beat"]
    snap = b["set"] != state["set"]
    if new_beat:
        state["beat"] = bi; state["set"] = b["set"]
    # ---- camera target
    cam = b.get("cam", {}); z = cam.get("zoom", 1.0); fx, fy = 540.0, 820.0
    if "on" in cam and cam["on"] in chars:
        ce = next((x for x in b.get("cast", []) if x["who"] == cam["on"]), None)
        if ce: fx, fy = ce.get("to", ce["x"]) if bt > blen * .6 else ce["x"], A.GROUND - 470
    elif "at" in cam: fx, fy = cam["at"]
    # punch zoom + shake for meme moments
    extra, shake = 0.0, 0.0
    pa = punch_at(b, tb)
    if b.get("sfx") in PUNCH and t > pa:
        dt = t - pa; extra = 0.22 * math.exp(-dt * 2.5); shake = 14 * math.exp(-dt * 6)
    if b.get("meme") == "shake": shake = max(shake, 7)
    if b.get("meme") == "slowzoom": z *= 1 + 0.12 * min(1, bt / max(blen, .1))
    k = 1.0 if snap else 0.14
    state["cam"] = [A.lerp(state["cam"][0], fx, k), A.lerp(state["cam"][1], fy, k), A.lerp(state["cam"][2], z, k)]
    cx, cy, cz = state["cam"]; cz += extra
    sx, sy = (random.uniform(-shake, shake), random.uniform(-shake, shake)) if shake else (0, 0)
    # ---- world
    c.save()
    c.translate(W / 2 + sx, 820 + YOFF + sy); c.scale(cz, cz); c.translate(-cx, -cy)
    st = dict(b.get("state", {})); st["t0"] = tb["start"]
    c.save(); c.translate(-2000, 0); c.restore()
    A.SETS[b["set"]](c, t, st)
    for pr in b.get("props", []):
        if not pr.get("front"): A.draw_prop(c, pr, pr["x"], pr["y"], t)
    speaker = b.get("speaker")
    for ce in b.get("cast", []):
        ch = chars[ce["who"]]; ch.facing = ce.get("facing", 1)
        base = A.POSES[ce.get("pose", "stand")]; target = dict(base)
        act = ce.get("act"); x = ce["x"]; walking = False
        if "to" in ce:
            kk = min(1, bt / max(0.4, blen * .7)); x = A.lerp(ce["x"], ce["to"], A.ease(kk)); walking = kk < 1
        if walking: target = walk_pose(A.POSES["stand"] if ce.get("pose") in (None, "stand") else base, t * 11)
        osc = math.sin(t * 9)
        if act == "talk": target["aF"] += 14 * osc; target["eF"] += 12 * math.sin(t * 7)
        if act == "stir": target["eF"] += 30 * math.sin(t * 8); target["aF"] += 10 * math.cos(t * 8)
        if act == "drink": target["head"] += 6 * math.sin(t * 6); target["eF"] += 6 * math.sin(t * 6)
        if act == "laugh": target["torso"] += 6 * math.sin(t * 16)
        if snap or new_beat and ce.get("snap", True) and not walking and abs(ch.x - x) > 4: ch.x = x
        else: ch.x = x if walking else A.lerp(ch.x, x, 0.3)
        if snap: ch.pose = dict(target)
        else:
            sm = 0.5 if walking else 0.28
            ch.pose = {kk: A.lerp(ch.pose[kk], target[kk], sm) for kk in target}
        fxd = dict(ce.get("fx", {}))
        r_target = fxd.get("red", 0); state["red"][ch.name] = A.lerp(state["red"].get(ch.name, 0), r_target, 0.05 if not snap else 1)
        fxd["red"] = state["red"][ch.name]
        if act == "shake": fxd["dx"] = 5 * math.sin(t * 50)
        if act in ("bounce", "laugh"): fxd["dy"] = -abs(18 * math.sin(t * 8))
        if walking: fxd["dy"] = fxd.get("dy", 0) - 6 * abs(math.sin(t * 11))
        talk = rms[n] if speaker == ch.name and tb["start"] <= t <= tb["end"] else 0
        A.draw_char(c, ch, t, talk, ce.get("face"), ce.get("hold"), fxd)
    for pr in b.get("props", []):
        if pr.get("front"): A.draw_prop(c, pr, pr["x"], pr["y"], t)
    if b.get("bubble"):
        bb = b["bubble"]; s = A.spring(bt - 0.05)
        c.save(); c.translate(bb["x"], bb["y"]); c.scale(max(.01, s), max(.01, s)); A.draw_prop(c, dict(type="bubble", text=bb["text"], tail=bb.get("tail", 30)), 0, 0, t); c.restore()
    cards = b.get("cards", [])
    for i, txt in enumerate(cards):
        ti = tb["start"] + blen * i / len(cards)
        if t >= ti:
            s = A.spring(t - ti, 12, 16); x = 220 + i * 320
            c.save(); c.translate(x, 470); c.rotate((-1) ** i * .06); c.scale(s, s)
            A.rrect(c, -130, -100, 260, 200, 18); A.fill_stroke(c, "#FFFFFF", A.INKC, 8)
            A.rrect(c, -130, -100, 260, 56, 18); A.fill_stroke(c, "#E0453A", A.INKC, 8)
            A.text(c, txt, 0, 30, 80); c.restore()
    c.restore()
    # ---- overlay: header, captions, progress
    if MEME: draw_band(c, b.get("top_text", ""), bt)
    elif b.get("top_text"): draw_top_text(c, b["top_text"], bt)
    draw_header(c, b)
    draw_captions(c, t)
    state["fry"] = b.get("meme") == "deepfry" and t > punch_at(b, tb) - 0.05
    c.set_source_rgb(*YEL); c.rectangle(0, 0, W * n / N, 10); c.fill()

def draw_band(c, txt, bt):
    """Meme layout: solid white band across the top with big black caption text."""
    top = 520
    c.set_source_rgb(1, 1, 1); c.rectangle(0, 0, W, top); c.fill()
    c.set_source_rgb(0.06, 0.05, 0.09); c.rectangle(0, top - 6, W, 6); c.fill()
    if not txt: return
    lines = txt.split("|"); size = 84
    c.select_font_face(A.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    wmax = max(c.text_extents(l)[4] for l in lines); sc = min(1, (W - 120) / max(wmax, 1)); sz = size * sc
    y0 = 240 + (top - 240) / 2 - (len(lines) - 1) * sz * 0.6
    pop = 1 + 0.06 * max(0, 1 - bt * 5)
    for i, l in enumerate(lines):
        c.save(); c.translate(W / 2, y0 + i * sz * 1.2); c.scale(pop, pop); A.text(c, l, 0, 0, sz, (0.05, 0.05, 0.07)); c.restore()

def draw_top_text(c, txt, bt):
    """Classic meme caption: white card at the top with black text. '|' = new line."""
    lines = txt.split("|"); size = 74
    c.select_font_face(A.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    wmax = max(c.text_extents(l)[4] for l in lines); sc = min(1, (W - 140) / max(wmax, 1))
    hh = (len(lines) * size * 1.18 + 50) * sc; s = max(0.01, A.spring(bt, 14, 18))
    c.save(); c.translate(W / 2, 250 + hh / 2); c.scale(s, s)
    A.rrect(c, -W / 2 + 40, -hh / 2, W - 80, hh, 26); A.fill_stroke(c, "#FFFFFF", A.INKC, 6)
    for i, l in enumerate(lines):
        A.text(c, l, 0, -hh / 2 + (25 + size * 1.18 * (i + 0.62)) * sc, size * sc, (0.05, 0.05, 0.07))
    c.restore()

def draw_header(c, b):
    label = story["channel"] + ("  ·  " + story["part"] if story.get("part") else "")
    c.select_font_face(A.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(38)
    tw = c.text_extents(label)[2]
    A.rrect(c, W / 2 - tw / 2 - 34, 140, tw + 68, 70, 35); c.set_source_rgba(0.1, 0.1, 0.13, 0.82); c.fill()
    A.text(c, label, W / 2, 175, 38, WHITE)

words = [w for tb in T for w in tb["words"]]
chunks, cur = [], []
for w in words:
    cur.append(w)
    if len(cur) == 3 or w["w"][-1:] in ".,:?!":
        chunks.append(cur); cur = []
if cur: chunks.append(cur)

def draw_captions(c, t):
    ch = next((k for k in chunks if k[0]["s"] - 0.04 <= t <= k[-1]["e"] + 0.12), None)
    if not ch: return
    size = 96; c.select_font_face(A.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    toks = [w["w"].upper() for w in ch]
    space = size * 0.55
    widths = [c.text_extents(tk)[4] for tk in toks]
    total = sum(widths) + space * (len(toks) - 1)
    s = 0.8 + 0.2 * A.spring(t - ch[0]["s"] + 0.04, 16, 22)
    if total * s > W - 80: s *= (W - 80) / (total * s)
    c.save(); c.translate(W / 2, 1470 + (250 if MEME else 0)); c.scale(s, s)
    x = -total / 2
    cur_i = max([i for i, w in enumerate(ch) if w["s"] - 0.02 <= t] or [0])
    for i, (tk, wd, w) in enumerate(zip(toks, widths, ch)):
        active = i == cur_i
        c.save()
        if active: c.translate(x + wd / 2, 0); c.scale(1.07, 1.07); c.translate(-(x + wd / 2), 0)
        A.text(c, tk, x, 0, size, YEL if active else WHITE, anchor="l", outline=(0.06, 0.05, 0.09))
        c.restore(); x += wd + space
    c.restore()

surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
def render_frame(n):
    frame(n, surf); surf.flush()
    a = np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())[:, :, [2, 1, 0]]
    if state.get("fry"):  # deep-fried meme look: crushed contrast, oversaturated, warm, grainy
        f = a.astype(np.float32); g = f.mean(axis=2, keepdims=True)
        f = (f - g) * 2.2 + g; f = (f - 128) * 1.6 + 128; f[:, :, 0] += 30; f[:, :, 2] -= 25
        f += np.random.default_rng(n).normal(0, 14, f.shape[:2])[:, :, None]
        return np.clip(f, 0, 255).astype(np.uint8)
    return a

if os.environ.get("STILLS"):
    from PIL import Image
    targets = [int(float(x) * FPS) for x in os.environ["STILLS"].split(",")]
    for n in range(max(targets) + 1):  # run through so smoothing state is right
        if n in targets: Image.fromarray(render_frame(n).copy()).save(f"still_{n / FPS:g}.png")
        else: frame(n, surf)
    sys.exit()

# ---- audio
fx = np.zeros(int(DUR * sfx.SR) + sfx.SR * 4)
for b, tb in zip(B, T):
    name = b.get("sfx")
    if not name: continue
    _, s = sfx.get(name, rng_fx); at = punch_at(b, tb) if name in PUNCH else tb["start"] - 0.05
    i = int(max(0, at) * sfx.SR); fx[i:i + len(s)] += s[:len(fx) - i] * (0.8 if name in PUNCH else 0.5)
sf.write("fx.wav", fx[:int(DUR * sfx.SR)], sfx.SR)
sf.write("music.wav", sfx.music(DUR, bpm=story.get("bpm", 96)) * (1 if story.get("music", True) else 0), sfx.SR)
enc = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", "voice.wav", "-i", "fx.wav", "-i", "music.wav", "-filter_complex",
    "[1:a]aresample=48000,apad,asplit[v1][v2];[3:a]volume=0.8[m];[m][v2]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=300[md];"
    f"[v1][2:a][md]amix=inputs=3:normalize=0:weights=1 0.85 0.6,alimiter=limit=0.92,atrim=0:{DUR:.2f}[a]",
    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{DUR:.2f}", OUT], stdin=subprocess.PIPE)
for n in range(N):
    enc.stdin.write(render_frame(n).tobytes())
    if n % 300 == 0: print(f"frame {n}/{N}", flush=True)
enc.stdin.close(); enc.wait(); print("done", OUT, f"{DUR:.1f}s")
