"""Choose tonight's experiment settings and write the scoreboard.
Usage: python3 engine/pick.py story|meme [YYYY-MM-DD]   -> prints JSON {variable: arm}, and rewrites experiments/REPORT.md"""
import csv, json, math, os, random, sys, datetime as dt

ARMS = json.load(open("experiments/arms.json")); LOG = "experiments/log.csv"
OVR = "experiments/overrides.json"   # owner-approved temporary overrides (see the file's _about)

def today_halifax():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Halifax")).date().isoformat()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=4)).date().isoformat()

def overrides(series, day=None):
    """-> (forced {var: arm}, blocked {var: [arms]}) for tonight."""
    day = day or today_halifax(); forced, blocked = {}, {}
    if not os.path.exists(OVR): return forced, blocked
    for o in json.load(open(OVR)).get("overrides", []):
        active = o["from"] <= day <= o["until"]
        if active: forced.update(o.get(series, {}))
        else:
            for var, arms in o.get("window_only", {}).get(series, {}).items():
                blocked.setdefault(var, []).extend(arms)
    return forced, blocked

def scored_rows(series):
    if not os.path.exists(LOG): return []
    out = []
    for r in csv.DictReader(open(LOG)):
        v = r.get(ARMS["metric"]) or ""
        if r["series"] == series and v.strip():
            out.append((json.loads(r["variants"] or "{}"), math.log1p(float(v))))
    return out

def stats(series):
    rows = scored_rows(series); table = {}
    for var, arms in ARMS[series].items():
        table[var] = {}
        for a in arms:
            xs = [s for v, s in rows if v.get(var) == a]
            table[var][json.dumps(a)] = (len(xs), sum(xs) / len(xs) if xs else None)
    return table

def pick(series, day=None):
    t = stats(series); choice = {}; forced, blocked = overrides(series, day)
    for var, arms in ARMS[series].items():
        if var in forced: choice[var] = forced[var]; continue
        arms = [a for a in arms if a not in blocked.get(var, [])]
        under = [a for a in arms if t[var][json.dumps(a)][0] < ARMS["min_samples"]]
        if under and random.random() < 0.6: choice[var] = random.choice(under)        # still learning: try unknowns
        elif random.random() < ARMS["explore_rate"]: choice[var] = random.choice(arms)  # keep exploring
        else:
            known = [a for a in arms if t[var][json.dumps(a)][1] is not None]
            choice[var] = max(known, key=lambda a: t[var][json.dumps(a)][1]) if known else random.choice(arms)
    return choice

def report():
    lines = [f"# Snortlo experiment scoreboard", f"_updated {dt.date.today()} · score = average log(1 + {ARMS['metric']}) on YouTube, higher is better_", ""]
    for series in ("story", "meme"):
        lines += [f"## {'stories' if series == 'story' else 'memes'}", ""]
        for var, arms in stats(series).items():
            ranked = sorted(arms.items(), key=lambda kv: -(kv[1][1] or -1))
            cells = [f"**{json.loads(a)}** {('%.2f' % m) if m is not None else '–'} (n={n})" for a, (n, m) in ranked]
            lines.append(f"- {var}: " + " · ".join(cells))
        lines.append("")
    open("experiments/REPORT.md", "w").write("\n".join(lines))

if __name__ == "__main__":
    series = sys.argv[1] if len(sys.argv) > 1 else "story"
    day = sys.argv[2] if len(sys.argv) > 2 else None   # optional YYYY-MM-DD, for testing
    report(); print(json.dumps(pick(series, day)))
