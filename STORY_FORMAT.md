# Story script format

One JSON file per part. Top level:

```json
{"channel": "Snortlo", "part": "Part 1", "voice": "af_heart", "speed": 1.2, "beats": [ ... ]}
```

Each beat = one spoken line plus what the viewer sees while it plays.

| key | meaning |
|---|---|
| `text` | the narration line (keep lines short and punchy) |
| `set` | `kitchen`, `night` (dark kitchen), `office`, `desk`, `closeup` |
| `state` | set options: kitchen/night `fridge_open`, `fridge_contents` (["lunch","cup"]), `clock` ("12:00"), `sign` ("LINE1\|LINE2"); office `table`, `cooler` (false hides it), `whiteboard` ("LINE1\|LINE2"); desk `minifridge`, `desk`; closeup `show` = `pepper`/`label`/`note`/`notebig` (+`note_lines`)/`part2`, `bg1`, `bg2` colours |
| `cast` | list of characters on screen (see below) |
| `speaker` | who's talking: their mouth moves |
| `bubble` | `{"text": "...", "x": 560, "y": 520, "tail": 30}` speech bubble |
| `cards` | e.g. `["MON","TUE","WED"]`, pop in across the line |
| `props` | `[{"type": "pot", "x": 880, "y": 890}]`: pot, pepper, lunch, cup, paper, note, sandwich |
| `cam` | `{"zoom": 1.6, "on": "boss"}` or `{"zoom": 1.2, "at": [x, y]}` |
| `meme` | `shake` or `slowzoom` |
| `sfx` | `vineboom`, `bruh`, `rimshot`, `airhorn`, `scratch`, `sadtrombone`, `crickets`, `heartbeat`, `riser`, `dundun`, `slideup`, `slidedown`, `pop`, `whoosh`, `tick`, `ding`. Punchline sounds (vineboom, bruh, rimshot, airhorn, sadtrombone, crickets, dundun) land right after the line with a pause and camera punch |
| `slow`, `pause` | slower delivery / extra seconds after the line |

Cast entry: `{"who": "me|boss|co1|co2|co3", "x": 100-980, "to": x (walks there), "facing": 1|-1, "pose": ..., "act": ..., "hold": ..., "face": {"eyes": ..., "mouth": ...}, "fx": {"red": 0-1, "sweat": true, "steam": true}}`

- poses: stand, talk, point, shrug, shocked, facepalm, hips, cross, drink, eat, reach, hold, stir, celebrate, laugh, slump, sneak, relax, evil
- acts: talk, stir, drink, laugh, shake, bounce
- hold: lunch, cup, sandwich, paper
- eyes: dot, wide, happy, angry, flat, closed, worried, smug
- mouths: smile, grin, frown, o, flat, wavy

Stage layout: ground is y=1180. Kitchen fridge at x 350-580, stove/counter x 680-1080 (pot at 880,890). Office whiteboard top-left, water cooler x 880, table x 180-740. Put 1-4 characters 200+ px apart.

## Writing rules
- **Stories are 1 or 2 parts (since Oct 16, 2026).** pick.py's `parts` setting decides. **Every part must be satisfying on its own:** someone who only ever sees that one video gets a complete joke with a payoff.
- **Length:** each part is about 210-230 words, so it runs 61-70 s at 1.2x (keep it over 1 minute).
- **Openings and pacing:** open on the hook in the first line, with no intro and a sound in the first 1.5 s. Put a twist or reveal, with a combo sound, around the 30 s beat; that's where viewers drop off.
- **1-part stories:**
  - Full arc in one video: hook, escalation, twist, payoff.
  - Title has no part tag, just the title and "#shorts".
  - End with the share sticker (below).
- **2-part stories:**
  - Titles end "(Part 1/2) #shorts" / "(Part 2/2) #shorts".
  - **Part 1** resolves its own mini-conflict with a real punchline. Only after that punchline does it open a bigger question ("…and that wasn't even the worst part"); never stop mid-scene. It carries `"end_card": {"text": "PART 2 IS UP|ON THE PROFILE", "secs": 3}`. Part 2 is posted 30 minutes BEFORE Part 1, so the card is true the moment anyone sees it, and the two sit side by side on the profile.
  - **Part 2** works for someone who never saw Part 1: a one-line recap gives all the context needed. Then it has its own escalation and payoff, ends teasing the next story, and carries the share sticker.
- **Share sticker:** `"end_card": {"text": "SEND THIS TO|YOUR <BROTHER/WIFE/BESTIE>", "secs": 2.5}`, naming whoever the story is about.
- A meme sound every one or two lines; vary them. Visual punch (zoom/shake) on the big moments.
- Original stories only: real threads can inspire the premise, but rewrite everything, change the details, use no real names, and never copy text.
- Keep it light: no politics, no punching down, nothing hateful or sexual, no real private people.

