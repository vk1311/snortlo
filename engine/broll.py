"""Fetch a free-to-use photo (CC0 or public domain only) for a podcast segment.

    python3 broll.py "cottage porch" ../podcasts/keegix/assets      # prints the saved path

Sources, in order: Wikimedia Commons (only files whose licence is CC0 or public domain; fast and reliable),
then Openverse (CC0 / Public Domain Mark photographs: Flickr PD, StockSnap and more; it rate-limits anonymous use,
so it gets a short timeout), then NASA's image library (public domain) for space and sky searches only.
Photos whose title or tags suggest a portrait of a person are skipped (scenes, objects and places only).
Every file used is logged to podcasts/CREDITS.md and returned with its credit line,
so the episode description can list it. No Pexels, no AI images.
"""
import hashlib, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

from PIL import Image

UA = {"User-Agent": "snortlo-podcast/1.1 (https://github.com/vk1311/snortlo; vatsalk1311@gmail.com) python-urllib"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDITS = os.path.join(ROOT, "podcasts", "CREDITS.md")
SKIP_PROVIDERS = {"rawpixel"}          # editor watermarks / login walls
# Photos of identifiable people next to topics like burnout or bad bosses would imply things about them,
# so anything that looks like a portrait is skipped. Scenes, objects and places only.
PEOPLE = re.compile(r"\b(portrait|man|men|woman|women|person|people|girl|boy|guy|lady|selfie|mr|mrs|ms|dr|"
                    r"senator|president|ceo|employee|worker|workers|astronaut|actor|actress|model|headshot|smiling|face|"
                    r"soldier|soldiers|army|military|troops|airman|marine|navy|war|wartime|holocaust|ghetto|nazi|refugee|"
                    r"children|child|kids|crowd|family|prisoner|police|students|staff|team|oval office|white house|"
                    r"bust|statue|sculpture|relief|painting|hand|hands)\b", re.I)
# Photos a human rejected on review (engine/broll_block.txt): never used again.
_BLOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "broll_block.txt")
BLOCK = {l.strip() for l in open(_BLOCK_FILE) if l.strip() and not l.startswith("#")} if os.path.exists(_BLOCK_FILE) else set()


def usable(im):
    """Reject thin panoramas, near-black frames and washed-out scans or line drawings."""
    from PIL import ImageStat
    w, h = im.size
    if w / h > 2.4 or w < 900 or w < h * 1.2:
        return False
    st = ImageStat.Stat(im.convert("L").resize((64, 64)))
    mean, sd = st.mean[0], st.stddev[0]
    return 45 <= mean <= 225 and sd >= 28


def _get(url, timeout=25):
    """GET with polite pacing: Wikimedia and Openverse throttle bursts (HTTP 429), so wait and retry."""
    for attempt in range(4):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            time.sleep(0.6)
            return data
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3: raise
            wait = int(e.headers.get("Retry-After") or 0) or 6 * (attempt + 1)
            time.sleep(min(wait, 30))


_OV_FAILS = [0]   # circuit breaker: Openverse sometimes times out on every call; stop asking after 3 failures


def _openverse(query):
    if _OV_FAILS[0] >= 3:
        return []
    q = urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "category": "photograph",
                                "page_size": 20, "mature": "false", "aspect_ratio": "wide", "size": "large"})
    data = json.loads(_get("https://api.openverse.org/v1/images/?" + q, timeout=12))
    for r in data.get("results", []):
        if r.get("provider") in SKIP_PROVIDERS or (r.get("width") or 0) < 1200:
            continue
        words = " ".join([r.get("title") or ""] + [t.get("name", "") for t in (r.get("tags") or [])])
        if PEOPLE.search(words):
            continue
        lic = "CC0" if r.get("license") == "cc0" else "Public domain"
        for k in ("creator", "title"):     # some providers send %uXXXX / %20 escapes
            v = r.get(k) or ""
            v = re.sub(r"%u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), v)
            r[k] = urllib.parse.unquote(v)
        yield r["url"], {"title": r.get("title") or query, "creator": r.get("creator") or "unknown",
                         "license": lic, "source": r.get("foreign_landing_url") or r["url"],
                         "via": "Openverse / " + (r.get("provider") or "")}


def _commons(query):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                                "gsrsearch": f"{query} filetype:bitmap -war -military -soldier -army -holocaust -portrait", "gsrlimit": 50, "prop": "imageinfo",
                                "iiprop": "url|size|extmetadata", "iiurlwidth": 1280,          # a standard (pre-cached) thumbnail size: far fewer 429s
                                "iiextmetadatafilter": "LicenseShortName|Artist"})
    data = json.loads(_get("https://commons.wikimedia.org/w/api.php?" + q, timeout=20))
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    stems = set()
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        lic = (m.get("LicenseShortName", {}).get("value") or "").lower()
        if not ("cc0" in lic or "public domain" in lic or lic == "pd"):
            continue
        title = re.sub(r"^File:|\.\w+$", "", p.get("title", ""))
        if PEOPLE.search(title) or (ii.get("width") or 0) < 1200 or ii.get("width", 0) < ii.get("height", 1) * 1.2:
            continue
        stem = re.sub(r"[\s_]*(\(\d+\)|\d+)$", "", title).lower()
        if stem in stems:                       # skip near-identical series shots (… 2, … 3)
            continue
        stems.add(stem)
        artist = re.sub(r"<[^>]+>", "", m.get("Artist", {}).get("value") or "").strip() or "unknown"
        yield ii.get("thumburl") or ii["url"], {"title": title, "creator": artist[:80],
                                               "license": "CC0" if "cc0" in lic else "Public domain",
                                               "source": ii.get("descriptionurl") or ii["url"], "via": "Wikimedia Commons"}


