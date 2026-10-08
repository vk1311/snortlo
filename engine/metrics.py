"""Pull view counts for every Snortlo YouTube Short and write them into experiments/log.csv.
YouTube is the only platform we can read without logins, so it is the scoreboard.
Usage: python3 engine/metrics.py   (from the repo root)"""
import csv, datetime as dt, json, os, re, sys, urllib.request

CHANNEL = "UCwh0hMZj0rAgCdqjcFlMUyw"
LOG = "experiments/log.csv"
FIELDS = ["posted_at", "series", "slug", "part", "title", "variants", "video_id", "views_24h", "views_72h", "views_7d", "views_now", "checked_at"]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")

def parse_views(txt):
    m = re.search(r"([\d.,]+)\s*(thousand|million|K|M)?\s*views?", txt, re.I)
    if not m: return 0 if "No views" in txt else None
    n = float(m.group(1).replace(",", "")); u = (m.group(2) or "").lower()
    return int(n * (1e3 if u in ("thousand", "k") else 1e6 if u in ("million", "m") else 1))

def channel_shorts():
    html = get(f"https://www.youtube.com/channel/{CHANNEL}/shorts")
    out = {}
    for m in re.finditer(r'"accessibilityText":"(.*?), ([^,"]*?views?) - play Short".{0,4000}?"videoId":"([\w-]{11})"', html):
        title, views, vid = m.group(1), m.group(2), m.group(3)
        out[norm(title)] = (vid, parse_views(views))
    return out

def norm(s): return re.sub(r"\W+", "", s.lower())

def main():
    if not os.path.exists(LOG): print("no log yet"); return
    rows = list(csv.DictReader(open(LOG)))
    shorts = channel_shorts(); now = dt.datetime.now(dt.timezone.utc)
    hit = 0
    for r in rows:
        key = norm(r["title"]); match = shorts.get(key)
        if not match:  # titles can get truncated on the shelf
            match = next((v for k, v in shorts.items() if k.startswith(key[:40]) or key.startswith(k[:40])), None)
        if not match or match[1] is None: continue
        vid, views = match; hit += 1
        r["video_id"] = r.get("video_id") or vid; r["views_now"] = views; r["checked_at"] = now.isoformat(timespec="minutes")
        age_h = (now - dt.datetime.fromisoformat(r["posted_at"])).total_seconds() / 3600
        for col, h in (("views_24h", 24), ("views_72h", 72), ("views_7d", 168)):
            if not r.get(col) and age_h >= h: r[col] = views   # first reading after the checkpoint
    with open(LOG, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows({k: r.get(k, "") for k in FIELDS} for r in rows)
    print(f"matched {hit}/{len(rows)} logged posts to {len(shorts)} shorts on the channel")

if __name__ == "__main__": main()
