"""One command per step for the combined nightly run (all channels), so the scheduled task makes few tool calls.

    cd engine
    python3 nightly.py voices <script.json> ...      # ONE Kaggle run for every line tonight + fail-safe decision
    python3 nightly.py render <script.json>=<out.mp4> ...   # render everything (shorts, memes, sleep, podcasts)
    python3 nightly.py qc <out.mp4> ...              # durations, sizes and one contact sheet (qc.png) to glance at
    python3 nightly.py photos <pod-x.timeline.json>  # numbered sheet of every photo an episode used (photos.png)
    python3 nightly.py block <pod-x.timeline.json> 3 17 ...   # never use those photos again (then re-render)

Script types are detected from the JSON: Snortlo story/meme parts ("beats"), sleep stories ("stories"),
podcast episodes ("segments"). Podcast Shorts are cut automatically after the episode renders.

Fail-safe (owner's rule, Oct 27, 2026): Kaggle (Qwen3 house voices) down once -> podcasts are DEFERRED to the next
night and Snortlo retries Kaggle once after 15 minutes; Kaggle down twice in a row -> everything uses Chatterbox on
this machine (same voice clips), then Kokoro as the last resort. `voices` prints a JSON decision and writes
VOICE_ENGINE for `render` into .voice_engine.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import voice_backend as VB

ENGINE_FILE = os.path.join(HERE, ".voice_engine")


def kind(d):
    if "segments" in d: return "podcast"
    if "stories" in d: return "sleep"
    return "short"


def lines_for(path):
    """Exactly the (voice, text) pairs each renderer will ask for, so tonight's Kaggle run covers them all."""
    d = json.load(open(path)); k = kind(d); out = []
    if k == "short":
        v0 = d.get("voice", "af_heart")
        out = [(b.get("voice", v0), b["text"]) for b in d["beats"] if b.get("text", "").strip()]
    elif k == "podcast":
        import podcast as P
        from podcast_brands import BRANDS
        host, guest = BRANDS[d["brand"]]["host"], d["guest"]
        for seg in d["segments"]:
            for ln in seg["lines"]:
                for s in P.sentences(ln["text"]):
                    out.append(((host if ln["who"] == "host" else guest)["voice"], s))
    else:
        import longform as L
        v = d.get("voice", "af_heart")
        def paras(txt):
            for para in L.paragraphs(txt):
                for _, s in L.sentences(para): out.append((v, s))
        if d.get("intro"): paras(d["intro"])
        for i, st in enumerate(d["stories"], 1):
            if d.get("announce", True):
                title = L.display_title(L.clean(st["title"]))
                out += [(v, f"Story {L.numword(i)}."), (v, title.rstrip(".") + ".")]
            paras(st["text"])
        if d.get("outro"): paras(d["outro"])
    return k, out


def cmd_voices(paths):
    kinds, lines = {}, []
    for p in paths:
        k, ls = lines_for(p); kinds[p] = k; lines += ls
    t0 = time.time()
    ok, msg, fails = VB.prefetch(lines)
    decision = {"kaggle_ok": ok, "kaggle_message": msg, "consecutive_kaggle_failures": fails, "lines": len(lines)}
    if ok:
        engine, defer = "auto", []
    elif fails >= 2:
        engine, defer = "chatterbox", []          # second failure in a row: fall back for everything
    else:
        # first failure: podcasts wait for tomorrow night; Snortlo tries Kaggle once more, then falls back tonight
        defer = [p for p, k in kinds.items() if k == "podcast"]
        snort = [l for p in paths if p not in defer for l in lines_for(p)[1]]
        engine = "chatterbox"
        if snort:
            VB.log("Kaggle failed once; retrying for Snortlo in 15 minutes")
            time.sleep(900)
            ok2, msg2, _ = VB.prefetch(snort)
            decision["snortlo_retry"] = msg2
            if ok2: engine = "auto"
    decision.update({"voice_engine": engine, "deferred_podcasts": defer, "seconds": round(time.time() - t0)})
    open(ENGINE_FILE, "w").write(engine)
    print(json.dumps(decision, indent=1))