def _nasa(query):
    q = urllib.parse.urlencode({"q": query, "media_type": "image"})
    data = json.loads(_get("https://images-api.nasa.gov/search?" + q))
    for it in data.get("collection", {}).get("items", [])[:10]:
        d = it["data"][0]
        for l in it.get("links", []):
            if l.get("render") == "image":
                href = l["href"].replace("~thumb", "~large")
                yield href, {"title": d.get("title", query), "creator": "NASA", "license": "Public domain",
                             "source": "https://images.nasa.gov/details/" + d["nasa_id"], "via": "NASA Image Library"}


def fetch(query, outdir, avoid=()):
    """Return (path, credit dict) or (None, None). `avoid` = source URLs already used in this episode."""
    if not query:
        return None, None
    os.makedirs(outdir, exist_ok=True)
    key = hashlib.sha1(query.lower().encode()).hexdigest()[:10]
    meta_path = os.path.join(outdir, key + ".json")
    img_path = os.path.join(outdir, key + ".jpg")
    if os.path.exists(meta_path) and os.path.exists(img_path) and json.load(open(meta_path))["source"] not in BLOCK:
        return img_path, json.load(open(meta_path))
    space = re.search(r"\b(space|earth|moon|planet|rocket|satellite|stars|galaxy|aurora)\b", query, re.I)
    for gen in ((_commons, _openverse, _nasa) if space else (_commons, _openverse)):
        try:
            for url, credit in gen(query):
                if credit["source"] in avoid or credit["source"] in BLOCK:
                    continue
                try:
                    im = Image.open(io.BytesIO(_get(url))).convert("RGB")
                except Exception:
                    continue
                if not usable(im):
                    continue
                im.thumbnail((1600, 1600))
                im.save(img_path, quality=86)
                credit["query"] = query
                json.dump(credit, open(meta_path, "w"), indent=1)
                _log(credit)
                return img_path, credit
        except Exception as e:  # network or API hiccup: try the next source
            print(f"[broll] {gen.__name__} failed for {query!r}: {e}", file=sys.stderr)
            time.sleep(1)
    return None, None


def fetch_many(query, outdir, n=3, avoid=()):
    """Up to n different photos for one search (one API call, cached). Returns [(path, credit)]."""
    if not query:
        return []
    os.makedirs(outdir, exist_ok=True)
    key = hashlib.sha1(("many|" + query.lower()).encode()).hexdigest()[:10]
    idx = os.path.join(outdir, key + ".many.json")
    if os.path.exists(idx):
        got = [(p, c) for p, c in json.load(open(idx))
               if os.path.exists(p) and c["source"] not in BLOCK and usable(Image.open(p).convert("RGB"))]
        if got:
            return [(p, c) for p, c in got if c["source"] not in avoid] or got
    space = re.search(r"\b(space|earth|moon|planet|rocket|satellite|stars|galaxy|aurora)\b", query, re.I)
    got = []
    for gen in ((_commons, _openverse, _nasa) if space else (_commons, _openverse)):
        try:
            for url, credit in gen(query):
                if len(got) >= n: break
                if credit["source"] in avoid or credit["source"] in BLOCK or any(c["source"] == credit["source"] for _, c in got):
                    continue
                try:
                    im = Image.open(io.BytesIO(_get(url))).convert("RGB")
                except Exception:
                    continue
                if not usable(im):
                    continue
                im.thumbnail((1700, 1700))
                p = os.path.join(outdir, f"{key}-{len(got)}.jpg"); im.save(p, quality=86)
                credit["query"] = query; got.append((p, credit)); _log(credit)
        except Exception as e:
            print(f"[broll] {gen.__name__} failed for {query!r}: {e}", file=sys.stderr)
            if gen is _openverse:
                _OV_FAILS[0] += 1
                if _OV_FAILS[0] == 3: print("[broll] Openverse failed 3 times; skipping it for the rest of this run", file=sys.stderr)
            time.sleep(2)
        if len(got) >= n: break
    if got:
        json.dump(got, open(idx, "w"), indent=1)
    time.sleep(1.2)                     # be gentle with the free API
    return got


def credit_line(c):
    return f'"{c["title"]}" by {c["creator"]}, {c["license"]}, {c["source"]}'


def _log(c):
    if os.path.exists(CREDITS) and c["source"] in open(CREDITS).read():
        return                                   # already credited
    new = not os.path.exists(CREDITS)
    with open(CREDITS, "a") as f:
        if new:
            f.write("# Podcast photo credits\n\nEvery outside image used in the Keegix and Staffkin podcasts. "
                    "CC0 or public domain only.\n\n")
        f.write(f"- {credit_line(c)} (via {c['via']}; search: {c['query']})\n")


if __name__ == "__main__":
    p, c = fetch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "/tmp/broll")
    print(p, c)
