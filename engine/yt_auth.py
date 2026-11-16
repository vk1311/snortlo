"""One-time Google sign-in for the YouTube Analytics API (read-only), and a quick test.

Secrets never go in the repo. They live in ~/.youtube/ (chmod 600) during a run, and the nightly
run restores them from Vatsal's Google Doc "youtube-analytics-token" (like the Kaggle token).

  python3 engine/yt_auth.py url                 -> prints the sign-in link (needs ~/.youtube/client.json)
  python3 engine/yt_auth.py code '<pasted URL or code>' <label>   -> saves ~/.youtube/token-<label>.json
  python3 engine/yt_auth.py test <label>        -> last 28 days: views, watch time, avg view %, subs
  python3 engine/yt_auth.py restore < doc.txt   -> rebuild ~/.youtube/ from the Google Doc's text (nightly setup)

Google Doc "youtube-analytics-token" holds ONE JSON object:
  {"client_id": "...", "client_secret": "...", "tokens": {"snortlo": "<refresh token>", "keegix": "...", ...}}
Google Docs may show "_" as "\\_"; restore strips those backslashes. Prints labels only, never a secret.
"""
import json, os, sys, urllib.parse, urllib.request, datetime as dt

DIR = os.path.expanduser("~/.youtube")
SCOPES = "https://www.googleapis.com/auth/yt-analytics.readonly https://www.googleapis.com/auth/youtube.readonly"
REDIRECT = "http://localhost:8765/"

def client():
    return json.load(open(os.path.join(DIR, "client.json")))

def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def access_token(label):
    t = json.load(open(os.path.join(DIR, f"token-{label}.json")))
    c = client()
    return post("https://oauth2.googleapis.com/token", {"client_id": c["client_id"], "client_secret": c["client_secret"],
                "refresh_token": t["refresh_token"], "grant_type": "refresh_token"})["access_token"]

def main():
    cmd = sys.argv[1]
    if cmd == "url":
        c = client()
        print("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": c["client_id"], "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPES,
            "access_type": "offline", "prompt": "consent select_account"}))
    elif cmd == "code":
        raw, label = sys.argv[2], sys.argv[3]
        code = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get("code", [raw])[0]
        c = client()
        t = post("https://oauth2.googleapis.com/token", {"code": code, "client_id": c["client_id"],
                 "client_secret": c["client_secret"], "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
        if "refresh_token" not in t:
            sys.exit("no refresh_token returned; sign in again from a fresh link")
        p = os.path.join(DIR, f"token-{label}.json")
        json.dump({"refresh_token": t["refresh_token"]}, open(p, "w")); os.chmod(p, 0o600)
        ch = get("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true", t["access_token"])
        print("saved", label, "->", [i["snippet"]["title"] for i in ch.get("items", [])])
    elif cmd == "restore":
        raw = sys.stdin.read().replace("\\_", "_")
        d = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        p = os.path.join(DIR, "client.json")
        json.dump({"client_id": d["client_id"].strip(), "client_secret": d["client_secret"].strip()}, open(p, "w")); os.chmod(p, 0o600)
        for label, rt in d.get("tokens", {}).items():
            p = os.path.join(DIR, f"token-{label}.json")
            json.dump({"refresh_token": rt.strip()}, open(p, "w")); os.chmod(p, 0o600)
        print("restored ~/.youtube:", ", ".join(sorted(d.get("tokens", {}))) or "no tokens")
    elif cmd == "test":
        tok = access_token(sys.argv[2])
        end = dt.date.today(); start = end - dt.timedelta(days=28)
        r = get("https://youtubeanalytics.googleapis.com/v2/reports?" + urllib.parse.urlencode({
            "ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(),
            "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained"}), tok)
        print(json.dumps({"columns": [h["name"] for h in r["columnHeaders"]], "rows": r.get("rows")}, indent=1))

if __name__ == "__main__":
    os.makedirs(DIR, exist_ok=True); os.chmod(DIR, 0o700)
    main()
