"""Cut the 5 Shorts / Reels from a rendered podcast episode (1080x1920, 30-60 s each).

    cd engine && python3 podcast_shorts.py ../podcasts/<brand>/<slug>.json ../media/pod-<slug>.mp4

Needs <stem>.timeline.json from podcast.py. Uses the script's "shorts" list:
    {"title": "on-screen hook", "from": [seg, line], "to": [seg, line], "caption": "post caption"}
Writes ../media/pod-<slug>-short1.mp4 … short5.mp4 and <stem>.shorts.json (file, title, caption, duration).

Layout keeps text out of the top 250 px and bottom 400 px (Reels / Shorts UI), per the brand bibles.
Visual-first (Oct 27, 2026): the same moving CC0 photos as the episode play in a 960x720 window, with the hook
title above and big captions below; info cards cover the photo while they're up. One small "AI voices" note.
"""
import json, os, sys, time

from PIL import Image, ImageDraw

import subprocess
import podcast as P_
from podcast import (BRANDS, DW, DH, FPS, Painter, background_loop, font, wrap, tracked, hexrgb, ff, log, CACHE,
                     display_text, base_frames, gradient_img)
PW, PH = 960, 720           # photo window

VW, VH = 1080, 1920
TAIL = 1.6          # seconds of end card after the last word


