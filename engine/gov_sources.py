"""More public-domain government video sources for Snortlo (companion to gov.py, which covers the House).

  python3 engine/gov_sources.py senate-days [n]        -> recent Senate floor session days (YYYYMMDD clip_id duration)
  python3 engine/gov_sources.py senate-test <date|clip_id> [start_s]   -> 20 s clip to /tmp/senate_test.mp4 + ffprobe
  python3 engine/gov_sources.py nasa <query...>        -> NASA video search (images-api.nasa.gov)
  python3 engine/gov_sources.py nasa-test <query...>   -> downloads 15 s of the first hit to /tmp/nasa_test.mp4 + ffprobe
  python3 engine/gov_sources.py dvids [n]              -> latest DVIDS (U.S. military) videos from the public RSS feed
  python3 engine/gov_sources.py dvids-test             -> downloads 15 s of the newest DVIDS video + ffprobe
  python3 engine/gov_sources.py whitehouse             -> explains why White House video is not usable from here

What works from the cloud workspace (checked 2026-10-08):
  * SENATE floor: senate.gov's own archive is hosted by Granicus (senate.granicus.com, "Senate Floor Proceedings", view_id=2).
    Archive covers 2012 -> 30 Mar 2023 only; after that senate.gov links past floor video to C-SPAN (do NOT use).
    HLS = MPEG-TS, 2 s segments, one variant (1280x720 in 2022-23, 640x360 in e.g. 2020); captions = roll-up WebVTT at
    /videos/<clip_id>/captions.vtt on the same clock as the HLS stream, but they LAG the speech by ~3-6 s (live captioning):
    pad clip starts or re-time with faster-whisper. Segments are packaged on demand (1-8 s each), so a 20 s clip takes 1-3 min.
    floor.senate.gov (live player) is not reachable from here. The Granicus CDN 403s non-browser User-Agents, so UA matters,
    and archive-video.granicus.com 403s direct (non-proxied) traffic such as ffmpeg's own HTTP client.
  * NASA: images-api.nasa.gov search + images-assets.nasa.gov MP4s (orig/large/medium/...) and sometimes an .srt.
  * DVIDS: public RSS feed (latest 20) + each video page links a direct CloudFront MP4 (usually the original, up to 4K).
    Keyword search needs a free API key (api.dvidshub.net, env DVIDS_API_KEY); the site search page is bot-gated.
  * WHITE HOUSE: whitehouse.gov/videos pages are YouTube embeds only; googlevideo.com is blocked here -> not downloadable.
"""
import html, json, os, re, subprocess, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
GRAN = "https://senate.granicus.com"
SENATE_VIEW = 2  # "Senate Floor Proceedings"
SENATE_RIGHTS = ("U.S. Senate floor video, recorded by the Senate Recording Studio (an office of the Senate Sergeant at Arms) "
                 "and published on senate.gov via Granicus. Work of the U.S. Government: no copyright (17 U.S.C. 105). "
                 "The Granicus pages carry no explicit rights line. CRS report R44665: Senate feeds 'are not copyrighted'; "
                 "'Recorded footage may be used in an informational or educational context, but not for political purposes.'")
NASA_RIGHTS = ("NASA media is generally not copyrighted (17 U.S.C. 105). Per NASA media guidelines: do not use the NASA insignia/logo, "
               "do not imply NASA endorsement, check the item for third-party material.")
DVIDS_RIGHTS = ("DVIDS item marked 'PUBLIC DOMAIN' on its page. dvidshub.net/about/copyright: must not imply endorsement; "
                "include 'The appearance of U.S. Department of War (DoW) visual information does not imply or constitute DoW endorsement.'")
WH_NOTE = ("whitehouse.gov/videos/* pages embed YouTube only (youtube.com/embed/<id>); media is served from googlevideo.com, "
           "which this workspace cannot reach. whitehouse.gov/copyright: 'government-produced materials appearing on this site "
           "are not copyright protected' (third-party content is CC BY 3.0).")


def _open(url, timeout=60, headers=None):
    h = {"User-Agent": UA}; h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)

def get(url, timeout=60):
    return _open(url, timeout).read().decode("utf-8", "ignore")

