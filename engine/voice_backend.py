"""One voice layer for every channel (Snortlo shorts, sleep stories, Keegix/Staffkin podcasts).

Main engine: Qwen3-TTS on Kaggle's free GPU, cloning the house voices in engine/voices/ (approved Oct 27, 2026).
Fail-safe (owner's rule): Kaggle down once -> podcasts wait a night, Snortlo retries once; down again ->
Chatterbox-Turbo on this machine's CPU, cloning the SAME voice clips; if that breaks too -> Kokoro (the old voices,
same names). Everything is spoken at 1.10x unless a caller asks otherwise (sleep stories stay slow).

Use from the engines:
    from voice_backend import voice_lines
    arrays = voice_lines([("af_bella", "Hello."), ...], tempo=1.10)   # list of float32 arrays, 24 kHz mono

Cache: raw takes live in VOICE_CACHE (default /tmp/snortlo-voice) keyed by engine|voice|text, so a second render
of the same script costs nothing. prefetch() voices a whole night's lines in ONE Kaggle run.

VOICE_ENGINE env: "auto" (default: cache -> Kaggle -> Chatterbox -> Kokoro), "kaggle", "chatterbox", "kokoro".
"""
import hashlib, json, os, subprocess, sys, tempfile, time

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 24000
CACHE = os.environ.get("VOICE_CACHE", "/tmp/snortlo-voice")
STATE = os.path.join(os.path.dirname(HERE), "voice_state.json")
DEFAULT_TEMPO = 1.10
CBX_VENV = os.environ.get("CBX_VENV", "/tmp/cbx-venv")


def log(*a): print("[voice]", *a, flush=True)


def _key(engine, voice, text):
    return hashlib.sha1(f"{engine}|{voice}|{text}".encode()).hexdigest()[:20]


def _cache_path(engine, voice, text):
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, _key(engine, voice, text) + ".wav")


