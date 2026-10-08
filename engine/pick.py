"""Choose tonight's experiment settings and write the scoreboard.
Usage: python3 engine/pick.py story|meme   -> prints JSON {variable: arm}, and rewrites experiments/REPORT.md"""
import csv, json, math, os, random, sys, datetime as dt

ARMS = json.load(open("experiments/arms.json")); LOG = "experiments/log.csv"

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

def pick(series):
    t = stats(series); choice = {}
    for var, arms in ARMS[series].items():
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
    report(); print(json.dumps(pick(series)))
