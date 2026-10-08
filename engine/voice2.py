"""Voiceover v2: faster, punchier, less robotic.
- Kokoro af_heart (its most natural voice) at ~1.2x, tight gaps like viral story channels
- room left after punchlines for the meme sound
- Whisper (open source) re-listens to get exact word timings for karaoke captions
Writes voice.wav, bruh.wav, timing.json"""
import json, sys, numpy as np, soundfile as sf
from scipy.signal import butter, lfilter
from kokoro_onnx import Kokoro
from faster_whisper import WhisperModel

story = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "story.json"))
VOICE, BASE = story.get("voice", "af_heart"), story.get("speed", 1.2)
PUNCH = {"vineboom", "bruh", "rimshot", "sadtrombone", "airhorn", "crickets", "dundun"}
k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
SR = 24000

def say(text, speed, voice=VOICE):
    s, _ = k.create(text, voice=voice, speed=speed, lang="en-us")
    nz = np.where(np.abs(s) > 0.008)[0]
    return s[max(nz[0] - 300, 0): nz[-1] + 900].astype(np.float64)

audio, t, beats = [np.zeros(int(SR * 0.08))], 0.08, []
for i, b in enumerate(story["beats"]):
    sp = BASE * (0.9 if b.get("slow") else 1.0)
    s = say(b["text"], sp); d = len(s) / SR
    beats.append({"i": i, "start": t, "end": t + d})
    gap = 0.06 + (0.42 if b.get("sfx") in PUNCH else 0) + b.get("pause", 0)
    audio += [s, np.zeros(int(SR * gap))]; t += d + gap
audio.append(np.zeros(int(SR * 0.5)))
wav = np.concatenate(audio)
b_, a_ = butter(2, 70 / (SR / 2), "high"); wav = lfilter(b_, a_, wav)
wav = wav / np.max(np.abs(wav)) * 0.95
sf.write("voice.wav", wav, SR)
sf.write("bruh.wav", say("Bruhh.", 0.8, "am_fenrir"), SR)

# exact word timings
wm = WhisperModel("base.en", device="cpu", compute_type="int8")
from scipy.signal import resample_poly
segs, _ = wm.transcribe(resample_poly(wav, 2, 3).astype(np.float32), word_timestamps=True, vad_filter=False)
words = [w for s in segs for w in s.words]
for b in beats:
    ws = [w for w in words if b["start"] - 0.05 <= (w.start + w.end) / 2 <= b["end"] + 0.05]
    b["words"] = [{"w": w.word.strip(), "s": w.start, "e": w.end} for w in ws] or \
                 [{"w": x, "s": b["start"], "e": b["end"]} for x in story["beats"][b["i"]]["text"].split()]
json.dump({"duration": len(wav) / SR, "beats": beats}, open("timing.json", "w"), indent=1)
print(f"voice: {len(wav)/SR:.1f}s, {len(words)} words timed")
