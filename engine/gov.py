"""Congress Moments: funny/chaotic clips from U.S. House floor video, which is public domain
(17 U.S.C. 105; every House floor record says so). Never use C-SPAN's own footage or news uploads.

  python3 engine/gov.py days                       -> recent session days
  python3 engine/gov.py find [YYYYMMDD] [n]        -> top-n candidate moments (writes gov/candidates-<day>.json)
  python3 engine/gov.py render <clip.json> <out.mp4>

clip.json: {"day": "20260916", "start": 1234.5, "end": 1268.0,       # seconds on the caption clock
            "top_text": "When your time runs out|but you keep going",  # meme caption, '|' = new line
            "sfx": [{"t": 12.3, "name": "vineboom"}]}                  # t = seconds from clip start
Rules: one continuous clip, no splicing words, no fake audio over a real person, no AI voices of real people.
"""
import json, math, os, re, subprocess, sys, urllib.request
import numpy as np, soundfile as sf

API = "https://liveproxy-azapp-prod-eastus2-003.azurewebsites.net"
HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

def get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout).read().decode("utf-8", "ignore")

def session_days():
    return [d["_id"] for d in json.loads(get(API + "/sessiondays/"))]

def media(day):
    """(manifest_url, captions_url, rights) for a session day."""
    ev = json.loads(get(f"{API}/broadcastevents/{day}"))
    s = json.dumps(ev)
    m3u8 = re.search(r'https://[^"#]+/east/[^"#]+/manifest\.m3u8', s) or re.search(r'https://[^"#]+/manifest\.m3u8', s)
    vtt = re.search(r'https://[^"#]+/east/[^"#]+/captions\.vtt', s) or re.search(r'https://[^"#]+/captions\.vtt', s)
    rights = ev[0].get("rights", "") if isinstance(ev, list) and ev else ""
    if not (m3u8 and vtt): raise SystemExit(f"no video for {day}")
    if "public domain" not in rights.lower(): raise SystemExit(f"{day}: rights statement missing, skipping")
    return m3u8.group(0), vtt.group(0), rights

def ts(x):
    h, m, s = x.split(":"); return int(h) * 3600 + int(m) * 60 + float(s)

def parse_vtt(txt):
    off = re.search(r"TIME OFFSET:\s*([\d:.]+)", txt); off = ts(off.group(1)) if off else 0.0
    cues = []
    for block in re.split(r"\n\s*\n", txt.replace("\r\n", "\n").replace("\r", "\n")):
        m = re.search(r"([\d:.]+)\s*-->\s*([\d:.]+)[^\n]*\n(.*)", block, re.S)
        if m: cues.append({"s": ts(m.group(1)), "e": ts(m.group(2)), "t": " ".join(m.group(3).split())})
    return cues, off

TRIGGERS = [  # (pattern on the joined caption text, weight)
    (r"WORDS (BE )?TAKEN DOWN", 6), (r"LAUGHTER", 5), (r"REGULAR ORDER", 4), (r"OUT OF ORDER", 4),
    (r"WILL SUSPEND", 4), (r"(GENTLEMAN|GENTLEWOMAN)'?S? TIME HAS EXPIRED", 3), (r"TIME('S| IS| HAS) EXPIRED", 2),
    (r"(HOUSE|COMMITTEE) WILL BE IN ORDER", 3), (r"NOT RECOGNIZED", 3), (r"REMINDS (ALL )?MEMBERS", 3), (r"DECORUM", 3),
    (r"POINT OF ORDER", 2), (r"PARLIAMENTARY INQUIRY", 2), (r"SIT DOWN", 3), (r"EXCUSE ME", 2), (r"ARE YOU KIDDING", 4),
    (r"APPLAUSE", 1), (r"UNANIMOUS CONSENT", -1), (r"THE QUESTION IS ON", -1), (r"PURSUANT TO", -1)]

def find(day, n=8):
    m3u8, vtt, _ = media(day); cues, off = parse_vtt(get(vtt, 120))
    hits = []
    for i, c in enumerate(cues):
        window = " ".join(x["t"] for x in cues[max(0, i - 2): i + 3])
        for pat, w in TRIGGERS:
            if w > 0 and re.search(pat, c["t"] + " " + window): hits.append((c["s"], w)); break
    cands = []
    for t, _ in hits:
        s, e = t - 22, t + 12
        inwin = [c for c in cues if c["s"] >= s and c["e"] <= e]
        if not inwin: continue
        text = " ".join(c["t"] for c in inwin)
        score = sum(w * len(re.findall(p, text)) for p, w in TRIGGERS)
        cands.append({"day": day, "start": round(inwin[0]["s"], 2), "end": round(inwin[-1]["e"], 2), "score": score, "text": text})
    cands.sort(key=lambda c: -c["score"]); keep = []
    for c in cands:  # no overlapping picks
        if all(abs(c["start"] - k["start"]) > 40 for k in keep): keep.append(c)
    keep = keep[:max(n * 2, 10)]
    for c in keep:  # loudness: shouting and gavels score higher
        c["loud"] = loudness(m3u8, c["start"] + off, c["end"] - c["start"]); c["score"] = round(c["score"] + 3 * c["loud"], 2)
    keep.sort(key=lambda c: -c["score"]); keep = keep[:n]
    os.makedirs("gov", exist_ok=True); json.dump(keep, open(f"gov/candidates-{day}.json", "w"), indent=1)
    return keep

