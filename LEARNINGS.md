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

## Rules of thumb (keep under 30 lines; edit, don't just append; last weekly rewrite Nov 1)
**Setup and ops**
- Postiz integration IDs: copy them from integrationList, never retype them (a typo'd Staffkin ID failed once).
- If setup.sh fails on a network reset, just rerun it (downloads now resume via .part files). Export KAGGLE_USERNAME in the same shell call that runs nightly.py.
- Kaggle token: Google Docs may show the underscore escaped as "\_"; remove the backslash.
- Anything over ~8 min (voices on big nights, sleep-story render, shrink.sh) runs with nohup in the background and is polled; the shell tool kills foreground commands at 10 min (and poll with `sleep` under 5 min per call, setting the tool timeout). kaggle_tts.py scales its wait with job size; since Nov 2 voice_backend streams its progress lines into the nightly.py log.
- Never `pkill -f` a pattern that also matches your own shell command line (it kills the tool call); kill by PID.
- Chatterbox (backup voice) needs the CPU-only torch reinstall and the float32 patches in voice_backend._ensure_chatterbox().
- ALWAYS read every `"ok"` in the `nightly.py render` output: a failed item still leaves a file behind (Nov 1: a 5.8 s video under 14 s of audio). qc now flags this as "BROKEN".
- Postiz's ask_postiz agent fails (no OpenAI key), so brand queues can't be read for the clash check; use the planned 12:00 slot and say so.
- Halifax is UTC-4 from Nov 1 (DST ended); it was UTC-3 before. Recheck the offset in March.
**Files and media**
- Every media file < 99 MB (Postiz pulls from raw.githubusercontent.com). podcast.py caps bitrate from length; Shorts cap at 12 Mbps. A big Short means grain/shake, not length.
- Brand names the voice gets wrong go in voice_backend.SAY. Check any new brand or place name by ear once.
**Podcasts**
- Visual first: full-screen photos changing every ~7 s, cards, big captions. Never a static "studio" look. AI disclosure = one small corner note + description; no "AI host"/"AI character" anywhere on screen or in dialogue.
- Length: write 3,700-4,300 spoken words for 20+ min (the new voices are faster; this beats the prompt's older 3,300-3,900). 3,724 words = 19.6 min, so aim for 3,900+. Plan 6 main segments, not 4; a practical 'how to say it' segment is easy, sourced-fact-free length.
- Photos: plain nouns for places and objects; people and abstract words return junk. Commons first (CC0/PD), Openverse second with a 3-failure circuit breaker; ~30-45 s per search, so start podcast renders early.
- Mood words in searches ("quiet office", "break room", "training class", "laptop meeting") return paintings, people and soldiers; use objects ("desk lamp", "empty chairs", "whiteboard").
- ALWAYS review photos: `nightly.py photos <timeline>`, look at engine/photos.png, `nightly.py block` people (even hands), military/tragedy, politicians, logos, black or off-topic frames, then re-render and re-run `photos` (replacements can be bad too).
**Snortlo writing and look**
- Winners so far (REPORT.md, small n): 1-part stories (6.70, n=6 vs 5.49, n=8), question hooks, am_puck, all-lowercase titles, music on; memes: x_years_later, 8 AM posts, unvoiced. Customers is the best story theme (n=3).
- Living-room `tv` text: max ~10 characters per line; keep EVERY character at x<600 (the TV is at x≈680-880) with no zoom on them. Read `layout_warnings` in the render output and fix before QC.
- `cards` (memes AND stories): 3 cards of max ~6 characters, no cam zoom on that beat (a 1.5x zoom crops the outer cards), and blank the whiteboard/sign behind them (cards cover x≈90-1090, y≈370-570).
- Speech bubbles: "|" is a line break.
- Congress: the House is pro forma (election recess since mid-September). If gov.py find returns [] for the 3 newest unused days, skip it.

## Temporary (delete after Nov 8, 2026)
- Nov 5-8: election_aftermath theme is forced on stories and both memes by experiments/overrides.json (Vatsal, Nov 4). Rules in STORY_FORMAT.md: the shared experience only, no parties, candidates, results, fraud talk or voting advice. Congress Moments stay as normal (the House is back Nov 9); they never touch the election.

## Night log (newest first; keep the last 14 nights, one to three lines each)
- 2026-11-05 (Thu): clean run, Kaggle OK first try (21 lines, 228 s). QC: mom and grandpa stood over the living-room TV text (third time this month); moved them to x<600 and re-rendered. Root fix: `nightly.py render` now prints `layout_warnings` (character at x>=600 on the living set, cards under a cam zoom) for every short, tested. Congress skipped (recess). First election_aftermath night (story + both memes). Numbers: no new calls.
- 2026-11-04 (Wed): setup.sh failed on a connection reset mid-download of the Kokoro model and left a truncated file the old `[ -f ]` check would have trusted forever; setup.sh now downloads to .part with retries and renames only when complete (tested). Kaggle OK first try (30 lines, 208 s). QC: "TEAL CAP MINE" cards cropped by a 1.5x cam zoom in the story; removed the zoom and re-rendered. Meme B came out 11.0 s for the 12-16 s arm; lengthened holds to 13.2 s. Congress skipped (no new day). Numbers: 1-part 6.35 (n=10) vs 2-part 5.49 (n=8); am_puck 6.53 (n=14) leads af_heart 5.79 (n=6).
- 2026-11-03 (Tue): clean run, Kaggle OK first try (19 lines, 164 s); no fixes needed. QC fine (no TV/sign overlaps; street set worked for a 3-person scene with x=200/540/880). Congress skipped (Nov 2 pro forma, find returned []). Improvement: added a 'seasonal' story theme arm (leaf blowers, snow, holidays) since the calendar is a free source of premises. Numbers: 1-part 6.45 (n=9) vs 2-part 5.49 (n=8); am_puck 6.60 (n=13) still leads.
- 2026-11-02 (Mon): Kaggle OK first try (388 lines incl. Staffkin ep 2, 1,117 s), but the nohup log stayed empty for 18 min because voice_backend captured kaggle_tts output; it now streams it (tested). QC: Kyle stood over the living-room TV text; moved him to x=640 and re-rendered. Photo review took three passes and blocked 28 (people, police, soldiers, a painting, a logo, a foreign parliament); Openverse timed out again, Commons carried it. Writing note: Staffkin ep 2 first draft came in at 3,100 words; a 'how to have the conversation' segment and a 4th situation got it to 3,724 (19.6 min). Congress skipped (recess). Numbers: no new calls.
- 2026-11-01 (Sun): Kaggle OK first try (14 lines, 150 s). Meme A's render crashed (cairo zero-scale on a pop-in card at its exact start frame) but left a half-length file that qc's sizes didn't catch; fixed by clamping every pop-in scale in anim_render.py, and qc now flags video shorter than audio. Congress skipped (recess). Weekly compilation: 6 stories, 7.1 min. Numbers: 1-part beats 2-part (6.70 n=6 vs 5.49 n=8); emoji_end trails all_lowercase (5.59 n=8 vs 6.33 n=15).
- 2026-10-31: Kaggle OK first try (373 lines incl. Keegix ep 2, 18 min), but the background log was silent the whole time; kaggle_tts.py now prints a progress line every ~5 min. QC: meme A cards cropped and Lo covered the TV; fixed and re-rendered. Openverse timed out on every search and Commons throttled hard (HTTP 429), so each podcast render took ~45 min; added an Openverse circuit breaker. Photo review blocked 19 photos over two passes (people, logos, a meeting). Numbers: no new calls (samples still small).
- 2026-10-30: Kaggle OK first try but slow (712 lines incl. sleep story, 58 min); first foreground try was killed by the 10-min shell cap, so long steps now run in background. QC: speech bubble printed "|" literally; fixed wrapc. Improvement: Kaggle wait scales with line count so a big night isn't logged as "Kaggle down" (would have deferred podcasts). Memes came out 10.7/11.8 s for the 12-16 s arm; lengthened silent holds. Numbers: am_puck 6.65 (n=8) leads; music on beats off (n=19 vs 13); lowercase titles lead (n=11); Lo Explains #1 got 987 views.
- 2026-10-29: clean run, Kaggle OK first try (144 s). QC: Lo stood in front of the kitchen sign in meme A; moved him and re-rendered. Improvement: capped Shorts bitrate at 12 Mbps (deepfry meme 42 MB -> 13 MB, tested). Congress skipped (no new session days). Numbers: not enough new samples.
- 2026-10-28: clean run, Kaggle OK first try. QC caught TV text cropped in meme B; fixed and added the tv-text rule here and in STORY_FORMAT.md. Congress skipped again (recess). First Lo Explains (sandwich). Numbers: too few new samples to call anything.
- 2026-10-27 (set-up day): photo review caught people, war and off-topic photos that slipped past the title filter; added broll_block.txt, a stronger filter (no strips, dark frames or scans), and the photos/block review step.
- 2026-10-27 (set-up day, not a nightly run): moved all channels to the Qwen3 house voices; podcasts switched to the visual-first look; Airbnb pronunciation fixed; started this file.

- 2026-11-03: YouTube rejects videos over 15 min on channels that aren't phone-verified ("Upload failed: Video too long"). Keegix and Staffkin are now verified. Any NEW YouTube channel must be verified (youtube.com/verify, switched to that channel) before it gets a long video.
