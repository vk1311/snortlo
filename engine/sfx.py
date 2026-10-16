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

# ---------- Oct 2026 additions: generic versions of sound TYPES trending on Shorts/Reels, all made from scratch ----------
def _pad(x, n):
    return np.concatenate([x, np.zeros(max(0, n - len(x)))])[:n]

def bonecrack():
    """Sharp crunchy snap (the 'bone crack' reaction): a few woody clicks plus a body thud."""
    out = np.zeros(int(SR * 0.45))
    for st, g, lo, hi in [(0.0, 1.0, 1500, 6000), (0.018, .7, 900, 4000), (0.04, .5, 2000, 8000), (0.075, .35, 700, 3000)]:
        tt = t_(0.06); c = bp(rng.standard_normal(len(tt)), lo, hi) * env(len(tt), .0002, .006)
        i = int(st * SR); out[i:i + len(c)] += c * g * 6
    tt = t_(0.25); out[:len(tt)] += np.sin(2 * np.pi * np.cumsum(140 * np.exp(-tt * 20) + 60) / SR) * env(len(tt), .001, .04) * .5
    return np.tanh(out * 3) * 0.75

def clownhorn():
    """Bulb-horn 'honk honk' for when someone is the clown of the story."""
    out = []
    for f, d in [(392, .18), (330, .32)]:
        t = t_(d); s = sawtooth(2 * np.pi * np.cumsum(f * (1 + .012 * np.sin(2 * np.pi * 30 * t))) / SR, 0.3)
        s = bp(s, 500, 2600) + 0.3 * bp(s, 2600, 5000)
        out += [s * np.minimum(1, t / .01) * np.minimum(1, (d - t) / .03), np.zeros(int(SR * .07))]
    return np.tanh(np.concatenate(out) * 2.5) * 0.45

def cowbell(f=540, d=0.22):
    t = t_(d); s = np.sign(np.sin(2 * np.pi * f * t)) + np.sign(np.sin(2 * np.pi * f * 1.48 * t))
    return bp(s, 600, 4000) * env(len(t), .001, .07)

def phonk():
    """Short drift-phonk sting: an original 6-hit cowbell figure over a distorted 808. For 'X years later' and flex moments."""
    out = np.zeros(int(SR * 1.9))
    for st, f in [(0, 587), (.15, 587), (.3, 784), (.45, 698), (.6, 587), (.9, 523)]:
        c = cowbell(f); i = int(st * SR); out[i:i + len(c)] += c * .35
    tt = t_(1.4); boom = np.tanh(4 * np.sin(2 * np.pi * np.cumsum(55 * np.exp(-tt * .8) + 33) / SR)) * env(len(tt), .004, .7)
    out[:len(tt)] += boom * .55
    out = lp(out, 9000)
    return out / (np.max(np.abs(out)) + 1e-9) * 0.85

def aura():
    """'+1000 aura' moment: a glassy shimmer that swells into a soft boom."""
    t = t_(0.8); k = (t / t[-1]) ** 2
    sh = sum(np.sin(2 * np.pi * f * (1 + .25 * k) * t) for f in (1760, 2217, 2637, 3520)) * (1 + .5 * np.sin(2 * np.pi * 14 * t))
    boom = vineboom(); tail = boom * .7 + _pad(ding(), len(boom)) * .3
    return np.concatenate([sh * k * 0.06, tail])

def rizz():
    """Cartoon eyebrow-raise 'bwee-oo' glide, for smooth-talker or suspicious moments."""
    t = t_(0.55); f = 500 + 700 * np.sin(np.pi * t / t[-1]) + 35 * np.sin(2 * np.pi * 11 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) ** .5 * 0.32

def reveal():
    """Dramatic 'it was YOU' reveal: a swell into a dark minor stab."""
    t = t_(1.6); stab = sum(sawtooth(2 * np.pi * f * (1 + d) * t) for f in (110, 130.8, 164.8) for d in (-.004, .004))
    stab = lp(stab, 1400) * env(len(t), .005, .6) * 0.12 + np.sin(2 * np.pi * 55 * t) * env(len(t), .005, .8) * 0.4
    return np.concatenate([riser(0.7) * 0.8, reverb(stab, 1.0, 0.35)])

def payding():
    """Generic tap-to-pay success chime (two clean notes), for money jokes."""
    out = np.zeros(int(SR * 0.8))
    for st, f in [(0, 1318.5), (0.11, 1975.5)]:
        tt = t_(0.6); s = (np.sin(2 * np.pi * f * tt) + .3 * np.sin(4 * np.pi * f * tt)) * env(len(tt), .002, .18)
        i = int(st * SR); out[i:i + len(s)] += s * .3
    return out

def textbuzz():
    """Phone vibrating on a table twice, then a soft ping. For 'she texted' / 'mom texted' beats."""
    out = []
    for _ in range(2):
        t = t_(0.32); gate = np.sin(2 * np.pi * 37 * t) > 0
        s = np.sin(2 * np.pi * 165 * t) * (0.6 + 0.4 * gate) + bp(rng.standard_normal(len(t)), 1500, 4000) * 0.15 * gate
        out += [s * np.minimum(1, t / .01) * np.minimum(1, (.32 - t) / .02) * .35, np.zeros(int(SR * .15))]
    return np.concatenate(out + [payding()[:int(SR * .35)] * .6])