def _load(path):
    a, sr = sf.read(path, dtype="float32")
    if a.ndim > 1: a = a.mean(1)
    if sr != SR:
        from scipy.signal import resample_poly
        g = np.gcd(sr, SR); a = resample_poly(a, SR // g, sr // g).astype(np.float32)
    return a


def _tempo(a, tempo):
    """Speed up/slow down without changing pitch (ffmpeg atempo)."""
    if abs(tempo - 1.0) < 1e-3 or len(a) == 0: return a
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.wav"), os.path.join(d, "o.wav")
        sf.write(i, a, SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", i, "-af", f"atempo={tempo:.3f}", o], check=True)
        return _load(o)


def _trim(a):
    nz = np.where(np.abs(a) > 0.008)[0]
    if len(nz): a = a[max(nz[0] - int(.03 * SR), 0): nz[-1] + int(.12 * SR)]
    f = min(len(a) // 2, int(.010 * SR))
    if f:
        a = a.copy(); a[:f] *= np.linspace(0, 1, f, dtype=np.float32); a[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return a.astype(np.float32)


# ------------------------------------------------------------------ engines
def _kaggle(todo):
    """todo: list of (voice, text). Fills the cache. Returns (ok, message)."""
    jobs = [{"id": _key("qwen3", v, t), "voice": v, "text": t} for v, t in todo]
    with tempfile.TemporaryDirectory() as d:
        jf = os.path.join(d, "jobs.json"); json.dump(jobs, open(jf, "w"))
        out = os.path.join(d, "out")
        r = subprocess.run([sys.executable, os.path.join(HERE, "kaggle_tts.py"), "clone", jf, out],
                           capture_output=True, text=True)
        msg = (r.stdout + r.stderr).strip().splitlines()[-1:] or ["no output"]
        if r.returncode != 0: return False, msg[0]
        n = 0
        for j in jobs:
            p = os.path.join(out, j["id"] + ".wav")
            if os.path.exists(p):
                os.replace(p, os.path.join(CACHE, j["id"] + ".wav")); n += 1
        return n > 0, msg[0]


def _ensure_chatterbox():
    py = os.path.join(CBX_VENV, "bin", "python")
    if os.path.exists(py): return py
    log("installing Chatterbox-Turbo (CPU) for the fallback, ~5 min")
    sh = f"""set -e
python3 -m venv {CBX_VENV}
P={CBX_VENV}/bin/pip
$P install -q --index-url https://download.pytorch.org/whl/cpu "torch==2.11.0+cpu" "torchaudio==2.11.0+cpu"
$P install -q --no-deps chatterbox-tts==0.1.7
$P install -q "numpy>=2" librosa==0.11.0 s3tokenizer "transformers==5.2.0" diffusers==0.29.0 resemble-perth conformer==0.3.2 safetensors==0.5.3 pyloudnorm omegaconf soundfile huggingface-hub
$P install -q --force-reinstall --no-deps --index-url https://download.pytorch.org/whl/cpu "torch==2.11.0+cpu" "torchaudio==2.11.0+cpu"
SP=$({CBX_VENV}/bin/python -c 'import chatterbox,os;print(os.path.dirname(chatterbox.__file__))')
sed -i 's/mel_spec = self._mel_filters.to(self.device) @ magnitudes$/mel_spec = self._mel_filters.to(self.device).float() @ magnitudes.float()/' $SP/models/s3tokenizer/s3tokenizer.py
sed -i "s/^        ref_16k_wav = librosa.resample(s3gen_ref_wav, orig_sr=S3GEN_SR, target_sr=S3_SR)$/        ref_16k_wav = librosa.resample(s3gen_ref_wav.astype('float32'), orig_sr=S3GEN_SR, target_sr=S3_SR).astype('float32')/" $SP/tts_turbo.py
sed -i "s/^        s3gen_ref_wav = s3gen_ref_wav\\[:self.DEC_COND_LEN\\]$/        s3gen_ref_wav = s3gen_ref_wav[:self.DEC_COND_LEN].astype('float32')/" $SP/tts_turbo.py
"""
    subprocess.run(["bash", "-c", sh], check=True)
    return py


CBX_SCRIPT = r'''
import json, sys, soundfile as sf
from chatterbox.tts_turbo import ChatterboxTurboTTS
m = ChatterboxTurboTTS.from_pretrained(device="cpu")
for j in json.load(open(sys.argv[1])):
    w = m.generate(j["text"], audio_prompt_path=j["ref"])
    sf.write(j["out"], w.squeeze().cpu().numpy(), m.sr)
'''


def _chatterbox(todo):
    try:
        py = _ensure_chatterbox()
        jobs = [{"text": t, "ref": os.path.join(HERE, "voices", v + ".wav"),
                 "out": os.path.join(CACHE, _key("chatterbox", v, t) + ".wav")} for v, t in todo]
        with tempfile.TemporaryDirectory() as d:
            jf, sp = os.path.join(d, "j.json"), os.path.join(d, "cbx.py")
            json.dump(jobs, open(jf, "w")); open(sp, "w").write(CBX_SCRIPT)
            subprocess.run([py, sp, jf], check=True, cwd=d)
        return True, f"{len(jobs)} lines on Chatterbox (CPU)"
    except Exception as e:
        return False, f"Chatterbox failed: {e!r}"[:300]


_K = None
def _kokoro(todo):
    global _K
    from kokoro_onnx import Kokoro
    if _K is None:
        _K = Kokoro(os.path.join(HERE, "models/kokoro-v1.0.onnx"), os.path.join(HERE, "models/voices-v1.0.bin"))
    for v, t in todo:
        s, _ = _K.create(t, voice=v, speed=1.0, lang="en-gb" if v.startswith("b") else "en-us")
        sf.write(os.path.join(CACHE, _key("kokoro", v, t) + ".wav"), np.asarray(s, np.float32), SR)
    return True, f"{len(todo)} lines on Kokoro"


ORDER = {"auto": ["qwen3", "chatterbox", "kokoro"], "kaggle": ["qwen3"], "chatterbox": ["chatterbox", "kokoro"],
         "kokoro": ["kokoro"]}
RUN = {"qwen3": _kaggle, "chatterbox": _chatterbox, "kokoro": _kokoro}
LAST_ENGINE = {}


def _cached(engine, v, t):
    return os.path.exists(_cache_path(engine, v, t))


def _known_voice(v):
    return os.path.exists(os.path.join(HERE, "voices", v + ".wav"))


def voice_lines(lines, tempo=DEFAULT_TEMPO, engine=None):
    """lines: [(voice, text)] -> list of float32 arrays (trimmed, 1.10x). Never returns silence silently:
    raises RuntimeError only if every engine fails."""
    engine = engine or os.environ.get("VOICE_ENGINE", "auto")
    order = ORDER[engine]
    result = [None] * len(lines)
    for eng in order:
        # a line already voiced by a better engine earlier tonight is reused
        missing = [i for i, (v, t) in enumerate(lines) if result[i] is None and not _cached(eng, v, t)]
        if eng in ("qwen3", "chatterbox"):
            missing = [i for i in missing if _known_voice(lines[i][0])]
        todo = sorted({lines[i] for i in missing})
        if todo:
            ok, msg = RUN[eng](todo)
            log(eng, "->", msg)
        for i, (v, t) in enumerate(lines):
            if result[i] is None and _cached(eng, v, t):
                result[i] = _tempo(_trim(_load(_cache_path(eng, v, t))), tempo)
                LAST_ENGINE[eng] = LAST_ENGINE.get(eng, 0) + 1
        if all(r is not None for r in result): return result
    raise RuntimeError(f"no voice engine produced {sum(r is None for r in result)} lines (tried {order})")


# ------------------------------------------------------------------ fail-safe state (committed to the repo)
def _state():
    try: return json.load(open(STATE))
    except Exception: return {"kaggle_failures": []}


def record_kaggle(ok, note=""):
    s = _state()
    if ok: s["kaggle_failures"] = []
    else: s["kaggle_failures"].append({"at": time.strftime("%Y-%m-%d %H:%M"), "note": note[:200]})
    s["kaggle_failures"] = s["kaggle_failures"][-10:]
    json.dump(s, open(STATE, "w"), indent=1)
    return len(s["kaggle_failures"])


def prefetch(lines):
    """Voice a whole night's lines in ONE Kaggle run. Returns (ok, message, consecutive_failures)."""
    todo = sorted({(v, t) for v, t in lines if _known_voice(v) and not _cached("qwen3", v, t)})
    if not todo: return True, "all lines already cached", 0
    ok, msg = _kaggle(todo)
    if ok:
        missing = [x for x in todo if not _cached("qwen3", *x)]
        if missing: msg += f" ({len(missing)} lines missing, those fall back)"
    n = record_kaggle(ok, msg)
    return ok, msg, n


if __name__ == "__main__":
    # quick self-test: python3 voice_backend.py "af_bella" "Hello there, this is a test."
    a = voice_lines([(sys.argv[1], sys.argv[2])])[0]
    sf.write("voice_test.wav", a, SR); print("voice_test.wav", round(len(a) / SR, 2), "s", LAST_ENGINE)