SEG = 2.0  # House HLS uses 2-second fMP4 segments, numbered from 0 at the stream start

def fetch(m3u8, start, dur, out, video=True):
    """Download just the segments covering [start, start+dur] (stream clock) and cut them exactly. Much faster than seeking with ffmpeg."""
    base = m3u8.rsplit("/", 1)[0]; tmp = out + ".parts"; os.makedirs(tmp, exist_ok=True)
    k0, k1 = int(max(0, start) // SEG), int((start + dur) // SEG) + 1
    tracks = [("a", "aac/128000")] + ([("v", "h264/3000000")] if video else [])
    for name, path in tracks:
        with open(f"{tmp}/{name}.mp4", "wb") as f:
            f.write(urllib.request.urlopen(f"{base}/{path}/init.mp4", timeout=60).read())
            for k in range(k0, k1 + 1):
                f.write(urllib.request.urlopen(f"{base}/{path}/segment_{k}.m4s", timeout=60).read())
    ins = sum([["-i", f"{tmp}/{n}.mp4"] for n, _ in reversed(tracks)], [])
    maps = ["-map", "0:v", "-map", "1:a"] if video else ["-map", "0:a"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-ss", f"{start - k0 * SEG:.3f}", "-t", f"{dur:.3f}", *maps,
                    *(["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"] if video else []), "-c:a", "aac", "-b:a", "192k", out], check=True, timeout=600)
    subprocess.run(["rm", "-rf", tmp])

def loudness(m3u8, start, dur):
    try:
        fetch(m3u8, start, dur, "/tmp/_loud.m4a", video=False)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "/tmp/_loud.m4a", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             capture_output=True, timeout=120).stdout
        x = np.frombuffer(raw, np.float32)
        if len(x) < 16000: return 0.0
        r = np.array([np.sqrt(np.mean(x[i:i + 1600] ** 2)) for i in range(0, len(x) - 1600, 1600)])
        return float(min(3.0, np.percentile(r, 97) / (np.median(r) + 1e-4) / 3))  # spikes vs normal speech
    except Exception:
        return 0.0

def band_png(top_text, path):
    sys.path.insert(0, HERE); import cairocffi as cairo, anim as A
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, 520); c = cairo.Context(surf)
    c.set_source_rgb(1, 1, 1); c.paint(); c.set_source_rgb(.06, .05, .09); c.rectangle(0, 514, W, 6); c.fill()
    A.rrect(c, W / 2 - 110, 120, 220, 56, 28); c.set_source_rgba(.1, .1, .13, .85); c.fill()
    A.text(c, "Snortlo", W / 2, 148, 32, (1, 1, 1))
    lines = top_text.split("|"); size = 80
    c.select_font_face(A.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); c.set_font_size(size)
    sc = min(1, (W - 110) / max(c.text_extents(l)[4] for l in lines)); sz = size * sc
    y0 = 330 - (len(lines) - 1) * sz * 0.6
    for i, l in enumerate(lines): A.text(c, l, W / 2, y0 + i * sz * 1.2, sz, (.05, .05, .07))
    A.text(c, "U.S. House floor video · public domain", W / 2, 490, 24, (.45, .45, .5), weight=cairo.FONT_WEIGHT_NORMAL)
    surf.write_to_png(path)

def ass_captions(cues, start, end, path):
    def t(x): x = max(0, x); return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Cap,Inter,70,&H00FFFFFF,&H0000D2FF,&H00140F17,&H64000000,-1,0,0,0,100,100,0,0,1,7,0,2,70,70,330,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    out = []
    for cue in cues:
        if cue["e"] < start or cue["s"] > end: continue
        txt = re.sub(r"^[A-Z .'-]+:\s*", "", cue["t"])  # drop "SPEAKER:" labels
        out.append(f"Dialogue: 0,{t(cue['s'] - start)},{t(cue['e'] - start)},Cap,,0,0,0,,{txt}")
    open(path, "w").write(head + "\n".join(out) + "\n")