def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    d = json.loads(out or "{}"); v = [s for s in d.get("streams", []) if s["codec_type"] == "video"]
    return {"duration": round(float(d.get("format", {}).get("duration", 0)), 2),
            "video": f"{v[0]['codec_name']} {v[0]['width']}x{v[0]['height']}" if v else None,
            "audio": any(s["codec_type"] == "audio" for s in d.get("streams", []))}


# ---------------------------------------------------------------- generic HLS range download
def _attrs(line):
    return {k: v.strip('"') for k, v in re.findall(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', line)}

def hls_tracks(manifest_url):
    """Resolve a master playlist to its media playlists: [(kind, playlist_url)], best video first, plus a separate audio
    rendition if the master declares one (House layout). A media playlist is returned as-is."""
    txt = get(manifest_url); lines = txt.splitlines()
    if "#EXT-X-STREAM-INF" not in txt: return [("av", manifest_url)]
    best, audio = None, None
    for i, l in enumerate(lines):
        if l.startswith("#EXT-X-STREAM-INF"):
            a = _attrs(l.split(":", 1)[1]); uri = next(x for x in lines[i + 1:] if x and not x.startswith("#"))
            bw = int(a.get("BANDWIDTH", 0))
            if not best or bw > best[0]: best = (bw, urllib.parse.urljoin(manifest_url, uri), a.get("AUDIO"))
        elif l.startswith("#EXT-X-MEDIA") and "TYPE=AUDIO" in l:
            a = _attrs(l.split(":", 1)[1])
            if a.get("URI") and (audio is None or a.get("DEFAULT") == "YES"): audio = (a.get("GROUP-ID"), urllib.parse.urljoin(manifest_url, a["URI"]))
    out = [("v" if audio and best[2] == audio[0] else "av", best[1])]
    if audio and best[2] == audio[0]: out.append(("a", audio[1]))
    return out

def hls_segments(playlist_url):
    """-> (init_url or None, [(start_s, dur_s, url)]) on the playlist's own clock (0 = first segment)."""
    txt = get(playlist_url, 120); t, segs, init, dur = 0.0, [], None, None
    for l in txt.splitlines():
        if l.startswith("#EXT-X-MAP"): init = urllib.parse.urljoin(playlist_url, _attrs(l.split(":", 1)[1])["URI"])
        elif l.startswith("#EXTINF"): dur = float(l.split(":", 1)[1].split(",")[0])
        elif l and not l.startswith("#") and dur is not None:
            segs.append((t, dur, urllib.parse.urljoin(playlist_url, l))); t += dur; dur = None
    return init, segs

def _grab(init, segs, start, dur, path):
    pick = [s for s in segs if s[0] + s[1] > start and s[0] < start + dur]
    if not pick: raise SystemExit(f"range {start}+{dur}s is outside the stream ({segs[-1][0] + segs[-1][1]:.0f}s long)")
    def dl(u):  # Granicus/Wowza packages segments on demand: 1-8 s each, so fetch in parallel with a retry
        for k in range(3):
            try: return _open(u, 90).read()
            except Exception:
                if k == 2: raise
    urls = ([init] if init else []) + [u for _, _, u in pick]
    with ThreadPoolExecutor(8) as ex, open(path, "wb") as f:
        for b in ex.map(dl, urls): f.write(b)
    return pick[0][0]

def fetch_range(manifest_url, start_s, dur_s, out_mp4, video=True):
    """Download only the HLS segments covering [start_s, start_s+dur_s] and cut exactly. Works for TS (Senate/Granicus) and
    fMP4 with separate audio (House) layouts. Times are on the stream clock (0 = first segment)."""
    tmp = out_mp4 + ".parts"; os.makedirs(tmp, exist_ok=True); ins, offs = [], []
    for kind, pl in hls_tracks(manifest_url):
        if kind == "v" and not video: continue
        init, segs = hls_segments(pl); ext = "mp4" if init else "ts"
        p = f"{tmp}/{kind}.{ext}"; offs.append(_grab(init, segs, start_s, dur_s, p)); ins.append((kind, p))
    args = []
    for (kind, p), o in zip(ins, offs): args += ["-ss", f"{start_s - o:.3f}", "-i", p]
    vi = next((i for i, (k, _) in enumerate(ins) if k in ("v", "av")), None)
    ai = next((i for i, (k, _) in enumerate(ins) if k == "a"), vi)
    maps = (["-map", f"{vi}:v:0"] if video and vi is not None else []) + ["-map", f"{ai}:a:0"]
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"] if video else ["-vn"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-t", f"{dur_s:.3f}", *maps, *enc, "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", out_mp4], check=True, timeout=600)
    subprocess.run(["rm", "-rf", tmp])
    return out_mp4