## New sets
`bedroom` (state: `dark`, `phone` = blue phone glow, `clock`), `classroom` (`board` = "LINE1|LINE2", `clock`), `street` (`night`), `living` (`tv` = "TEXT|TEXT", `dark`). `closeup` also takes `show: "text"` with `big` ("YOU|TOO?!") and `color`.

## Sounds (83, see engine/sounds/CREDITS.md)
Any name below works in `sfx`. Use `random:punch` / `random:accent` to let the engine pick. Every use gets a slight random pitch/volume change so repeats never sound identical.
- **Punchline** (lands after the line, or as a silent shot appears): vineboom, bruh, fahh, huh, oof, nooo, waitwhat, rimshot, sadtrombone, airhorn, crickets, dundun, metalpipe, bonk, sadviolin, recordscratch, laughtrack, ooh, aww, gasp, gong, applause, crowdcheer, boo, buzzer, success, fanfare, sting, goat, evillaugh, yay, angelchoir, thunder, glass, carcrash, slap, cashregister
- **Accent** (on the line): pop, ding, tick, whoosh, boing, scratch, slideup, slidedown, riser, heartbeat, shutter, cork, splash, tirescreech, doorslam, drumroll, meow, bark, chicken, crunch, gulp, whistle, squeak, alarm, sparkle, typebell, rizz (eyebrow-raise glide), payding (tap-to-pay chime), textbuzz (phone buzzes twice + ping)
- **New punchlines (Oct 2026, trending sound types, made from scratch):**
  - bonecrack: crunchy snap for a brutal comeback or physical fail
  - clownhorn: honk-honk when someone just played themselves
  - phonk: cowbell + 808 sting for "X years later", glow-ups and flexes
  - aura: shimmer into boom for a cool move ("+1000 aura")
  - reveal: dark dramatic stab for the twist or "it was YOU"
  - toot: cartoon fart, by name only and at most once a week
  - shouts: ayo (edgy line), ohno (dread), wow (impressed), hmm (suspicious)
- **Combos (layered punches, the strongest option for the final beat):**
  - roast: vineboom + crowd "ooh" for a savage reply
  - caught: record scratch + crickets when someone is caught
  - ko: slap + crack + "ooh" for a verbal knockout
  - busted: reveal + gasp when the twist lands
  - brokeboi: pay chime + sad trombone for money jokes
  - smooth: rizz + sparkle for the smooth line
  - clowned: clown horn + laugh track when someone gets clowned
- **How to use them (from the Oct 15 analytics):**
  - Put a sound in the first 1.5 s of every video; the swipe decision happens there.
  - Stories lose most viewers around 25–40 s, so put a combo or reveal on the beat around 30 s.
  - Use at most one combo per video, on the biggest punch. Mix older Vine-era classics (vineboom, bruh, metalpipe, oof) with the new ones, since our viewers are mostly 25–44.
- Never add ripped audio from shows, films, songs or other creators. New sounds must be CC0 (Freesound filter "Creative Commons 0"), synthesized, or voiced by our own TTS, and get a line in CREDITS.md.

# Meme format (memes/<slug>.json)
Short (6–16 s) recreations of well-known meme formats, drawn with our cast. Top level adds `"format": "meme"` and usually `"music": false`; no `part`, no minimum length.
- Layout: white caption band on top, scene below, karaoke captions near the bottom.
- `top_text`: the meme caption for that beat ("Nobody:", "Me at 3 AM:", "POV: …"; `|` = new line).
- `text` may be empty for a silent reaction shot; then set `hold` (seconds). A punch `sfx` on a silent shot hits as the shot appears.
- `voice` per beat lets characters sound different (e.g. mom = af_bella).
- `meme: "deepfry"` = crushed, oversaturated, grainy look from the punch onwards. Use on the final punch only.
- Recreate the *format*, never the original image, clip or character. No copyrighted characters, no real people.
- **Recurring series "Lo vs Life" (since Oct 16, 2026):** every meme stars **Lo**, our teal-cap guy (cast `me`), against everyday life: his wife, mom, brother, bestie, boss, money and sleep.
  - **Header:** set top-level `"series": "Lo vs Life #<n>"`, where n = the number of memes in memes/ that already have a `series` field, plus 1. It shows in the header pill as "Snortlo · Lo vs Life #n".
  - **Sound logo:** every meme opens with Lo's snort automatically. Only set `"sting": false` if the snort ruins a joke.
  - **Captions:** keep them relatable ("Me when…", "My wife at 2 AM:"). Lo is the viewer's stand-in, so don't write "Lo" in the caption.
  - **Post captions:** end with "#LoVsLife".
- **Share sticker (since Oct 16, 2026):** every meme gets `"end_card": {"text": "SEND THIS TO|YOUR <WIFE/HUSBAND/BROTHER/SISTER/MOM/BESTIE>", "secs": 2}`, naming the person the joke is about. It pops in over the last 2 s without adding length, so the loop stays seamless. Plain text only (the font has no emoji).
- Examples: memes/3am-snack.json, memes/you-too.json.
