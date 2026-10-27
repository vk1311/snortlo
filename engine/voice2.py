"""Voiceover v2: faster, punchier, less robotic.
- Kokoro af_heart (its most natural voice) at ~1.2x, tight gaps like viral story channels
- room left after punchlines for the meme sound
- Whisper (open source) re-listens to get exact word timings for karaoke captions
Writes voice.wav, bruh.wav, timing.json"""
import json, os, sys, numpy as np, soundfile as sf
from scipy.signal import butter, lfilter
from kokoro_onnx import Kokoro
from faster_whisper import WhisperModel

story = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "story.json"))
VOICE, BASE = story.get("voice", "af_heart"), story.get("speed", 1.2)
from sfx import PUNCH
k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
SR = 24000

def say(text, speed, voice=VOICE):
    s, _ = k.create(text, voice=voice, speed=speed, lang="en-us")
    nz = np.where(np.abs(s) > 0.008)[0]
    return s[max(nz[0] - 300, 0): nz[-1] + 900].astype(np.float64)

# Oct 27, 2026: spoken beats come from voice_backend (Qwen3 house voices on Kaggle, Chatterbox/Kokoro fail-safe),
# all at 1.10x (owner's choice); "slow" beats at 0.99x. The story-level "speed" now only matters on the Kokoro fallback.
from voice_backend import voice_lines, _tempo
_spoken = [(b.get("voice", VOICE), b["text"]) for b in story["beats"] if b.get("text", "").strip()]
_voiced = dict(zip(_spoken, voice_lines(_spoken, tempo=1.0))) if _spoken else {}
TEMPO = float(os.environ.get("VOICE_TEMPO", "1.10"))

audio, t, beats = [np.zeros(int(SR * 0.08))], 0.08, []
for i, b in enumerate(story["beats"]):
    sp = BASE * (0.9 if b.get("slow") else 1.0)
    if b.get("text", "").strip():
        s = _tempo(_voiced[(b.get("voice", VOICE), b["text"])], TEMPO * (0.9 if b.get("slow") else 1.0)).astype(np.float64)
    else:  # silent beat (meme reaction shots): just hold the picture
        s = np.zeros(int(SR * b.get("hold", 1.0)))
    d = len(s) / SR
    beats.append({"i": i, "start": t, "end": t + d})
    sx = str(b.get("sfx", ""))
    spoken = bool(b.get("text", "").strip())
    gap = 0.06 + (0.42 if spoken and (sx in PUNCH or sx == "random:punch") else 0) + b.get("pause", 0)
    audio += [s, np.zeros(int(SR * gap))]; t += d + gap
audio.append(np.zeros(int(SR * 0.5)))
wav = np.concatenate(audio)
b_, a_ = butter(2, 70 / (SR / 2), "high"); wav = lfilter(b_, a_, wav)
wav = wav / (np.max(np.abs(wav)) + 1e-9) * 0.95
sf.write("voice.wav", wav, SR)
sf.write("bruh.wav", say("Bruhh.", 0.8, "am_fenrir"), SR)

# meme shouts, voiced by our own TTS (sound-alikes, never the original clips).
# (text, voice, speed, stretch, pitch, phonemes?)  stretch < 1 = longer, pitch > 1 = higher
SHOUTS = {"fahh": ("Fah!", "am_onyx", 0.7, 0.62, 1.08, False), "huh": ("Huh?", "am_adam", 1.0, 1.0, 1.0, False),
          "oof": ("ˈuːf", "am_fenrir", 0.8, 0.9, 0.95, True), "nooo": ("No!", "am_michael", 0.8, 0.45, 1.0, False),
          "waitwhat": ("Wait, what?", "am_puck", 1.0, 1.0, 1.0, False),
          # Oct 2026: generic reaction words that are everywhere in Shorts/Reels comedy right now
          "ayo": ("Ayo?", "am_fenrir", 0.9, 0.85, 1.0, False), "ohno": ("Oh no.", "am_michael", 0.85, 0.75, 1.0, False),
          "wow": ("Wooow!", "af_bella", 0.85, 0.6, 1.22, False), "hmm": ("Hmmm?", "am_adam", 0.8, 0.6, 0.95, False)}
import subprocess
for name, (txt, vo, sp, stretch, pitch, isph) in SHOUTS.items():
    s, _ = k.create(txt, voice=vo, speed=sp, lang="en-us", is_phonemes=isph)
    nz = np.where(np.abs(s) > 0.008)[0]; s = s[max(nz[0] - 200, 0): nz[-1] + 600]
    sf.write("_shout.wav", s, SR)
    flt = f"asetrate={int(SR * pitch)},aresample={SR},atempo={max(0.5, stretch * pitch):.3f}"
    if stretch * pitch < 0.5: flt += f",atempo={stretch * pitch / 0.5:.3f}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "_shout.wav", "-af", flt, f"shout_{name}.wav"], check=True)

# exact word timings
wm = WhisperModel("base.en", device="cpu", compute_type="int8")
from scipy.signal import resample_poly
segs, _ = wm.transcribe(resample_poly(wav, 2, 3).astype(np.float32), word_timestamps=True, vad_filter=False)
words = [w for s in segs for w in s.words]
for b in beats:
    ws = [w for w in words if b["start"] - 0.05 <= (w.start + w.end) / 2 <= b["end"] + 0.05]
    if not story["beats"][b["i"]].get("text", "").strip(): b["words"] = []; continue
    script = story["beats"][b["i"]]["text"].split()
    if len(ws) == len(script):  # Oct 16: show the script's words with Whisper's timings, so a mishearing never reaches the captions
        b["words"] = [{"w": x, "s": w.start, "e": w.end} for x, w in zip(script, ws)]
    else:  # counts differ: spread the script words over the spoken span, weighted by length
        s0, e0 = (ws[0].start, ws[-1].end) if ws else (b["start"], b["end"])
        tot = sum(len(x) + 2 for x in script); acc = 0.0; b["words"] = []
        for x in script:
            ws_ = s0 + (e0 - s0) * acc / tot; acc += len(x) + 2
            b["words"].append({"w": x, "s": ws_, "e": s0 + (e0 - s0) * acc / tot})
json.dump({"duration": len(wav) / SR, "beats": beats}, open("timing.json", "w"), indent=1)
print(f"voice: {len(wav)/SR:.1f}s, {len(words)} words timed")