# ---------------------------------------------------------------- captions
def _ts(x):
    p = x.replace(",", ".").split(":"); p = ["0"] * (3 - len(p)) + p
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])

def parse_captions(txt):
    """WebVTT/SRT -> [{'s','e','t'}]. Senate captions are roll-up (each cue repeats the growing line), so cues whose text
    extends the previous cue are merged into one."""
    raw = []
    for block in re.split(r"\n\s*\n", txt.replace("\r\n", "\n").replace("\r", "\n")):
        m = re.search(r"([\d:.,]+)\s*-->\s*([\d:.,]+)[^\n]*\n(.*)", block, re.S)
        if m: raw.append({"s": _ts(m.group(1)), "e": _ts(m.group(2)), "t": " ".join(re.sub(r"<[^>]+>", "", m.group(3)).split())})
    cues = []
    for c in raw:
        if cues and c["t"].startswith(cues[-1]["t"]) and c["s"] - cues[-1]["e"] < 3:
            cues[-1]["t"], cues[-1]["e"] = c["t"], max(c["e"], cues[-1]["e"])
        elif c["t"]:
            cues.append(dict(c))
    return cues


# ---------------------------------------------------------------- SENATE (Granicus archive, 2012 .. Mar 2023)
_MON = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}

def senate_clips():
    """All archived floor sessions: [{'date': 'YYYYMMDD', 'clip_id': int, 'dur': '05h 12m' | None}], oldest first.
    Merges the RSS feed (newest 100, through Mar 2023) with the full HTML listing (6.7 MB, through Dec 2022)."""
    clips = {}
    rss = get(f"{GRAN}/ViewPublisherRSS.php?view_id={SENATE_VIEW}")
    for it in re.findall(r"<item>(.*?)</item>", rss, re.S):
        p = re.search(r"yr='(\d+)' mo='(\d+)' day='(\d+)'", it); c = re.search(r"clip_id=(\d+)", it)
        if p and c: clips[int(c.group(1))] = {"date": "".join(p.groups()), "clip_id": int(c.group(1)), "dur": None}
    page = get(f"{GRAN}/ViewPublisher.php?view_id={SENATE_VIEW}", 180)
    for row in page.split('headers="Date')[1:]:  # one chunk per listed session (some days are split into parts)
        d = re.search(r"\w{3}, (\w{3})\s+(\d{1,2}), (\d{4})", row); c = re.search(r"clip_id=(\d+)", row)
        du = re.search(r"(\d+h)&nbsp;(\d+m)", row)
        if d and c and int(c.group(1)) in clips and du: clips[int(c.group(1))]["dur"] = " ".join(du.groups())
        elif d and c:
            clips[int(c.group(1))] = {"date": f"{d.group(3)}{_MON[d.group(1)]:02d}{int(d.group(2)):02d}", "clip_id": int(c.group(1)),
                                      "dur": " ".join(du.groups()) if du else None}
    return sorted(clips.values(), key=lambda x: (x["date"], x["clip_id"]))

def senate_days():
    return sorted({c["date"] for c in senate_clips()})

def senate_media(date_or_clip):
    """(manifest_url, captions_url_or_None, rights_note). Accepts 'YYYYMMDD' (first clip of that day) or a Granicus clip_id."""
    s = str(date_or_clip)
    if len(s) == 8 and s.startswith(("19", "20")):
        ids = [c["clip_id"] for c in senate_clips() if c["date"] == s]
        if not ids: raise SystemExit(f"no Senate floor video archived for {s} (archive ends 2023-03-30)")
        clip = ids[0]
    else:
        clip = int(s)
    page = get(f"{GRAN}/player/clip/{clip}?view_id={SENATE_VIEW}&redirect=true")
    m = re.search(r"https://archive-stream\.granicus\.com/[^\"'\s]+?/playlist\.m3u8", page)
    if not m: raise SystemExit(f"clip {clip}: no HLS url on the player page")
    cap = f"{GRAN}/videos/{clip}/captions.vtt"
    try:
        if "-->" not in get(cap, 60)[:2000]: cap = None
    except Exception:
        cap = None
    return m.group(0), cap, SENATE_RIGHTS

