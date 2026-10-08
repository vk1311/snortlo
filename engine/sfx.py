"""Step 2: sound. Every sound effect and the music bed are synthesized here
from scratch, so there is no licence to track and nothing can get claimed."""
import numpy as np, soundfile as sf

SR = 48000
rng = np.random.default_rng(7)
t_ = lambda d: np.arange(int(SR * d)) / SR

def env(n, a=0.002, r=0.1):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / r)

def pop():
    t = t_(0.12); f = 900 * np.exp(-t * 30) + 250
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.001, 0.03) * 0.8

def ding():
    t = t_(0.9)
    s = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1318.5, 1), (2637, .35), (1975.5, .25)])
    return s * env(len(t), 0.002, 0.25) * 0.35

def tick():
    t = t_(0.06); return np.sin(2 * np.pi * 2200 * t) * env(len(t), 0.0005, 0.008) * 0.6

def whoosh():
    t = t_(0.45); n = rng.standard_normal(len(t))
    # sweep a simple one-pole low-pass
    out, y = np.zeros_like(n), 0.0
    cut = 0.02 + 0.25 * np.sin(np.pi * t / t[-1]) ** 2
    for i, x in enumerate(n):
        y += cut[i] * (x - y); out[i] = y
    return out * np.sin(np.pi * t / t[-1]) ** 2 * 1.4

def boing():
    t = t_(0.5); f = 180 + 120 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 5)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.18) * 0.5

def music(dur, bpm=84):
    """Soft lo-fi bed: electric-piano chords, kick, brushed hat."""
    beat = 60 / bpm; n = int(SR * dur); out = np.zeros(n)
    chords = [[57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65], [52, 55, 59, 62]]  # Am7 Fmaj7 G7 Em7
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    bar, k = beat * 4, 0
    while k * bar < dur:
        s = int(k * bar * SR); ch = chords[k % 4]
        t = t_(bar * 1.1); e = env(len(t), 0.01, 1.3)
        tone = sum(np.sin(2 * np.pi * hz(m) * t) + 0.2 * np.sin(4 * np.pi * hz(m) * t) for m in ch)
        tone *= e * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)) * 0.05
        seg = out[s:s + len(tone)]; seg += tone[:len(seg)]
        for b in range(4):
            bs = s + int(b * beat * SR)
            if b in (0, 2):  # kick
                tk = t_(0.25); kick = np.sin(2 * np.pi * np.cumsum(110 * np.exp(-tk * 25) + 45) / SR) * env(len(tk), .001, .09) * .35
                seg2 = out[bs:bs + len(kick)]; seg2 += kick[:len(seg2)]
            for off in (0, 0.5):  # hat
                hs = bs + int(off * beat * SR); th = t_(0.05)
                hat = rng.standard_normal(len(th)) * env(len(th), .0005, .012) * (.05 if off else .035)
                seg3 = out[hs:hs + len(hat)]; seg3 += hat[:len(seg3)]
        k += 1
    fade = np.minimum(1, np.minimum(np.arange(n) / (SR * 1.5), (n - np.arange(n)) / (SR * 2)))
    return out * fade

BANK = {"pop": pop, "ding": ding, "tick": tick, "whoosh": whoosh, "boing": boing}

# ---------- meme-style sounds, recreated from scratch (originals get Content ID claims) ----------
from scipy.signal import butter, lfilter, sawtooth

def lp(x, f):
    b, a = butter(2, min(f / (SR / 2), 0.99)); return lfilter(b, a, x)
