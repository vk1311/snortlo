# Proposed next version of the nightly task (waiting for owner approval)

Adds to the current nightly run (stories + memes when memes/ENABLED exists):
- **Weekly compilation, Sundays 12:00:** the week's stories joined into one long video, posted to YouTube and Facebook (engine/compile.py). Every story also gets a full cut every night, but the full cut is posted on Wednesdays only.
- **Congress Moments,** only if gov/ENABLED exists:
  - One clip a day from House floor video, following the rules in GOV_SOURCES.md.
  - Posted to Facebook and Instagram daily at 13:00, and to YouTube on Mon/Tue/Thu/Sat.
  - Logged in gov/used.txt, which also tracks balance across parties.
- **Sleep stories,** only if longform/ENABLED exists: a new compilation every Friday at 21:00, posted to YouTube and Facebook (engine/longform.py, then shrink.sh).
- **YouTube cap:** at most 5 Snortlo uploads a day. Every day gets the story parts 1–3 and meme A, plus one extra that depends on the day: Wed full cut, Fri sleep stories, Sun compilation, and the Congress clip on the other days.
- Delete media older than 8 days instead of 7, so Sunday's compilation still has all the full cuts.