def senate_mp4_url(clip_id):
    """Direct whole-session MP4 (archive-video.granicus.com, supports HTTP Range). Large: a full day is GBs."""
    r = _open(f"{GRAN}/DownloadFile.php?view_id={SENATE_VIEW}&clip_id={clip_id}", 60, {"Range": "bytes=0-0"})
    return r.geturl()


# ---------------------------------------------------------------- NASA (images-api.nasa.gov)
NASA_API = "https://images-api.nasa.gov"

def nasa_search(q, n=10):
    url = f"{NASA_API}/search?" + urllib.parse.urlencode({"q": q, "media_type": "video", "page_size": max(n, 1)})
    out = []
    for it in json.loads(get(url))["collection"]["items"][:n]:
        d = it["data"][0]
        out.append({"title": d.get("title"), "url": "https://images.nasa.gov/details/" + urllib.parse.quote(d["nasa_id"]), "nasa_id": d["nasa_id"],
                    "date": (d.get("date_created") or "")[:10], "description": (d.get("description") or "")[:400],
                    "center": d.get("center"), "assets": it["href"], "rights": NASA_RIGHTS})
    return out

def nasa_assets(item):
    """-> {'mp4': best mp4 url, 'all_mp4': [...], 'captions': srt/vtt url or None}"""
    files = [u.replace("http://", "https://", 1) for u in json.loads(get(item["assets"] if isinstance(item, dict) else item))]
    mp4 = [u for u in files if u.lower().endswith(".mp4")]
    rank = ["~orig", "~large", "~medium", "~small", "~mobile", "~preview"]
    mp4.sort(key=lambda u: next((i for i, r in enumerate(rank) if r in u), 9))
    cap = next((u for u in files if u.lower().endswith((".srt", ".vtt"))), None)
    return {"mp4": mp4[0] if mp4 else None, "all_mp4": mp4, "captions": cap}