def bp(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band"); return lfilter(b, a, x)
def reverb(x, tail=1.2, mix=0.35):
    out = np.concatenate([x, np.zeros(int(SR * tail))]); wet = np.zeros_like(out)
    for d, g in [(0.029, .5), (0.037, .45), (0.041, .4), (0.053, .35)]:
        k = int(SR * d); buf = out.copy()
        for i in range(k, len(buf)): buf[i] += g * buf[i - k]
        wet += buf
    wet = lp(wet, 4000); wet /= np.max(np.abs(wet)) + 1e-9
    return out * (1 - mix) + wet * mix * np.max(np.abs(x))

def vineboom():
    t = t_(0.9); f = 70 * np.exp(-t * 2) + 38
    s = np.tanh(3 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(len(t), 0.003, 0.35)
    s += lp(rng.standard_normal(len(t)), 300) * env(len(t), 0.001, 0.05) * 0.8
    return reverb(s, 1.0, 0.4) * 0.9

def scratch():
    t = t_(0.5); speed = np.sin(2 * np.pi * 6 * t) * np.sin(np.pi * t / t[-1])
    n = bp(rng.standard_normal(len(t)), 400, 3500)
    tone = np.sin(2 * np.pi * np.cumsum(300 + 900 * np.abs(speed)) / SR) * 0.4
    return (n * 0.6 + tone) * np.abs(speed) * 0.9

def brass(f, d, vib=0.0):
    t = t_(d); ff = f * (1 + vib * np.sin(2 * np.pi * 5.5 * t))
    s = sawtooth(2 * np.pi * np.cumsum(ff) / SR)
    cut = 600 + 2500 * np.minimum(1, t / 0.06) * np.exp(-t * 1.5)
    out = np.zeros_like(s); y = 0.0
    for i in range(len(s)):  # sweeping low-pass = "wah"
        a = 1 - np.exp(-2 * np.pi * cut[i] / SR); y += a * (s[i] - y); out[i] = y
    return out * np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.05)

def sadtrombone():
    parts = [brass(f, d, v) for f, d, v in [(233, .32, 0), (220, .32, 0), (208, .32, 0), (196, 1.1, .03)]]
    return np.concatenate(parts) * 0.45

def dundun():  # dun dun DUNNN
    gap = np.zeros(int(SR * 0.05))
    hits = [brass(196, .22), gap, brass(185, .22), gap, brass(175, 1.4, .02)]
    s = np.concatenate(hits) * 0.5
    t = t_(len(s) / SR); s += np.sin(2 * np.pi * 55 * t) * env(len(t), .01, .8) * 0.3
    return reverb(s, 0.8, 0.3)

def rimshot():  # ba dum tss
    def drum(f, d):
        t = t_(d); return (np.sin(2 * np.pi * f * t) + bp(rng.standard_normal(len(t)), 1500, 6000) * .6) * env(len(t), .001, .05)
    t = t_(0.9); cym = bp(rng.standard_normal(len(t)), 5000, 14000) * env(len(t), .002, .3) * .5
    out = np.zeros(int(SR * 1.3))
    for st, s in [(0, drum(200, .15)), (0.18, drum(140, .2)), (0.38, cym)]:
        i = int(st * SR); out[i:i + len(s)] += s
    return out * 0.7

def slidewhistle(up=True):
    t = t_(0.6); f = (500 + 1300 * (t / t[-1]) ** 1.3) if up else (1800 - 1300 * (t / t[-1]))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * 0.35

def airhorn():
    out = []
    for d in (0.35, 0.12, 0.7):
        t = t_(d); s = sum(sawtooth(2 * np.pi * f * t) for f in (466, 554, 698))
        out += [lp(s, 3000) * np.minimum(1, t / .01) * np.minimum(1, (d - t) / .02) * 0.18, np.zeros(int(SR * .06))]
    return np.concatenate(out)

def riser(d=2.0):
    t = t_(d); w = rng.standard_normal(len(t)); k = (t / d) ** 2; n = lp(w, 900) * (1 - k) + lp(w, 7000) * k
    tone = np.sin(2 * np.pi * np.cumsum(200 + 600 * (t / d) ** 2) / SR)
    return (n * 0.5 + tone * 0.25) * (t / d) ** 2 * 0.6

def heartbeat():
    out = np.zeros(int(SR * 1.6))
    for st in (0, 0.22, 0.8, 1.02):
        tt = t_(0.18); s = np.sin(2 * np.pi * np.cumsum(60 * np.exp(-tt * 8) + 35) / SR) * env(len(tt), .002, .06)
        i = int(st * SR); out[i:i + len(s)] += s * (1 if st in (0, 0.8) else .6)
    return out * 0.9

def crickets():
    t = t_(1.6); chirp = (np.sin(2 * np.pi * 4500 * t) * (np.sin(2 * np.pi * 30 * t) > 0.3) *
                          (np.sin(2 * np.pi * 2.2 * t) > 0.2))
    return lp(chirp, 7000) * 0.12

def bruh():
    """'bruh' comes from the voice engine, pitched down — made in voice.py."""
    import os
    if os.path.exists("bruh.wav"):
        x, r = sf.read("bruh.wav"); idx = np.arange(0, len(x), r / SR * 0.82)
        return np.interp(idx, np.arange(len(x)), x) * 0.9
    return vineboom()

BANK.update({"vineboom": vineboom, "scratch": scratch, "sadtrombone": sadtrombone, "dundun": dundun,
             "rimshot": rimshot, "slideup": slidewhistle, "slidedown": lambda: slidewhistle(False),
             "airhorn": airhorn, "riser": riser, "heartbeat": heartbeat, "crickets": crickets, "bruh": bruh})
