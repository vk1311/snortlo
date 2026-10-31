# What the nightly run has learned

The nightly run ("All channels nightly") **reads this file at the start** of every run and **updates it at the end** (the Reflect step). It's how each run gets better than the last one instead of repeating mistakes.

## How to reflect (end of every run, 5 minutes max)
1. **What broke tonight and how you fixed it.** If the fix belongs in code or a doc, make the fix there (engine/, *.md) so it never happens again, then add a one-line rule of thumb below.
2. **What the numbers say.** Snortlo: experiments/REPORT.md (pick.py already favours winners). Podcasts and brand Shorts: compare view counts on the brand YouTube channels when available. Note any clear winner or loser with its sample size; don't call a winner on fewer than 3 samples.
3. **One small improvement for tomorrow.** Pick one: a sharper hook pattern, a better visuals search habit, a caption tweak, a new experiment arm in experiments/arms.json, retiring an arm with 10+ samples that keeps losing, or a speed-up in the engine. Do it, and log it in the night log.
4. **Sundays: the weekly review.** Rewrite "Rules of thumb" (merge, cut stale lines, stay under 30 lines), and put 1 or 2 bigger ideas in the report as **proposals for Vatsal** (don't do them).

## What the run may change by itself
- Bug fixes and speed-ups in engine/ (test before committing).
- Wording and clarity of the repo docs, and the writing guidance in STORY_FORMAT.md / CAPTIONS.md / PODCAST_FORMAT.md, when the numbers or a failure show something better.
- Experiment arms (add new arms freely; remove only after 10+ samples).
- Which photo searches, hooks, themes and title styles to use.

## Needs Vatsal's OK first (list as a proposal in the report, don't do it)
- Posting schedule, YouTube caps, which channels get what, new series or formats, stopping a series.
- Voices, the look of the videos, the AI note, honesty rules, anything about his brands' positioning.
- Anything that costs money or needs a new account or login.

## Rules of thumb (keep under 30 lines; edit, don't just append)
- Postiz integration IDs: copy them from integrationList, never retype them (a typo'd Staffkin ID failed a schedule once).
- Every media file must be under 99 MB (Postiz pulls from raw.githubusercontent.com). podcast.py caps the bitrate from the episode length.
- Kaggle token: Google Docs may show the underscore escaped as "\_"; remove the backslash.
- Chatterbox (backup voice) needs the CPU-only torch reinstall and the float32 patches in voice_backend._ensure_chatterbox().
- Brand names the voice gets wrong go in voice_backend.SAY (Airbnb -> "Air bee en bee"). Check any new brand or place name by ear once.
- Photos: Wikimedia Commons first (CC0 / public domain only), then Openverse. Both throttle bursts (HTTP 429), so broll.py paces requests; expect about 30 s per search.
- ALWAYS review podcast photos before scheduling: `python3 engine/nightly.py photos media/pod-<slug>.timeline.json`, look at engine/photos.png, then `nightly.py block <timeline> <numbers>` for anything with people (even hands), war/military/historic-tragedy images, recognizable politicians or offices, logos, black frames, or off-topic shots, and re-render. On Oct 27 the first review blocked 61 of 187 photos, including a wartime crowd photo found by "burnt match". The title filter alone is NOT enough. Re-run `photos` after every block: replacements can be bad too (Oct 31: "coins jar" swapped in a boardroom meeting photo).
- Photo searches: plain nouns for places and objects ("smoke alarm", "Halifax waterfront"). People searches are skipped, and abstract words ("burnout", "policy") return junk.
- The owner wants podcasts to be visual first: full-screen photos changing every ~7 s, cards, big captions. Never go back to a static "studio" look.
- AI disclosure is one small corner note plus the description. No "AI host" or "AI character" in dialogue, cards or roles.
- Podcast length: the new voices are faster. Write 3,700 to 4,300 spoken words for 20+ minutes (3,346 words came out at 18.4 min). The nightly prompt's older "3,300-3,900" figure is outdated; this file and PODCAST_FORMAT.md win.
- Snortlo: 1-part stories and question hooks lead so far (small samples); am_puck is the strongest narrator; all-lowercase titles do best (see REPORT.md).
- Living-room `tv` text: max ~10 characters per line, and keep Lo at x≈360 with no zoom on him, or the camera crops the TV (caught on qc Oct 28).
- Congress: the House has been pro forma since mid-September (election recess). If gov.py find returns [] for the 3 newest unused days, skip it without trying more days.
- Snortlo memes: "x years later" format and 8 AM posts lead (small samples).
- Anything over ~8 min (nightly.py voices, sleep-story render, shrink.sh) must run with nohup in the background and be polled; the shell tool kills foreground commands at 10 min (killed voices and shrink on Oct 30). Sleep-story Fridays: ~700 lines take ~60 min on Kaggle; kaggle_tts.py now scales its wait with job size.
- Meme `cards`: 3 cards of max ~6 characters, and no cam zoom on that beat, or they overlap and crop (caught on qc Oct 31).
- Openverse can time out on every call for a whole night; broll.py now skips it after 3 failures (Oct 31). Commons alone is enough.
- Speech bubbles: "|" is a line break (fixed in anim.wrapc Oct 30; it used to print literally).
- Shorts renders cap video at 12 Mbps (anim_render.py): deepfry grain made a 12 s meme 42 MB; now ~13 MB. If a file is still big, check for grain/shake, not length.

## Night log (newest first; keep the last 14 nights, one to three lines each)
- 2026-10-31: Kaggle OK first try (373 lines incl. Keegix ep 2, 18 min), but the background log was silent the whole time; kaggle_tts.py now prints a progress line every ~5 min. QC: meme A cards cropped and Lo covered the TV; fixed and re-rendered. Openverse timed out on every search and Commons throttled hard (HTTP 429), so each podcast render took ~45 min; added an Openverse circuit breaker. Photo review blocked 19 photos over two passes (people, logos, a meeting). Numbers: no new calls (samples still small).
- 2026-10-30: Kaggle OK first try but slow (712 lines incl. sleep story, 58 min); first foreground try was killed by the 10-min shell cap, so long steps now run in background. QC: speech bubble printed "|" literally; fixed wrapc. Improvement: Kaggle wait scales with line count so a big night isn't logged as "Kaggle down" (would have deferred podcasts). Memes came out 10.7/11.8 s for the 12-16 s arm; lengthened silent holds. Numbers: am_puck 6.65 (n=8) leads; music on beats off (n=19 vs 13); lowercase titles lead (n=11); Lo Explains #1 got 987 views.
- 2026-10-29: clean run, Kaggle OK first try (144 s). QC: Lo stood in front of the kitchen sign in meme A; moved him and re-rendered. Improvement: capped Shorts bitrate at 12 Mbps (deepfry meme 42 MB -> 13 MB, tested). Congress skipped (no new session days). Numbers: not enough new samples.
- 2026-10-28: clean run, Kaggle OK first try. QC caught TV text cropped in meme B; fixed and added the tv-text rule here and in STORY_FORMAT.md. Congress skipped again (recess). First Lo Explains (sandwich). Numbers: too few new samples to call anything.
- 2026-10-27 (set-up day): photo review caught people, war and off-topic photos that slipped past the title filter; added broll_block.txt, a stronger filter (no strips, dark frames or scans), and the photos/block review step.
- 2026-10-27 (set-up day, not a nightly run): moved all channels to the Qwen3 house voices; podcasts switched to the visual-first look; Airbnb pronunciation fixed; started this file.