def _cut_http_mp4(url, out_mp4, start=0, dur=None, prefer=None):
    """ffmpeg reads a progressive MP4 over HTTP with Range requests, so only the needed bytes are fetched."""
    t = ["-t", f"{dur:.3f}"] if dur else []
    def cut(src):
        return subprocess.run(["ffmpeg", "-v", "error", "-y", "-user_agent", UA, "-ss", f"{start:.3f}", "-i", src, *t,
                               "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_mp4], timeout=900).returncode
    # NB: ffmpeg ignores HTTPS_PROXY and connects directly; that works for NASA/DVIDS CloudFront but some CDNs
    # (e.g. archive-video.granicus.com) 403 direct datacenter traffic. Fallback: pull the whole file through the proxy.
    if cut(url) == 0: return out_mp4
    tmp = out_mp4 + ".src.mp4"
    with _open(url, 600) as r, open(tmp, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)
    rc = cut(tmp); os.remove(tmp)
    if rc: raise SystemExit(f"ffmpeg failed on {url}")
    return out_mp4

def nasa_download(item, out_mp4, start=0, dur=None, size="~orig"):
    a = nasa_assets(item)
    url = next((u for u in a["all_mp4"] if size in u), a["mp4"])
    if not url: raise SystemExit("no mp4 asset for this NASA item")
    return _cut_http_mp4(url, out_mp4, start, dur)


# ---------------------------------------------------------------- DVIDS (dvidshub.net, U.S. military; no key needed for RSS + files)
def dvids_latest(n=20):
    rss = get("https://www.dvidshub.net/rss/video"); out = []
    for it in re.findall(r"<item>(.*?)</item>", rss, re.S)[:n]:
        g = lambda tag: html.unescape((re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S) or [None, ""])[1])
        desc = re.sub(r"<[^>]+>", " ", g("description").replace("<![CDATA[", "").replace("]]>", ""))
        out.append({"title": g("title"), "url": g("link"), "date": g("pubDate"), "description": " ".join(desc.split())[:400]})
    return out

def dvids_search(q, n=10):
    """Keyword search needs a free key from https://api.dvidshub.net (set DVIDS_API_KEY). Without it, filter the RSS."""
    key = os.environ.get("DVIDS_API_KEY")
    if not key:
        return [x for x in dvids_latest(20) if q.lower() in (x["title"] + " " + x["description"]).lower()][:n]
    d = json.loads(get("https://api.dvidshub.net/search?" + urllib.parse.urlencode({"q": q, "type": "video", "max_results": n, "api_key": key})))
    return [{"title": r.get("title"), "url": r.get("url"), "date": r.get("date"), "description": (r.get("short_description") or "")[:400]}
            for r in d.get("results", [])]

def dvids_media(page_url):
    """-> (mp4_url, rights_note). The page links the original file on CloudFront (often 1080p or 4K)."""
    page = get(page_url)
    m = re.search(r"https://[a-z0-9]+\.cloudfront\.net/video/[^\"'\s]+\.mp4", page)
    if not m: raise SystemExit("no direct mp4 on this DVIDS page")
    pd = "PUBLIC DOMAIN" in page
    return m.group(0), (DVIDS_RIGHTS if pd else "WARNING: page is not marked PUBLIC DOMAIN - check before use")

def dvids_download(item, out_mp4, start=0, dur=None):
    url, rights = dvids_media(item["url"] if isinstance(item, dict) else item)
    if not rights.startswith("DVIDS"): raise SystemExit(rights)
    return _cut_http_mp4(url, out_mp4, start, dur)


# ---------------------------------------------------------------- WHITE HOUSE (not feasible here)
def whitehouse_videos(n=10):
    """Recent whitehouse.gov video pages with their YouTube id. Media itself cannot be downloaded from this workspace."""
    idx = get("https://www.whitehouse.gov/videos/")
    urls = list(dict.fromkeys(u for u in re.findall(r'https://www\.whitehouse\.gov/videos/[a-z0-9-]+/', idx) if "/page/" not in u))[:n]
    out = []
    for u in urls:
        p = get(u); y = re.search(r"youtube\.com/embed/([\w-]{11})", p); t = re.search(r"<title>([^<]+)", p)
        out.append({"title": html.unescape(t.group(1)).split(" – ")[0] if t else u, "url": u, "youtube_id": y.group(1) if y else None})
    return out


if __name__ == "__main__":
    cmd, a = sys.argv[1], sys.argv[2:]
    if cmd == "senate-days":
        cl = senate_clips()
        for c in cl[-int(a[0]) if a else -30:]: print(c["date"], c["clip_id"], c["dur"] or "")
        print(f"{len(cl)} clips, {cl[0]['date']} .. {cl[-1]['date']}")
    elif cmd == "senate-test":
        m3u8, cap, rights = senate_media(a[0] if a else senate_days()[-1])
        print("manifest:", m3u8); print("captions:", cap); print("rights:", rights)
        start = float(a[1]) if len(a) > 1 else None
        if cap and start is None:
            cues = parse_captions(get(cap, 120)); print(f"{len(cues)} caption lines")
            start = max(0, cues[min(len(cues) - 1, len(cues) // 3)]["s"] - 2)
            for c in cues:
                if start <= c["s"] < start + 20: print(f"  {c['s']:.1f}: {c['t'][:110]}")
        out = fetch_range(m3u8, start or 600, 20, "/tmp/senate_test.mp4"); print(out, ffprobe(out))
    elif cmd == "nasa":
        for r in nasa_search(" ".join(a) or "artemis"): print(json.dumps({k: r[k] for k in ("title", "url", "date", "description")})[:300])
    elif cmd == "nasa-test":
        it = nasa_search(" ".join(a) or "artemis", 1)[0]; print(it["title"], nasa_assets(it))
        out = nasa_download(it, "/tmp/nasa_test.mp4", 0, 15); print(out, ffprobe(out))
    elif cmd == "dvids":
        for r in dvids_latest(int(a[0]) if a else 10): print(json.dumps(r)[:300])
    elif cmd == "dvids-test":
        it = dvids_latest(1)[0]; print(it["title"], dvids_media(it["url"]))
        out = dvids_download(it, "/tmp/dvids_test.mp4", 0, 15); print(out, ffprobe(out))
    elif cmd == "whitehouse":
        print(WH_NOTE)
        for v in whitehouse_videos(5): print(v)
