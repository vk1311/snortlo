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
- Each part: about 210-230 words, so it runs 61-70 s at 1.2x (TikTok only pays on videos over 1 minute).
- Part 1 opens on the hook, no intro. Parts 2+ open with a one-line recap.
- Every part ends on a cliffhanger, except the last, which pays off and teases the next story.
- A meme sound every one or two lines; vary them. Visual punch (zoom/shake) on the big moments.
- Original stories only: real threads can inspire the premise, but rewrite everything, change the details, use no real names, and never copy text.
- Keep it light: no politics, no punching down, nothing hateful or sexual, no real private people.

## New sets
`bedroom` (state: `dark`, `phone` = blue phone glow, `clock`), `classroom` (`board` = "LINE1|LINE2", `clock`), `street` (`night`), `living` (`tv` = "TEXT|TEXT", `dark`). `closeup` also takes `show: "text"` with `big` ("YOU|TOO?!") and `color`.

## Sounds (63, see engine/sounds/CREDITS.md)
Any name below works in `sfx`. Use `random:punch` / `random:accent` to let the engine pick. Every use gets a slight random pitch/volume change so repeats never sound identical.
- **Punchline** (lands after the line, or as a silent shot appears): vineboom, bruh, fahh, huh, oof, nooo, waitwhat, rimshot, sadtrombone, airhorn, crickets, dundun, metalpipe, bonk, sadviolin, recordscratch, laughtrack, ooh, aww, gasp, gong, applause, crowdcheer, boo, buzzer, success, fanfare, sting, goat, evillaugh, yay, angelchoir, thunder, glass, carcrash, slap, cashregister
- **Accent** (on the line): pop, ding, tick, whoosh, boing, scratch, slideup, slidedown, riser, heartbeat, shutter, cork, splash, tirescreech, doorslam, drumroll, meow, bark, chicken, crunch, gulp, whistle, squeak, alarm, sparkle, typebell
- Never add ripped audio from shows, films, songs or other creators. New sounds must be CC0 (Freesound filter "Creative Commons 0"), synthesized, or voiced by our own TTS, and get a line in CREDITS.md.

# Meme format (memes/<slug>.json)
Short (6–16 s) recreations of well-known meme formats, drawn with our cast. Top level adds `"format": "meme"` and usually `"music": false`; no `part`, no minimum length.
- Layout: white caption band on top, scene below, karaoke captions near the bottom.
- `top_text`: the meme caption for that beat ("Nobody:", "Me at 3 AM:", "POV: …"; `|` = new line).
- `text` may be empty for a silent reaction shot; then set `hold` (seconds). A punch `sfx` on a silent shot hits as the shot appears.
- `voice` per beat lets characters sound different (e.g. mom = af_bella).
- `meme: "deepfry"` = crushed, oversaturated, grainy look from the punch onwards. Use on the final punch only.
- Recreate the *format*, never the original image, clip or character. No copyrighted characters, no real people.
- Examples: memes/3am-snack.json, memes/you-too.json.
