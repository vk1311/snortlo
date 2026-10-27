# Nightly task schedule (UPDATED Oct 27, 2026; the live prompt is in the scheduled task "All channels nightly")

**Oct 27, 2026:**
- One nightly run now does every channel: Snortlo, sleep stories, and on Saturdays and Mondays the Keegix and Staffkin podcasts.
- Voices come from Qwen3 house voices on Kaggle at 1.10x, with a fail-safe (engine/voice_backend.py, engine/nightly.py).
- New Snortlo series "Lo Explains" posts Mon, Wed and Fri in meme B's slot (CONCEPTS.md).

**Oct 26, 2026: the YouTube cap drops from 5 to 4 Snortlo uploads a day.** The owner's new Keegix Podcast and Staffkin Podcast (see PODCAST_FORMAT.md) use up to 2 uploads a day from the same shared Google quota (about 6 a day for all channels). The owner is asking Google for a free quota increase; once approved, the cap goes back to 5.

Owner approved on Oct 15, 2026 (after the first-week analytics review):
- 1–2 part stories where every part stands on its own
- meme B on YouTube in place of Part 3
- the recurring meme series "Lo vs Life"
- YouTube long form paused, except sleep stories
- the Part 2 hand-off fix
- Instagram cut to 3 reels a day, with share stickers

Earlier schedule: Oct 8.

## Stories (always on): 1 or 2 parts, never 3
- pick.py's `parts` setting (1 or 2) is an experiment.
- Part 1 (or the single part) posts at the picked `part1_hour`. In 2-part stories, Part 2 posts **30 minutes before** Part 1, so Part 1's "PART 2 IS UP" sticker is true and the two sit side by side on the profile.
- On 1-part days Instagram gets the story plus memes A and B.

## Memes: "Lo vs Life"
Every meme is an episode of Lo vs Life. See STORY_FORMAT.md for the series tag, the snort sound logo and the #LoVsLife hashtag.
- Every story still gets a full cut (`media/<slug>-full.mp4`). It's used for the Wednesday Facebook post and the Sunday Facebook compilation.

## Daily posting grid (America/Halifax)
| Post | YouTube | Facebook | Instagram |
|---|---|---|---|
| Story Part 2 (part1_hour − 30 min) | yes | yes | yes |
| Story Part 1 (part1_hour) | yes | yes | yes |
| Meme A (its post_hour) | yes | yes | yes |
| Meme B (its post_hour, moved 2 h if it clashes with A or the story) | **yes (new)**, except Mon/Wed/Fri when Lo Explains takes this slot | yes | no |
| Lo Explains (Mon/Wed/Fri, at meme B's hour) | yes | yes | only on 1-part days |
| Congress Moment, 13:00 (if gov/ENABLED) | only when it fits the 4-upload cap (1-part days, never Friday) | daily | **no** |
| Sleep stories, Fridays 21:00 (if longform/ENABLED) | yes | yes | no |
| Story full cut, Wednesdays (2 h after Part 1) | **no (paused)** | yes | no |
| Weekly compilation, Sundays 12:00 | **no (paused)** | yes | no |

- **YouTube:** at most **4** uploads a day. Fill in this order: the story parts (1 or 2), meme A, meme B, then Congress. On Fridays the sleep story takes the last slot (so Congress is off YouTube, and on 2-part Fridays meme B is too). 2-part day = Part 1, Part 2, meme A, meme B. 1-part day = the story, meme A, meme B, Congress. The upload quota is shared with the owner's other channels, so never go over 4.
- **Instagram:** 3 reels a day: Part 2, Part 1 and meme A, or on 1-part days the story plus memes A and B. Reach stalled after Oct 11 while we were posting 6 a day.
- **Share stickers:** every meme and every Part 2 ends with a "SEND THIS TO YOUR …" sticker (`end_card`, see STORY_FORMAT.md). Part 1 ends with "PART 2 IS UP / ON THE PROFILE".
- **Experiments:** log both memes (A and B) with log_post.py now that both go to YouTube.
- **Housekeeping:** delete media older than 8 days, so Sunday's compilation still has the week's full cuts.

## Review
Look at the YouTube stayed-to-watch rate, Instagram reach, and subscriber and follower growth after about 10 days (around Oct 26). If YouTube long form is wanted back, re-enable it then.
