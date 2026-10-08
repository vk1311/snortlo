# Nightly pipeline (run by the "Snortlo nightly story" scheduled task)

1. `bash engine/setup.sh`
2. Score past posts: `python3 engine/metrics.py` (reads YouTube view counts into experiments/log.csv)
3. Pick tonight's settings: `python3 engine/pick.py story` and `python3 engine/pick.py meme` (also rewrites experiments/REPORT.md)
4. Write the story (3 parts) and memes to match the picked settings; render with `engine/make_video.sh <json> <mp4>`
5. Upload via Postiz (raw.githubusercontent.com URLs), schedule, and log each YouTube post with `engine/log_post.py`
6. Commit + push

Experiment variables and their options live in experiments/arms.json. The scoreboard is experiments/REPORT.md.
YouTube is the scoreboard because it is the only platform readable without logins; posts go to Facebook/Instagram with the same settings.

## Long-form sleep stories

Calm 30-90 min "stories to fall asleep to" compilations for YouTube / Facebook (1920x1080).

```
cd engine && python3 longform.py ../longform/<slug>.json ../media/long-<slug>.mp4
```

Input (`longform/<slug>.json`):

```json
{"title": "...", "voice": "af_heart", "speed": 0.92,
 "intro": "text (paragraphs separated by blank lines)",
 "stories": [{"title": "The Laundromat at Midnight", "text": "paragraph one...\n\nparagraph two..."}],
 "outro": "text"}
```

Optional keys: `card_title` (on-screen intro card; otherwise `title` cut at the first emoji or ` | `),
`thumb_title` (default "Sleepy Stories"), `thumb_subtitle` (default "N cozy stories to fall asleep to"),
`announce` (default true: narrates "Story two. <title>." at each story), `rain` (default true).

Outputs next to the mp4: `long-<slug>.chapters.txt` (paste into the YouTube description; first line is 0:00)
and `long-<slug>-thumb.png` (1280x720).

How it works: Kokoro narrates sentence by sentence (0.45 s between sentences, 1.3 s between paragraphs,
~4 s + a soft chime between stories), mixed over a synthesized rain + soft pad bed, normalized to -18 LUFS.
The cozy night-window scene is a 60 s seamless cairo loop rendered once (cached in /tmp/snortlo-longform),
cut into 10 s sub-clips; the full video is a stream-copy concat of those, and only the sub-clips under a
title card get re-encoded. TTS (~2x realtime on 2 cores) is the slow part; chunks are cached, so re-runs are fast.
Add `--keep` to keep the intermediate audio files for debugging.
After rendering, shrink it under GitHub's 100 MB limit (Postiz pulls media from raw.githubusercontent.com):
`engine/shrink.sh media/long-<slug>.mp4 media/long-<slug>-web.mp4` (720p, ~1.1 MB/min). Only the `-web.mp4` is committed.

## Weekly story compilation (Sundays)
`python3 engine/compile.py "<title>" media/compile-<date>.mp4 media/<a>-full.mp4 "Title A" media/<b>-full.mp4 "Title B" ...`
Joins the week's animated full cuts into one 1280x720 video (blurred-background fill, a title card per story),
plus `.chapters.txt` and `-thumb.png`. About 2.5 MB per minute.

## Congress Moments (real public-domain footage)
Rules first: read GOV_SOURCES.md (what footage is allowed, and the house rules for these clips).
- `python3 engine/gov.py days` lists House session days; `python3 engine/gov.py find <YYYYMMDD> 8` scores moments
  (captions with gavels, "time has expired", "regular order", "out of order", laughter… plus loudness spikes) and writes gov/candidates-<day>.json.
- Write gov/<slug>.json: {"day", "start", "end" (caption clock, from the candidate), "end_on_word" (optional, e.g. "expired"),
  "top_text" (meme caption about the SITUATION, not the person's politics), "sfx": [{"at_word": "expired", "name": "recordscratch"}], "hold_end": 1.6}
- `cd engine && python3 gov.py render ../gov/<slug>.json ../media/gov-<slug>.mp4`. Whisper lines the captions up with the real audio,
  cuts one continuous clip (never splice words), adds the white caption band with the "U.S. House floor video · public domain" credit,
  karaoke captions and the sounds (added on top; the original audio is never altered).
- More public-domain sources in engine/gov_sources.py: Senate floor archive 2012–2023 (senate.granicus.com), NASA, DVIDS (needs its
  non-endorsement line). White House video is YouTube-only and can't be downloaded from the cloud. Canadian and provincial
  legislature video is NOT usable commercially without the Speaker's written permission.
