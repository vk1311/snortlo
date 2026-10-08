# Long-form sleep story format

One weekly compilation of calm, original "stories to fall asleep to" for YouTube and Facebook. One JSON file per compilation in `longform/`, named `sleepy-stories-<n>.json`. Example: `longform/sleepy-stories-1.json`.

## JSON shape

```json
{"title": "Cozy Stories to Fall Asleep To 🌙 6 Calm Tales | Snortlo",
 "voice": "af_heart", "speed": 0.92,
 "intro": "...",
 "stories": [{"title": "The Night Baker", "text": "Paragraph one.\n\nParagraph two."}],
 "outro": "...",
 "description": "line 1\nline 2\nline 3",
 "tags": ["sleep stories", "bedtime stories for adults"]}
```

- Valid UTF-8 JSON. Check it loads with `python3 -c "import json;json.load(open('longform/sleepy-stories-N.json'))"`.
- `voice` stays `af_heart` and `speed` stays `0.92` unless the renderer changes.
- Story paragraphs are separated by a blank line (`\n\n`). No other formatting inside `text`.
- Exactly 6 stories.

## Length targets

- Each story: 1,000 to 1,300 words. Whole compilation: about 7,000 to 7,500 words, roughly 45 to 50 minutes at a slow pace.
- Intro: 80 to 120 words. Outro: 60 to 90 words.
- Count the words before you finish and report them per story and in total.

## Titles

- YouTube title under 90 characters, ends with `| Snortlo`, one 🌙 at most.
- Rotate patterns so weeks don't look identical:
  - `Cozy Stories to Fall Asleep To 🌙 6 Calm Tales | Snortlo`
  - `Sleepy Stories for Grown-Ups 🌙 Rain, Tea and Quiet Places | Snortlo`
  - `45 Minutes of Calm Bedtime Stories for Adults | Snortlo`
  - `Fall Asleep Fast 🌙 6 Gentle Stories on a Rainy Night | Snortlo`
  - `Bedtime Stories for Adults 🌙 Night Shifts and Quiet Streets | Snortlo`
- Story titles: short and plain, like "The Night Baker" or "The Library After Closing". No puns that need explaining.

## Intro and outro

- Intro: soft welcome, name the channel once, say how many stories, invite the listener to get comfortable and dim the lights, tell them they don't need to stay awake till the end, one slow breath, "Let's begin."
- Outro: gentle goodnight, one line that touches each story's closing image, a soft mention that more stories are on the channel. No "like and subscribe", no calls to action beyond that one line.

## Tone

- Cozy, warm, low-stakes, gently funny. Light smiles, never punchlines.
- Slow and descriptive with soft sensory detail: rain on windows, warm lamplight, tea, bread, quiet streets, ticking clocks, snow, the sea.
- Small, kind characters doing ordinary things well. Night shifts and in-between hours work beautifully.
- Each story resolves and ends softly, ideally on someone settling down, a light going on or off, or a quiet repeated sound. The last lines should slow down.
- Vary the settings across the six stories: indoor and outdoor, town and coast, people and animals, weather.

## Never include

- Cliffhangers, danger, injury, illness, death, violence, villains, or anything scary.
- Romance or sexual content, politics, religion as a topic, news, money worries.
- Real people, real brands, real products, or real place names. Generic places only: "a small fishing town", "Elm Lane", "the city".
- Copied or closely paraphrased wording from any published story. Every story is written fresh.

## Text-to-speech rules

- Short to medium sentences. Plain punctuation only: periods, commas, question marks, quotation marks, apostrophes.
- No em dashes or en dashes. Use a comma or a full stop instead.
- No ellipses, no parentheses, no emojis inside stories, no all-caps words, no bullet lists, no headings.
- Spell out numbers under 100 in words: "two in the morning", "thirty years", "half past three". Avoid digits altogether in story text.
- Simple, easy-to-pronounce names: Mabel, Theo, Ruth, Nora, Walt, June, Henry, Mr. Pell, Mrs. Lowe. Avoid invented or unusual spellings.
- Sounds can be written as soft words the voice can say: "pat, pat, pat", "clickety clack", "shh". Keep them gentle.
- Signs and notes in the story are written as plain sentences, never in capitals.
- Before finishing, scan for digits, dashes, ellipses, parentheses and capitalised words.

## Description and tags

- Description: 3 to 5 short lines, no links. Line 1 says what it is, line 2 lists the six settings in one sentence, line 3 promises no drama, last line is a soft goodnight. One 🌙 is fine.
- Tags: 8 to 12. Keep the core set and add a few that match this week's settings: `sleep stories`, `bedtime stories for adults`, `stories to fall asleep to`, `cozy stories`, `calm stories`, `relaxing stories`, `sleep story compilation`, `bedtime stories`, `soothing stories`, `fall asleep fast`, `insomnia relief`, `Snortlo`.

## Weekly checklist

1. Pick six premises from the bank below, varied in setting and mood, and strike them off.
2. Write each story at 1,000 to 1,300 words.
3. Write the intro, outro, title, description and tags.
4. Build the JSON, check it loads, count words, run the TTS punctuation scan.

## Premises already used

- Compilation 1: midnight laundromat with a lost-sock board; lighthouse caretaker and an opinionated gull called the Captain; night baker on a snowy morning; a cat who runs Elm Lane; overnight sleeper train with cocoa; night custodian reading the returned library books.

## Story idea bank (25)

1. A night-shift bus driver on the last route of the evening, with three regular passengers who never speak but always wave.
2. An old woman who runs a tiny greenhouse and talks each plant through a frosty night.
3. A clock repairer setting every clock in his shop to chime at the same moment, just once, at the end of the day.
4. A ferry crossing a still lake at dusk, and the ferryman who names the ducks.
5. A mountain hut where a warden keeps the stove lit for hikers who arrive late and soaked.
6. A post office on the last evening before a holiday, sorting letters and parcels into their little wooden slots.
7. A beekeeper closing up the hives for winter and wrapping them in old blankets.
8. A night watchman at a small museum who says good night to each painting.
9. A tea shop on a rainy afternoon where every customer orders something different and the owner remembers them all.
10. A fisherman's wife mending nets by lamplight while the boats come home one at a time.
11. A town bandstand after the last concert, and the man who stacks the chairs and plays one quiet note on the piano.
12. A dog who walks the same retired postman around the village every evening, and decides the route.
13. A snowed-in country inn where the guests pass the evening with soup, cards and a slow jigsaw puzzle.
14. A candle maker pouring the last batch of the night, each scent named after a season.
15. An allotment gardener counting pumpkins on the first cold morning of autumn.
16. A night nurse for newborn lambs on a small farm, warm milk bottles and straw.
17. A small-town radio host on the overnight show who reads out the weather and requests from three loyal listeners.
18. A houseboat on a canal in the rain, and the owner who keeps a kettle and a cat on board.
19. A hotel night porter polishing the brass and helping one sleepy guest find a spare toothbrush.
20. A girl and her grandfather stargazing from the roof with a flask of cocoa and a very old telescope.
21. A bookbinder repairing a much-loved old cookbook page by page.
22. A tortoise in a walled garden on a slow summer evening, taking all afternoon to reach the strawberry patch.
23. A cobbler who leaves each repaired pair of shoes on the shelf with a little note.
24. An owl who keeps watch over a sleeping orchard and approves of very little.
25. A seaside ice cream kiosk closing up at the end of the last warm day of the year.