def panel_crop(P, ev):
    im = Image.new("RGBA", (DW, DH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if ev["card"]: P.panel_card(im, d, ev["card"])
    else: P.panel_default(im, d, ev["seg"])
    x0, y0, x1, y1 = P_.CARD_BOX
    box = im.crop((x0 - 10, y0 - 10, x1 + 10, y1 + 30))      # panel plus its shadow
    s = 960 / box.width
    return box.resize((960, int(box.height * s)), Image.LANCZOS)


def frame(P, B, ep, sh, ev, path, end=False):
    """Returns the y of the photo window."""
    im = Image.new("RGBA", (VW, VH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = lambda k, a=255: hexrgb(B[k], a)
    logo = P.logo
    im.alpha_composite(logo, ((VW - logo.width) // 2, 262))
    d.text((VW / 2, 352), B["show"], font=font(B["ui"], 26), fill=c("on_dark_muted"), anchor="ms")
    hf = font(B["head"], 66)
    lines = wrap(d, sh["title"], hf, 940, 3)
    y = 400
    for l in lines:
        d.text((VW / 2, y), l, font=hf, fill=c("on_dark"), anchor="mt"); y += 74
    d.rectangle((VW / 2 - 60, y + 14, VW / 2 + 60, y + 21), fill=c("accent"))
    py = y + 50
    if end:
        d.text((VW / 2, py + 200), "Full episode on YouTube", font=font(B["ui"], 44), fill=c("on_dark_muted"), anchor="mm")
        d.text((VW / 2, py + 280), B["show"], font=font(B["head"], 76), fill=c("on_dark"), anchor="mm")
        d.text((VW / 2, py + 380), B["cta"], font=font(B["ui"], 38), fill=c("on_dark_muted"), anchor="mm")
    else:
        if ev["card"]:
            pan = panel_crop(P, ev)
            im.alpha_composite(pan, ((VW - pan.width) // 2, py + (PH - pan.height) // 2))
        d.text((60 + PW - 16, py + PH - 16), B["footer"].split(" · ")[0], font=font(B["ui"], 18),
               fill=(255, 255, 255, 190), anchor="rs")
        cy = py + PH + 30
        who = B["host"] if ev["who"] == "host" else ep["guest"]
        d.text((300, cy + 40), who["name"].upper(), font=font(B["ui_bold"], 30), fill=c("accent"), anchor="ls")
        cf, lh = font(B["caption"], 50), 62
        txt = display_text(ev["text"])
        cl = wrap(d, txt, cf, 960)
        if len(cl) > 3: cf, lh = font(B["caption"], 42), 52; cl = wrap(d, txt, cf, 960, 4)
        for i, l in enumerate(cl):
            d.text((62, cy + 112 + i * lh), l, font=cf, fill=(0, 0, 0, 110), anchor="ls")
            d.text((60, cy + 110 + i * lh), l, font=cf, fill=c("on_dark"), anchor="ls")
    im.save(path, compress_level=3)
    return py


def build(script_path, ep_mp4):
    ep = json.load(open(script_path)); B = BRANDS[ep["brand"]]
    stem = os.path.splitext(ep_mp4)[0]
    tl = json.load(open(stem + ".timeline.json"))
    P = Painter(B, ep, ep["guest"], {}, DW, DH)
    shots = tl.get("shots") or []
    blank = gradient_img(B, PW, PH, os.path.join(CACHE, f"grad-{ep['brand']}-{PW}x{PH}.png"))
    bg = background_loop(B, VW, VH, os.path.join(CACHE, f"bg-{ep['brand']}-{VW}x{VH}.mp4"))
    out = []
    for k, sh in enumerate(ep.get("shorts", [])[:5], 1):
        lo, hi = tuple(sh["from"]), tuple(sh["to"])
        evs = [e for e in tl["events"] if lo <= (e["seg"], e["line"]) <= hi]
        if not evs:
            log(f"short {k}: no lines in range {lo}-{hi}, skipped"); continue
        t0, t1 = max(evs[0]["start"] - 0.25, 0), evs[-1]["end"] + 0.35
        dur = t1 - t0 + TAIL
        work = os.path.join(CACHE, ep["slug"], f"short{k}"); os.makedirs(work, exist_ok=True)
        seq, photo_y = [], None
        for i, e in enumerate(evs):
            name = os.path.join(work, f"s{i:03d}.png")
            photo_y = frame(P, B, ep, sh, e, name)
            a = 0 if i == 0 else e["start"] - t0
            b = (evs[i + 1]["start"] - t0) if i + 1 < len(evs) else (t1 - t0)
            seq.append((name, b - a))
        endp = os.path.join(work, "end.png"); frame(P, B, ep, sh, None, endp, end=True); seq.append((endp, TAIL))
        with open(os.path.join(work, "ov.txt"), "w") as f:
            for name, d_ in seq: f.write(f"file '{name}'\nduration {max(d_, 1 / FPS):.4f}\n")
            f.write(f"file '{seq[-1][0]}'\n")
        clip = os.path.join(work, "photos.mp4")
        if shots:
            pr = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                   "-s", f"{PW}x{PH}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                                   "-crf", "18", "-pix_fmt", "yuv420p", clip], stdin=subprocess.PIPE)
            for fr in base_frames(shots, PW, PH, t0, t1, blank): pr.stdin.write(fr)
            pr.stdin.close(); pr.wait()
        else:
            ff("-loop", "1", "-i", blank, "-t", f"{t1 - t0:.3f}", "-r", str(FPS), "-pix_fmt", "yuv420p", clip)
        col = B["accent"].lstrip("#")
        py = photo_y or 600
        fc = (f"[0:v]trim=duration={dur:.3f},setpts=PTS-STARTPTS[bg];[1:v]fps={FPS},format=rgba[ov];"
              f"[2:v]setpts=PTS-STARTPTS[ph];"
              f"[3:a]atrim=duration={t1 - t0:.3f},apad=pad_dur={TAIL},asplit[a1][a2];"
              f"[a1]showwaves=s=210x48:mode=cline:rate={FPS}:colors=0x{col}:scale=sqrt:draw=full,format=rgba[w];"
              f"[bg][ph]overlay=60:{py}:eof_action=pass[x0];[x0][ov]overlay=0:0:shortest=1[x];"
              f"[x][w]overlay=60:{py + PH + 30 + 4}:shortest=1,format=yuv420p[v]")
        mp4 = f"{stem}-short{k}.mp4"
        ff("-stream_loop", "-1", "-i", bg, "-f", "concat", "-safe", "0", "-i", os.path.join(work, "ov.txt"),
           "-i", clip, "-ss", f"{t0:.3f}", "-i", ep_mp4, "-filter_complex", fc, "-map", "[v]", "-map", "[a2]",
           "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-r", str(FPS),
           "-g", str(FPS * 2), "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", mp4)
        out.append({"file": os.path.basename(mp4), "title": sh["title"], "caption": sh.get("caption", ""),
                    "duration": round(dur, 1)})
        log(f"short {k}: {dur:.0f}s -> {mp4} ({os.path.getsize(mp4) / 1048576:.1f} MB)")
    json.dump(out, open(stem + ".shorts.json", "w"), indent=1)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
