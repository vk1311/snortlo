"""Score every logged Snortlo post, and track all four YouTube channels.

  python3 engine/metrics.py            (from the repo root)

1. View counts for experiments/log.csv. With YouTube API tokens in ~/.youtube/ (see engine/yt_auth.py) they come from
   the YouTube Data API; otherwise from scraping the public Shorts shelf (the old way, still the fallback).
2. Retention, when the tokens are there (YouTube Analytics API, read-only, lifetime of each video):
   views_api, avg_view_s (average view duration), avg_view_pct (average % of the video watched), subs_gained.
   Analytics runs about 2 days behind, so very new videos may stay blank for a night or two.
3. experiments/channels.csv: every upload on every connected channel (Snortlo, Keegix, Staffkin, Waypoint), Shorts and
   episodes alike, with the same numbers. That's how the brand podcasts, their Shorts and Waypoint explainers are scored.
Secrets are never printed. Any API failure falls back to scraping and is reported in one line.
"""
import csv, datetime as dt, json, os, re, sys, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CHANNEL = "UCwh0hMZj0rAgCdqjcFlMUyw"   # Snortlo
LOG = "experiments/log.csv"
CHANNELS_CSV = "experiments/channels.csv"
YT_DIR = os.path.expanduser("~/.youtube")
LABELS = ("snortlo", "keegix", "staffkin", "waypoint")
BASE = ["posted_at", "series", "slug", "part", "title", "variants", "video_id", "views_24h", "views_72h", "views_7d", "views_now", "checked_at"]
RETENTION = ["views_api", "avg_view_s", "avg_view_pct", "subs_gained", "analytics_at"]
FIELDS = BASE + RETENTION
CH_FIELDS = ["channel", "video_id", "published_at", "kind", "duration_s", "title", "views_now", "views_api",
             "avg_view_s", "avg_view_pct", "subs_gained", "watch_min", "checked_at"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")

def parse_views(txt):
    m = re.search(r"([\d.,]+)\s*(thousand|million|K|M)?\s*views?", txt, re.I)
    if not m: return 0 if "No views" in txt else None
    n = float(m.group(1).replace(",", "")); u = (m.group(2) or "").lower()
    return int(n * (1e3 if u in ("thousand", "k") else 1e6 if u in ("million", "m") else 1))

def channel_shorts():
    """Fallback: {normalized title: (video_id, views)} from the public Shorts shelf."""
    html = get(f"https://www.youtube.com/channel/{CHANNEL}/shorts")
    out = {}
    for m in re.finditer(r'"accessibilityText":"(.*?), ([^,"]*?views?) - play Short".{0,4000}?"videoId":"([\w-]{11})"', html):
        title, views, vid = m.group(1), m.group(2), m.group(3)
        out[norm(title)] = (vid, parse_views(views))
    return out

def norm(s): return re.sub(r"\W+", "", s.lower())

# ---------- YouTube APIs (read-only) ----------
def api_labels():
    if not os.path.exists(os.path.join(YT_DIR, "client.json")): return []
    return [l for l in LABELS if os.path.exists(os.path.join(YT_DIR, f"token-{l}.json"))]

def iso_seconds(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m: return None
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s

def channel_videos(tok, limit=300):
    """All recent uploads of the signed-in channel: {video_id: {...}} with live public view counts."""
    import yt_auth as A
    ch = A.get("https://www.googleapis.com/youtube/v3/channels?part=contentDetails,snippet&mine=true", tok)["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], ""
    while len(ids) < limit:
        r = A.get("https://www.googleapis.com/youtube/v3/playlistItems?" + urllib.parse.urlencode(
            {"part": "contentDetails", "playlistId": uploads, "maxResults": 50, **({"pageToken": page} if page else {})}), tok)
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        page = r.get("nextPageToken")
        if not page: break
    vids = {}
    for i in range(0, len(ids), 50):
        r = A.get("https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(
            {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50])}), tok)
        for v in r.get("items", []):
            secs = iso_seconds(v["contentDetails"].get("duration"))
            vids[v["id"]] = {"title": v["snippet"]["title"], "published_at": v["snippet"]["publishedAt"],
                             "duration_s": secs, "kind": "short" if secs is not None and secs <= 180 else "long",
                             "views_now": int(v.get("statistics", {}).get("viewCount", 0))}
    return ch["snippet"]["title"], vids

