# Waypoint YouTube explainers: format

Approved by Vatsal on Nov 12, 2026. Made on Tuesday and Thursday nights by the "All channels nightly" run, posted on
the **Waypoint Software YouTube channel only**, Mondays and Fridays at 10:00 Halifax. Topics: waypoint/TOPICS.md.

## Feedback from Vatsal
(Chat sessions write his feedback on aired episodes here, newest first. It wins over everything below.)

- (none yet; episode 1 airs Mon Nov 23, 2026)

## What it is
- Waypoint Software's channel: conventional founder content about business basics and how to start a business. The
  things you study in school PLUS the things school never teaches, so people come to YouTube for it.
- NOT a podcast. ONE narrator, no guest, no dialogue. Faceless.
- Style: a How Money Works-style money/business explainer (big question title, narrated, fast-moving visuals) with
  Chill Dude Explains simplicity (plain words, calm, clear).
- His quality test: "If I personally don't watch the video in full, I'll understand it's fluff." He watches every
  episode once it's live and gives feedback in a chat later. **Never add a review/watch item for him and never hold
  an episode for his approval** ("Don't wait for me. Just post it.").

## Look (renderer: engine/podcast.py with brand "waypoint", see engine/podcast_brands.py)
- Visual first, like the podcasts: full-screen CC0 / public-domain photos with slow zoom/pan, a new one every ~7 s,
  info cards, big captions, number cards for every key figure. No photos of people (not even hands), no logos.
  Same photo review and `nightly.py block` routine as the podcasts.