def toot():
    """Cartoon fart: a short buzzy wobble. Kept out of random picks; use by name, rarely."""
    t = t_(0.6); f = 85 + 30 * np.sin(2 * np.pi * 7 * t) - 30 * t
    s = sawtooth(2 * np.pi * np.cumsum(f) / SR, 0.2) * (0.7 + 0.3 * np.sin(2 * np.pi * 23 * t))
    return lp(np.tanh(s * 2), 900) * np.sin(np.pi * t / t[-1]) ** .4 * 0.6

def snort():
    """Snortlo's sound logo: two quick piggy snorts with a giggle lift. Plays at the start of every meme."""
    out = np.zeros(int(SR * 0.42))
    for st, f0, d in [(0.0, 120, 0.11), (0.15, 150, 0.14)]:
        t = t_(d); buzz = sawtooth(2 * np.pi * np.cumsum(f0 * (1 + 0.6 * t / d)) / SR)
        grit = rng.standard_normal(len(t)) * 0.5
        s = bp(buzz + grit, 300, 1800) + 0.5 * bp(buzz, 2000, 3200)
        s *= np.sin(np.pi * t / d) ** 0.6
        i = int(st * SR); out[i:i + len(s)] += s
    return np.tanh(out * 1.8) * 0.5

BANK.update({"bonecrack": bonecrack, "clownhorn": clownhorn, "phonk": phonk, "aura": aura, "rizz": rizz,
             "reveal": reveal, "payding": payding, "textbuzz": textbuzz, "toot": toot, "snort": snort})

# ---------- recorded sounds (public domain / CC0, see sounds/CREDITS.md) + our voiced shouts ----------
import os, glob
HERE = os.path.dirname(os.path.abspath(__file__))

def _load(path):
    def f():
        x, r = sf.read(path)
        if x.ndim > 1: x = x.mean(axis=1)
        if r != SR: x = np.interp(np.arange(0, len(x), r / SR), np.arange(len(x)), x)
        return x * 0.9
    return f

for _p in sorted(glob.glob(os.path.join(HERE, "sounds", "*.wav"))):
    BANK[os.path.splitext(os.path.basename(_p))[0]] = _load(_p)

SHOUTS = ["fahh", "huh", "oof", "nooo", "waitwhat", "ayo", "ohno", "wow", "hmm"]  # written by voice2.py as shout_<name>.wav
for _s in SHOUTS:
    BANK[_s] = (lambda s: (lambda: _load(f"shout_{s}.wav")() if os.path.exists(f"shout_{s}.wav") else vineboom()))(_s)

# ---------- layered combos: two or three sounds stacked, the way big meme pages build a punch ----------
def stack(*parts):
    """parts = (name, offset_seconds, gain). Mixed lazily so recorded files and shouts are found."""
    def f():
        clips = [(BANK[n](), off, g) for n, off, g in parts]
        out = np.zeros(max(int(off * SR) + len(c) for c, off, _ in clips))
        for c, off, g in clips:
            i = int(off * SR); out[i:i + len(c)] += c * g
        return out / max(1.0, np.max(np.abs(out)) / 0.95)
    return f

COMBOS = {
    "roast": stack(("vineboom", 0, .9), ("ooh", .22, .8)),             # savage comeback: boom, then crowd 'ooooh'
    "caught": stack(("recordscratch", 0, .9), ("crickets", .45, 1.0)),  # caught red-handed, awkward silence
    "ko": stack(("slap", 0, .9), ("bonecrack", .06, .8), ("ooh", .3, .6)),  # verbal knockout
    "busted": stack(("reveal", 0, .8), ("gasp", .7, .8)),               # the twist lands
    "brokeboi": stack(("payding", 0, .7), ("sadtrombone", .35, .8)),    # payment goes through... balance doesn't
    "smooth": stack(("rizz", 0, .9), ("sparkle", .25, .6)),             # smooth-talker line
    "clowned": stack(("clownhorn", 0, .9), ("laughtrack", .3, .5)),     # someone just got clowned
}
BANK.update(COMBOS)

# Punchline sounds land just after the line, with a pause and a camera punch. Everything else is an accent at the line start.
PUNCH = {"vineboom", "bruh", "rimshot", "sadtrombone", "airhorn", "crickets", "dundun", "fahh", "huh", "oof", "nooo",
         "waitwhat", "metalpipe", "bonk", "sadviolin", "recordscratch", "laughtrack", "ooh", "aww", "gasp", "gong",
         "applause", "crowdcheer", "boo", "buzzer", "success", "fanfare", "sting", "goat", "evillaugh", "yay",
         "angelchoir", "thunder", "glass", "carcrash", "slap", "cashregister",
         "bonecrack", "clownhorn", "phonk", "aura", "reveal", "toot", "ayo", "ohno", "wow", "hmm", *COMBOS}
NO_RANDOM = {"toot", "snort"}  # only when a script asks for it by name

def get(name, rng=None):
    """Sound by name, with a little random pitch/speed so repeats never sound identical.
    name may be 'random:punch' or 'random:accent' to let the engine pick."""
    rng = rng or np.random.default_rng()
    if name.startswith("random:"):
        pool = sorted(PUNCH - NO_RANDOM) if name.endswith("punch") else sorted(set(BANK) - PUNCH - NO_RANDOM)
        name = pool[rng.integers(len(pool))]
    s = BANK[name]()
    k = rng.uniform(0.94, 1.06)  # +-6% pitch/speed
    s = np.interp(np.arange(0, len(s), k), np.arange(len(s)), s)
    return name, s * rng.uniform(0.85, 1.0)
