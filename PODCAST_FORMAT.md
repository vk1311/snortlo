# Keegix Podcast and Staffkin Podcast: script format

Weekly long-form YouTube episodes (20+ minutes) for the owner's two products, plus 5 Shorts cut from each.
Approved Oct 26, 2026. The full plan is in the Content project doc `claude/brand-podcasts-plan.md`.
The month's approved topics are in `podcasts/TOPICS.md`. Only write episodes for approved topics.

**Not Snortlo.** No stories, no memes, no stick figures, no meme sounds, no "Lo". These are calm, useful,
search-friendly conversations.

Voices: the `voice` names below are the house voices in engine/voices/ (Qwen3-TTS on Kaggle, made Oct 27, 2026; they keep the old Kokoro names). Every line is spoken at 1.10x. See engine/voice_backend.py. Brand names are respelled for the voice automatically (Airbnb -> "Air bee en bee", Vrbo -> "Verbo"; list in voice_backend.SAY): write them normally in the script.

**Look (owner's call, Oct 27, 2026): visuals first, not a "podcast studio".** The screen is full of moving CC0 / public-domain photos that change every ~7 seconds, with big captions, info cards and a small speaker name. Every segment needs a `visuals` list (below). The owner doesn't like plain podcast visuals.

## The shows

| | Keegix Podcast | Staffkin Podcast |
|---|---|---|
| Airs | Tuesdays 10:00 Halifax | Thursdays 10:00 Halifax |
| Scope | The whole B&B and short-term rental industry, worldwide, with Canadian examples: growing bookings, rules and how they're enforced, real host problems (Reddit threads retold), local guides, standards and minimums | Workplace psychology for people who manage people: burnout, power plays, why people quit, conflict, motivation. Every episode mixes the psychology, a bit of history, and real workplace situations |
| Host (fixed) | **June**, voice `af_bella` | **Sam**, voice `am_michael` |
| Brand mention | Once mid-episode and once at the end, max | Once mid-episode and once at the end, max |
| CTA | keegix.com/start (free for one property) or a free Keegix tool that fits the topic, e.g. keegix.com/airbnb-house-rules | "Try it free at staffkin.com" |
| Spelling | Canadian (colour, neighbour, centre) | Canadian (behaviour, labour, centre) |

## Honesty rules (both shows)

- AI disclosure (owner's call, Oct 27, 2026): **keep it small.** A small "AI voices" note sits in the corner of the screen (automatic), and the YouTube description says it (automatic). Don't say "AI host" or "AI character" in the dialogue or put it in roles.
- The guest is a **fictional character**: introduce them as "Rowan plays a B and B owner with twenty years behind the desk. Not a real person, and not a lawyer." Never present the guest as a real person or a real expert. Never invent a credential, an employer, a book or a quote for them.
- Every number, law, date, study or historical claim must come from a source listed in `sources`, with a URL. If you can't source it, cut it.
- Never quote real people at length. Paraphrase. One short quote under 15 words is the maximum per source.
- Reddit threads: retell in your own words, never quote, never give usernames or subreddit post titles. Say "a host on Reddit described…".
- Rules and law: say "as of <month year>", say rules vary by city or province, and end that segment with "This isn't legal advice."
- No invented testimonials, user counts, or results ("save 5 hours"). Mechanisms only.
- Don't name competitors of Keegix or Staffkin.
- Staffkin: plan everything as Nova Scotia-based; never mention the owner's day job or employer.
- Keegix: never call Keegix an "Airbnb alternative". It sits beside the booking platforms.
- Keep it respectful: humour about situations, never about guests, hosts, employees or groups of people.

## Episode shape (20 to 26 minutes, 3,700 to 4,300 spoken words)

The Qwen3 house voices at 1.10x speak about 3 words a second including pauses, so 3,700 words is about 20.5 minutes. Under 3,700 words the episode comes out under 20 minutes (Keegix ep 1 at 3,346 words was 18.4 min).

1. **Cold open** (30 to 45 s): the most surprising fact or situation from the episode. No hello yet.
2. **Intro** (about 1 min): show name, "I'm June", what the episode covers, introduce the guest as a character ("Rowan plays…", "not a real person").
2b. **In the news** (60 to 90 s, optional): real news from the last 14 days, sourced, "as of <date>". See CONCEPTS.md for where to look. Skip it if there's nothing real.
3. **4 or 5 main segments** (3 to 5 min each). Each has a clear heading that reads like a search query or chapter title.
4. **Mid-episode brand mention** (2 or 3 sentences, natural, after segment 2 or 3).
5. **Recap** (about 1 min): 3 to 5 takeaways.
6. **Outro** (30 s): CTA, "sources are in the description", next week's topic if known.

Dialogue style:
- Natural conversation. The host asks and reacts; the guest explains. Turns of 1 to 5 sentences, with a few longer explanations.
- Use concrete situations: "Say your best line cook starts showing up late and snapping at servers."
- Short reactions are fine ("Right.", "Wait, really?", "That's the part people miss.") but no fake laughing, no "um".

## Text-to-speech rules (spoken `text` only)

- Short to medium sentences. Periods, commas, question marks, apostrophes, quotation marks.
- No em or en dashes, no ellipses, no parentheses, no emojis, no all-caps words, no bullet lists.
- Write numbers the way they're said: "fifteen point five percent", "twenty twenty-six", "one hundred and eighty nights". Years are fine as words. Cards can use digits.
- Spell out abbreviations the first time and write how they're said: "the W H O", "S T R". Avoid symbols like % $ & /.
- Simple names. The guest's name should be easy to say.

## JSON file

One file per episode: `podcasts/<brand>/<slug>.json`, slug like `keegix-ep01-str-rules-2026`.

```json
{
  "brand": "keegix",
  "episode": 1,
  "slug": "keegix-ep01-str-rules-2026",
  "air_date": "2026-11-03",
  "title": "Short-Term Rental Rules in 2026: What's Changing and How It's Enforced | Keegix Podcast",
  "card_title": "Short-term rental rules in 2026",
  "guest": {"name": "Rowan", "role": "B&B owner, 20 years", "voice": "bm_george"},
  "description": "3 to 6 short lines. Line 1 says what the episode covers. Include: 'Hosts and guests on this show are AI voices. Facts are sourced below.' Rules episodes include 'Not legal advice.' Sources and chapters are appended automatically.",
  "tags": ["short term rental rules", "airbnb rules 2026"],
  "segments": [
    {"heading": "Cold open", "visuals": ["unmade bed", "laundry basket", "dishes sink"], "lines": [
      {"who": "host", "text": "Spoken words."},
      {"who": "guest", "text": "Spoken words.", "card": {"type": "stat", "big": "180 nights", "label": "Toronto's yearly cap for renting out a whole home", "source": "City of Toronto"}}
    ]}
  ],
  "sources": [{"label": "City of Toronto: Short-term rentals", "url": "https://..."}],
  "shorts": [
    {"title": "On-screen hook, max 8 words", "from": [2, 0], "to": [2, 6], "caption": "Post caption for Reels/Shorts, 1 to 2 lines plus 3 hashtags"}
  ]
}
```

- `guest.voice`: pick one not used in the last 3 episodes of that show. Good choices: `bm_george`, `bf_emma`, `am_adam`, `af_nicole`, `bm_lewis`, `af_sarah`, `am_eric`, `bf_isabella`, `af_kore`, `bm_daniel`. Never the host's voice.
- `segments[].heading`: shown on screen and used as the YouTube chapter title.
- `segments[].visuals`: **required**, 4 to 8 photo searches per segment (1 to 3 plain words each) that match what's being said, in order: places, objects, scenes, e.g. "Halifax waterfront", "smoke alarm", "typewriter", "warehouse shelves". Each search brings up to 3 CC0 / public-domain photos (Openverse, Wikimedia Commons, NASA), so 6 searches fill a 4-minute segment without repeats. No people searches, no brand logos, never a person's name. (`broll`, a single search, still works as a fallback.)
- `lines[].card`: optional on-screen card that stays up until the next card or the end of the segment. `"card": "clear"` removes it. Types:
  - `{"type": "stat", "big": "40%", "label": "short explanation", "source": "short source name"}`
  - `{"type": "list", "title": "...", "items": ["max 4 items, max 6 words each"], "source": "optional"}`
  - `{"type": "point", "text": "One takeaway, max 14 words"}`
  - `{"type": "compare", "left_title": "...", "left": "...", "right_title": "...", "right": "..."}`
  - `{"type": "rule", "title": "Where", "text": "What the rule says, max 18 words", "source": "...", "as_of": "Oct 2026"}`
  - `{"type": "history", "year": "1974", "text": "What happened, max 16 words"}`
  Aim for one card every 30 to 60 seconds of talk.
- `shorts`: exactly 5 clips. `from` and `to` are `[segment index, line index]`, inclusive, both zero-based. Each clip runs 30 to 55 seconds (roughly 80 to 140 words), starts with a line that works as a hook on its own, and makes sense without the rest of the episode. Don't cut mid-thought.

## Before finishing

- `python3 -c "import json;json.load(open('podcasts/<brand>/<slug>.json'))"` loads.
- Count spoken words (target 3,700 to 4,300).
- Scan spoken text for digits, %, $, dashes, ellipses, parentheses, all-caps words.
- Every card and every factual line traces to an entry in `sources`.
- After rendering: review every photo (`python3 engine/nightly.py photos media/pod-<slug>.timeline.json`, then look at engine/photos.png), block anything with people, war or military scenes, politicians, logos, dark frames or off-topic shots (`nightly.py block …`), and re-render.

## Render

```
cd engine && python3 podcast.py ../podcasts/<brand>/<slug>.json ../media/pod-<slug>.mp4
python3 podcast_shorts.py ../podcasts/<brand>/<slug>.json ../media/pod-<slug>.mp4
```
See PIPELINE.md, section "Brand podcasts".