- Waypoint look from github.com/vk1311/Social-posts (waypoint/00-BRAND-BIBLE.md): Manrope type (engine/fonts/Manrope.ttf,
  OFL), "chart" palette (ink #12252F, magenta #C2185B, paper #FBF9F4), faint chart grid + two diagonal bearing lines,
  coordinates (Kentville, 45.08° N 64.50° W), magenta underline bar under the chapter heading, Waypoint mark
  bottom-left, waypointns.ca bottom-right. Never use waypoint/humour/images/ (off-brand).
- AI disclosure: the small "AI voice" corner note plus the description line. Never in the narration.

## Voice
- Narrator `am_eric` (Vatsal's Nov 10 shortlist: am_eric, which he loves, then bm_daniel). Never the two Qwen podcast
  host voices he said hurt his head. Normal speed (PODCAST_TEMPO 1.0, same as the podcasts since Nov 10).
- Same Kaggle fail-safe as podcasts: Kaggle down once -> the episode is DEFERRED to the next night.

## Length
10 to 15 minutes. am_eric at normal speed runs about 2.8 spoken words a second including chapter gaps, so
**1,750 to 2,500 spoken words** (1,832 words = about 11 min). Never pad: if the real material runs 10 minutes,
it's 10 minutes. If a render comes out under 10:00, add a real chapter from research, never filler.
A new YouTube channel must be phone-verified before any video over 15 min.

## No fluff
- The topic starts within the first 15 seconds. No "in this video", no channel intro, no "before we begin",
  no recap padding, no repeating a point in new words.
- Every 45-60 seconds the viewer gets something new: a number, a concrete example, a short story beat, a myth
  busted, or a step they can use.
- **Re-hook every 60 to 90 s** (Vatsal, Nov 16, same rule as PODCAST_FORMAT.md): a tease of what's coming, an open
  question answered a little later, a surprising number, "here's the part nobody tells you". Every tease pays off.
  Start each Short on a re-hook line.
- Structure: cold-open hook -> 3 to 6 chapters that each answer one sharp question -> a short "what to actually do"
  ending with concrete steps. Each chapter opens with an open loop that the chapter pays off.
- Pair "what school teaches" (the textbook idea, explained simply) with "what school doesn't teach" (how it really
  works for a small business in Canada / Nova Scotia).
- FLUFF PASS after writing: read the script line by line and delete every sentence that adds no new information,
  then count words again.

## Honesty
- Every fact, figure and rule is sourced with a URL you actually opened (official and primary sources first: CRA,
  Government of Canada, NS government, Statistics Canada, Competition Bureau, Canadian Anti-Fraud Centre).
- Rules/tax content says "as of <month year>" and "This isn't legal or tax advice."
- Name a real company or person in a scam or wrongdoing context ONLY when a regulator, court or major outlet has
  stated it; otherwise describe the pattern.
- No invented testimonials, results, quotes or prices. Canadian spelling. Never mention Vatsal's day job or employer.
  Never pitch Keegix or Staffkin here (no cross-promotion).

## Hooks (Nov 12, 2026, every video and Short)
- First 3 seconds: (1) bold, short, curiosity-led headline text (the cold open's first card); (2) a sound effect on the
  opening motion (`hook_sfx` in the JSON, any name from engine/sfx.py; vary it); (3) movement (the photos already
  zoom/pan; never a static open). Makes sense with the sound off.
- Opening line uses one formula: "Unexpected Truth", "You vs Problem" or "Fast Reward". Never promise instant
  results, money or outcomes. Record the combo in the JSON `hook` field and in schedule-log.md.

## Waypoint promo (approved Nov 12; its length and placement need Vatsal's OK to change)
- One ~30-second promo segment between 45% and 60% of the runtime, right AFTER an open loop/cliffhanger, then return
  to the cliffhanger. Segment heading and on-screen text: "A quick word from Waypoint (that's us)"; `"promo": true`.
- Message: Waypoint Software builds websites plus the booking, quoting and invoicing tools behind them for small
  service businesses in Atlantic Canada; software built around how you already work; waypointns.ca.
- No prices unless they are on waypointns.ca, no reviews, no hype words (revolutionary, seamless, unlock,
  game-changer, 10x). Vary the wording between episodes.

## End card
The last 5 seconds are the Waypoint end card (mark + "waypointns.ca"), drawn automatically (`outro_len` 5 s).
The script's last line is one short spoken line, e.g. "This is Waypoint Software, at waypointns dot ca."

## Shorts
Exactly 3 Shorts of 30-55 s (about 85 to 150 words) cut from each episode, each standing alone with its own payoff,
each starting on a re-hook line, each with its own `sfx` (hook sound; vary them). The last 2 s are a small
"waypointns.ca" tag (automatic).

## JSON (waypoint/<slug>.json, slug like `wp01-free-certifications`)
Same shape as a podcast episode (PODCAST_FORMAT.md: segments, lines, cards, visuals, sources, shorts), plus:
```json
{"brand": "waypoint", "format": "waypoint-explainer", "episode": 1, "slug": "wp01-...", "air_date": "2026-11-23",
 "topic": 1, "title": "<100 chars, curiosity-led, in the parent video's style", "card_title": "...",
 "thumb_title": "2-5 BIG WORDS", "hook": {"pillars": "...", "formula": "..."}, "hook_sfx": "whoosh",
 "description": "summary lines; sources, chapters and the AI-voice line are appended automatically; include waypointns.ca",
 "tags": ["..."], "segments": [{"heading": "...", "visuals": ["4-8 plain nouns"], "promo": false,
 "lines": [{"who": "host", "text": "...", "card": {...}}]}], "sources": [{"label": "...", "url": "..."}],
 "shorts": [{"title": "max 8 words", "from": [seg, line], "to": [seg, line], "sfx": "ding", "caption": "..."}]}
```
Every line is the narrator's (`who` is forced to "host"). Spoken text follows the podcast TTS rules: no digits,
%, $, dashes, ellipses, parentheses or all-caps words (write "C R A", "M B A", "waypointns dot ca").

## Render and post
```
cd engine && python3 nightly.py render ../waypoint/<slug>.json=../media/wp-<slug>.mp4
```
Outputs: media/wp-<slug>.mp4 (1280x720), -thumb.png, .description.txt, .chapters.txt, .timeline.json,
-short1..3.mp4 (1080x1920), .shorts.json. Posting rules are in the nightly prompt (step 5, "Waypoint explainers").
