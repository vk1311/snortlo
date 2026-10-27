"""Fetch a free-to-use photo (CC0 or public domain only) for a podcast segment.

    python3 broll.py "cottage porch" ../podcasts/keegix/assets      # prints the saved path

Sources, in order: Openverse (CC0 / Public Domain Mark, photographs only, which also covers
Wikimedia Commons, Flickr PD and StockSnap), then NASA's image library (public domain) for space and sky searches only.
Photos whose title or tags suggest a portrait of a person are skipped (scenes, objects and places only).
Every file used is logged to podcasts/CREDITS.md and returned with its credit line,
so the episode description can list it. No Pexels, no AI images.
"""
import hashlib, io, json, os, re, sys, time, urllib.parse, urllib.request

from PIL import Image

UA = {"User-Agent": "snortlo-podcast/1.0 (github.com/vk1311/snortlo)"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDITS = os.path.join(ROOT, "podcasts", "CREDITS.md")
SKIP_PROVIDERS = {"rawpixel"}          # editor watermarks / login walls
# Photos of identifiable people next to topics like burnout or bad bosses would imply things about them,
# so anything that looks like a portrait is skipped. Scenes, objects and places only.
PEOPLE = re.compile(r"\b(portrait|man|men|woman|women|person|people|girl|boy|guy|lady|selfie|mr|mrs|ms|dr|"
                    r"senator|president|ceo|employee|worker|astronaut|actor|actress|model|headshot|smiling|face)\b", re.I)


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _openverse(query):
    q = urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "category": "photograph",
                                "page_size": 20, "mature": "false", "aspect_ratio": "wide", "size": "large"})
    data = json.loads(_get("https://api.openverse.org/v1/images/?" + q))
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
    if os.path.exists(meta_path) and os.path.exists(img_path):
        return img_path, json.load(open(meta_path))
    space = re.search(r"\b(space|earth|moon|planet|rocket|satellite|stars|galaxy|aurora)\b", query, re.I)
    for gen in ((_openverse, _nasa) if space else (_openverse,)):
        try:
            for url, credit in gen(query):
                if credit["source"] in avoid:
                    continue
                try:
                    im = Image.open(io.BytesIO(_get(url))).convert("RGB")
                except Exception:
                    continue
                if im.width < 900 or im.width < im.height * 1.2:     # landscape only
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
