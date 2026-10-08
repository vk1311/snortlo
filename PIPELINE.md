# Nightly pipeline (run by a Claude scheduled task)

1. `git clone` this repo, run `engine/setup.sh`.
2. Write one new 3-part series in `stories/<slug>/part1..3.json` following STORY_FORMAT.md. Check `stories/` so premises never repeat.
3. Render: `engine/make_video.sh stories/<slug>/partN.json media/<slug>-partN.mp4` for N=1..3 (check each is 61 s+; if short, add a beat and re-render). Join parts into `media/<slug>-full.mp4` with ffmpeg concat.
4. Commit and push. Delete media older than 7 days to keep the repo small.
5. For each video: Postiz `uploadFromUrlTool` with `https://raw.githubusercontent.com/vk1311/snortlo/main/media/<file>`, then `integrationSchedulePostTool` to the Snortlo channels:
   - Part 1 at 11:00, Part 2 at 15:00, Part 3 at 19:00 (America/Halifax) on YouTube (Shorts) and Facebook (Reels); Instagram and TikTok once connected.
   - Full cut at 21:00 on YouTube.
   - Caption: hook line + "Part N/3" + 3-5 hashtags. YouTube title under 70 chars ending in #shorts for the parts.
6. Log what was scheduled in `schedule-log.md` and send the owner a short summary.