def whisper_words(path):
    from faster_whisper import WhisperModel
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    m = WhisperModel("base.en", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(np.frombuffer(raw, np.float32), word_timestamps=True, vad_filter=False)
    return [{"w": w.word.strip(), "s": w.start, "e": w.end} for sg in segs for w in sg.words]

def norm(w): return re.sub(r"[^a-z0-9']", "", w.lower())

def align(cues, start, end, words):
    """Caption clock -> local clip clock, using where the caption words actually occur in the audio."""
    import difflib
    cw = [(norm(x), c["s"]) for c in cues if start - 30 <= c["s"] <= end + 30 for x in c["t"].split() if norm(x)]
    ww = [norm(w["w"]) for w in words]
    sm = difflib.SequenceMatcher(None, [a for a, _ in cw], ww, autojunk=False)
    deltas = [words[b + k]["s"] - cw[a + k][1] for a, b, n in sm.get_matching_blocks() if n >= 3 for k in range(n)]
    if not deltas: raise SystemExit("could not line up captions with the audio")
    return float(np.median(deltas))

def ass_from_words(words, path):
    def t(x): x = max(0, x); return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Cap,Inter,84,&H00FFFFFF,&H0000D2FF,&H00140F17,&H64000000,-1,0,0,0,100,100,0,0,1,8,0,2,60,60,300,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    out, chunk = [], []
    for w in words:
        chunk.append(w)
        if len(chunk) == 3 or w["w"][-1:] in ".,?!":
            for i, cw in enumerate(chunk):  # karaoke: the word being said is yellow
                txt = " ".join(("{\\c&H3FD2FF&}" + x["w"].upper() + "{\\c&HFFFFFF&}") if j == i else x["w"].upper() for j, x in enumerate(chunk))
                end = chunk[i + 1]["s"] if i + 1 < len(chunk) else cw["e"] + 0.15
                out.append([cw["s"], end, txt])
            chunk = []
    for i in range(len(out) - 1): out[i][1] = min(out[i][1], out[i + 1][0])  # never two caption lines at once
    open(path, "w").write(head + "\n".join(f"Dialogue: 0,{t(a)},{t(b)},Cap,,0,0,0,,{x}" for a, b, x in out) + "\n")

def render(clip_path, out):
    """Grab a padded window, line captions up with the real audio (Whisper), cut exactly, add band/captions/sfx."""
    sys.path.insert(0, HERE); import sfx
    clip = json.load(open(clip_path)); day = clip["day"]
    m3u8, vtt, _ = media(day); cues, off = parse_vtt(get(vtt, 120))
    s, e = clip["start"], clip["end"]; pad = 20
    work = os.path.join(os.path.dirname(os.path.abspath(out)), "_gov"); os.makedirs(work, exist_ok=True)
    win0 = s + off - 25 - pad  # rough guess at the stream clock; Whisper fixes it below
    raw = f"{work}/window.mp4"; fetch(m3u8, win0, (e - s) + 2 * pad + 25, raw)
    words = whisper_words(raw)
    delta = align(cues, s, e, words)          # local time = caption time + delta
    a, b = s + delta - 0.4, e + delta + 1.0
    if clip.get("end_on_word"):              # end right after a given word (e.g. EXPIRED)
        hit = next((w for w in words if w["s"] >= a and norm(w["w"]) == norm(clip["end_on_word"])), None)
        if hit: b = hit["e"] + clip.get("tail", 1.6)
    a = max(0, a); dur = b - a
    src = f"{work}/src.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-i", raw, "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", src], check=True)
    local = [dict(w, s=w["s"] - a, e=w["e"] - a) for w in words if a <= w["s"] < b]
    band_png(clip.get("top_text", ""), f"{work}/band.png"); ass_from_words(local, f"{work}/cap.ass")
    fx = np.zeros(int((dur + 4) * sfx.SR)); rng = np.random.default_rng(len(clip.get("top_text", "")))
    for hit in clip.get("sfx", []):
        t0 = hit.get("t")
        if "at_word" in hit:
            w = next((w for w in local if norm(w["w"]) == norm(hit["at_word"])), None)
            if not w: continue
            t0 = w["e"] + hit.get("delay", 0.05)
        _, x = sfx.get(hit["name"], rng); i = int(max(0, t0) * sfx.SR); fx[i:i + len(x)] += x[:len(fx) - i] * hit.get("gain", 0.8)
    tail = clip.get("hold_end", 1.2); total = dur + tail   # freeze the last frame while the punch sound plays
    sf.write(f"{work}/fx.wav", fx[:int(total * sfx.SR)], sfx.SR)
    fc = (f"[0:v]tpad=stop_mode=clone:stop_duration={tail},split[a][b];[b]scale=-2:1920,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.15[bg];"
          "[a]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2+170[v1];[v1][1:v]overlay=0:0[v2];"
          f"[v2]ass={work}/cap.ass[v];"
          "[0:a]aresample=48000,apad,volume=1.6[o];[2:a]aresample=48000[f];[o][f]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", f"{work}/band.png", "-i", f"{work}/fx.wav", "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{total:.3f}", out], check=True, timeout=900)
    json.dump({"words": local, "cut": [a, b]}, open(out + ".json", "w"))
    print("done", out, f"{total:.1f}s")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "days": print(session_days()[-30:])
    elif cmd == "find":
        day = sys.argv[2] if len(sys.argv) > 2 else session_days()[-1]
        for c in find(day, int(sys.argv[3]) if len(sys.argv) > 3 else 8): print(json.dumps(c)[:400])
    elif cmd == "render": render(sys.argv[2], sys.argv[3])