def retention(tok, vids):
    """Lifetime analytics per video -> {video_id: {...}}. Videos with no analytics yet are absent."""
    import yt_auth as A
    if not vids: return {}
    start = min(v["published_at"][:10] for v in vids.values())
    end = dt.date.today().isoformat(); out = {}
    ids = list(vids)
    for i in range(0, len(ids), 50):
        r = A.get("https://youtubeanalytics.googleapis.com/v2/reports?" + urllib.parse.urlencode({
            "ids": "channel==MINE", "startDate": start, "endDate": end, "dimensions": "video",
            "metrics": "views,averageViewDuration,averageViewPercentage,subscribersGained,estimatedMinutesWatched",
            "filters": "video==" + ",".join(ids[i:i + 50]), "maxResults": 200, "sort": "-views"}), tok)
        cols = [h["name"] for h in r["columnHeaders"]]
        for row in r.get("rows") or []:
            d = dict(zip(cols, row))
            out[d["video"]] = {"views_api": int(d["views"]), "avg_view_s": int(d["averageViewDuration"]),
                               "avg_view_pct": round(float(d["averageViewPercentage"]), 1),
                               "subs_gained": int(d["subscribersGained"]), "watch_min": int(d["estimatedMinutesWatched"])}
    return out

def pull_api():
    """-> {label: (channel title, {video_id: merged info})}; failures are reported, never fatal."""
    import yt_auth as A
    out = {}
    for label in api_labels():
        try:
            tok = A.access_token(label)
            title, vids = channel_videos(tok)
            try: ret = retention(tok, vids)
            except Exception as e: ret = {}; print(f"analytics failed for {label}: {type(e).__name__}")
            for vid, r in ret.items(): vids[vid].update(r)
            out[label] = (title, vids)
        except Exception as e:
            print(f"YouTube API failed for {label} ({type(e).__name__}); using fallback")
    return out

def write_channels(api, now):
    rows = []
    for label, (_, vids) in api.items():
        for vid, v in vids.items():
            rows.append({"channel": label, "video_id": vid, "checked_at": now, **v})
    rows.sort(key=lambda r: (r["channel"], r["published_at"]), reverse=True)
    with open(CHANNELS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CH_FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def main():
    if not os.path.exists(LOG): print("no log yet"); return
    rows = list(csv.DictReader(open(LOG)))
    now_dt = dt.datetime.now(dt.timezone.utc); now = now_dt.isoformat(timespec="minutes")
    api = pull_api()
    snort = api.get("snortlo", (None, {}))[1]
    by_title = {norm(v["title"]): (vid, v["views_now"]) for vid, v in snort.items()}
    source = "YouTube API" if snort else "public Shorts shelf"
    if not snort:
        try: by_title = channel_shorts()
        except Exception as e: print(f"shelf scrape failed ({type(e).__name__})"); by_title = {}
    hit = ret_hit = 0
    for r in rows:
        match = None
        if r.get("video_id") and r["video_id"] in snort: match = (r["video_id"], snort[r["video_id"]]["views_now"])
        if not match:
            key = norm(r["title"]); match = by_title.get(key)
            if not match:  # titles can get truncated on the shelf
                match = next((v for k, v in by_title.items() if k.startswith(key[:40]) or key.startswith(k[:40])), None)
        if not match or match[1] is None: continue
        vid, views = match; hit += 1
        r["video_id"] = r.get("video_id") or vid; r["views_now"] = views; r["checked_at"] = now
        age_h = (now_dt - dt.datetime.fromisoformat(r["posted_at"])).total_seconds() / 3600
        for col, h in (("views_24h", 24), ("views_72h", 72), ("views_7d", 168)):
            if not r.get(col) and age_h >= h: r[col] = views   # first reading after the checkpoint
        a = snort.get(r["video_id"], {})
        if "avg_view_pct" in a:
            ret_hit += 1; r.update({k: a[k] for k in RETENTION if k in a}); r["analytics_at"] = now
    with open(LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows({k: r.get(k, "") for k in FIELDS} for r in rows)
    print(f"views ({source}): matched {hit}/{len(rows)} logged posts; retention filled for {ret_hit}")
    if api:
        write_channels(api, now)
        print("channels.csv: " + ", ".join(f"{l} ({t}) {len(v)} videos, {sum('avg_view_pct' in x for x in v.values())} with retention"
                                           for l, (t, v) in api.items()))
    else:
        print("no YouTube API tokens in ~/.youtube (restore them from the 'youtube-analytics-token' Doc); retention skipped")

if __name__ == "__main__": main()