def cmd_render(pairs):
    env = dict(os.environ, VOICE_ENGINE=open(ENGINE_FILE).read().strip() if os.path.exists(ENGINE_FILE) else "auto")
    root = os.path.dirname(HERE); results = []
    for pair in pairs:
        src, out = pair.split("=", 1)
        k = kind(json.load(open(src))); t0 = time.time()
        try:
            if k == "short":
                rs = os.path.relpath(os.path.abspath(src), root); ro = os.path.relpath(os.path.abspath(out), root)
                subprocess.run(["bash", os.path.join(HERE, "make_video.sh"), rs, ro], check=True, env=env)
            elif k == "sleep":
                subprocess.run([sys.executable, "longform.py", src, out], check=True, cwd=HERE, env=env)
            else:
                subprocess.run([sys.executable, "podcast.py", src, out], check=True, cwd=HERE, env=env)
                subprocess.run([sys.executable, "podcast_shorts.py", src, out], check=True, cwd=HERE, env=env)
            results.append({"src": src, "out": out, "ok": True, "seconds": round(time.time() - t0)})
        except subprocess.CalledProcessError as e:
            results.append({"src": src, "out": out, "ok": False, "error": str(e)[:200]})
    print(json.dumps({"voice_engine": env["VOICE_ENGINE"], "results": results}, indent=1))


def cmd_qc(files):
    from PIL import Image
    rows, thumbs = [], []
    for f in files:
        try:
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                       capture_output=True, text=True).stdout.strip())
        except ValueError:
            rows.append({"file": f, "error": "unreadable"}); continue
        mb = os.path.getsize(f) / 1048576
        rows.append({"file": os.path.basename(f), "seconds": round(dur, 1), "MB": round(mb, 1), "over_99MB": mb > 99})
        for frac in (0.25, 0.7):
            tp = f"/tmp/qc_{len(thumbs)}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(dur * frac), "-i", f, "-frames:v", "1",
                            "-vf", "scale=-2:360", tp])
            if os.path.exists(tp): thumbs.append(Image.open(tp).convert("RGB"))
    if thumbs:
        w = max(t.width for t in thumbs); cols = 4; h = 360
        sheet = Image.new("RGB", (w * cols, h * ((len(thumbs) + cols - 1) // cols)))
        for i, t in enumerate(thumbs): sheet.paste(t, ((i % cols) * w, (i // cols) * h))
        sheet.thumbnail((2400, 2400)); sheet.save(os.path.join(HERE, "qc.png"))
    print(json.dumps(rows, indent=1)); print("contact sheet: engine/qc.png" if thumbs else "no frames")


def cmd_photos(args):
    """Numbered contact sheet of every photo an episode used, to spot people / off-topic shots fast."""
    from PIL import Image, ImageDraw, ImageFont
    t = json.load(open(args[0])); seen = []
    for sh in t.get("shots", []):
        if sh["img"] and sh["img"] not in [s["img"] for s in seen]: seen.append(sh)
    f = ImageFont.truetype(os.path.join(HERE, "fonts", "Archivo.ttf"), 20); cols, tw, th = 10, 220, 138
    rows = (len(seen) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 24)), "white"); d = ImageDraw.Draw(sheet)
    for k, sh in enumerate(seen):
        im = Image.open(sh["img"]).convert("RGB"); im.thumbnail((tw - 4, th)); x, y = (k % cols) * tw, (k // cols) * (th + 24)
        sheet.paste(im, (x, y)); d.text((x + 2, y + th + 1), f"{k} {(sh['credit'] or {}).get('query', '')[:14]}", font=f, fill="black")
    out = os.path.join(HERE, "photos.png"); sheet.save(out)
    print(f"{len(seen)} photos -> engine/photos.png (block bad ones: nightly.py block {args[0]} <numbers>)")


def cmd_block(args):
    t = json.load(open(args[0])); seen = []
    for sh in t.get("shots", []):
        if sh["img"] and sh["img"] not in [s["img"] for s in seen]: seen.append(sh)
    new = [seen[int(i)]["credit"]["source"] for i in args[1:] if seen[int(i)].get("credit")]
    with open(os.path.join(HERE, "broll_block.txt"), "a") as fh:
        for u in new: fh.write(u + "\n")
    print(f"blocked {len(new)} photos; re-render the episode")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"voices": cmd_voices, "render": cmd_render, "qc": cmd_qc, "photos": cmd_photos, "block": cmd_block}[cmd](args)
