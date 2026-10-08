"""Record a scheduled post so metrics.py can score it later.
Usage: python3 engine/log_post.py <series> <slug> <part> "<YouTube title>" '<variants json>' <posted_at ISO UTC>"""
import csv, os, sys
FIELDS = ["posted_at", "series", "slug", "part", "title", "variants", "video_id", "views_24h", "views_72h", "views_7d", "views_now", "checked_at"]
LOG = "experiments/log.csv"; new = not os.path.exists(LOG)
series, slug, part, title, variants, posted = sys.argv[1:7]
with open(LOG, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new: w.writeheader()
    w.writerow(dict(posted_at=posted, series=series, slug=slug, part=part, title=title, variants=variants))
print("logged", slug, part)
