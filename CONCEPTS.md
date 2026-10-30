# Concept ideas and news: where they go (approved Oct 27, 2026)

The owner's concept list feeds two places. Anything not listed here stays parked.

## 1. Snortlo: "Lo Explains" (new series)

Short animated explainers starring Lo, our teal-cap guy, in the normal Snortlo stick-figure style. They're still funny and relatable, but every episode teaches one surprising, true thing.

- **When:** Mon, Wed and Fri. It takes meme B's slot: YouTube and Facebook always, Instagram only on 1-part story days, same as meme B. Meme B still goes to Facebook those days. Caps don't change: Snortlo YouTube ≤ 4/day, Instagram 3 reels/day.
- **Format:** a normal story JSON (STORY_FORMAT.md) with top-level `"series": "Lo Explains #<n>"` and `"format": "concept"`. One part only, 45 to 70 s. A hook question in the first line ("Why do you forget dreams in 10 seconds?"), Lo acting out the idea, one twist or "wait, what?" fact around the middle, a satisfying answer, and the share sticker end card (`SEND THIS TO|YOUR <person>`).
- **Facts:** every fact needs a source the run actually opened (official, university, museum, encyclopedia). Put the sources in the YouTube/Facebook description as "Sources: …". Leave out anything you can't confirm. No medical advice. Body topics explain how things work and never tell anyone what to take or do.
- **Topic bank** (rotate, never repeat a topic in stories/, strike it here when used):
  - **Dreams:** why we forget dreams; why you can't read in dreams; falling dreams; lucid dreaming basics; do animals dream
  - **Your body explained:** how sleep works; why we yawn; hiccups; brain freeze; why onions make you cry; goosebumps; why your stomach growls; why your foot "falls asleep"
  - **Geography:** the country with the most time zones; a town split by a border; the coldest inhabited place; why Canada has so many lakes; places with weird names
  - **Ancient times:** the oldest written complaint; ancient Roman fast food; who invented the toothbrush; ancient board games
  - **History stories:** ~~how the sandwich got its name~~ (Lo Explains #1, Oct 28); the first speeding ticket; the Great Emu War; why we say "OK"; the man who sold the Eiffel Tower (fraud story, keep it light)
  - **Business explained:** ~~why everything ends in .99~~ (Lo Explains #2, Oct 30); how free apps make money; why airlines overbook; what a franchise really is; why stores put milk at the back
  - **Meme trend reviews:** where a currently trending meme format came from and why it spreads. Talk about the format; never reuse anyone's clip.
- **Logging:** `python3 engine/log_post.py concept <slug> 1 "<title>" '{"series":"Lo Explains"}' <UTC time>` so it shows up in metrics.

## 2. Brand podcasts: concepts and news

- **Monthly topic lists** (made when a month runs out, sent to the owner for approval) may use these concepts when they fit the show:
  - **Staffkin:** how sleep affects work; what stress does to your body at work; why we procrastinate; business explained simply (payroll, overhead, why small firms lose good people)
  - **Keegix:** travel geography and why guests choose a region; local attractions and guides; the history of inns and guesthouses
  - Autocomplete still decides which ones people actually search for.
- **News in every episode:** a 60 to 90 s "In the news" segment right after the intro, using news from the last 14 days at the time of writing, sourced. Say "as of <date>".
  - **Keegix:** start from Pappu's weekly STR news rows in the agent handoff sheet (Google Sheet 1UDh-BqIVvPQhPpsRe0U8jXA7ZQ9GmHzyCCLuTgi1j3s, tab "Untitled", rows from Pappu with business Keegix), then web search to confirm.
  - **Staffkin:** Canadian and Nova Scotia employment and HR news.
  - If there's no real news, skip the segment rather than pad it.

## Still parked (no action)

Book summaries (animated or detailed), controversy beginnings and a separate infographic show.
