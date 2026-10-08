# Nightly pipeline (run by the "Snortlo nightly story" scheduled task)

1. `bash engine/setup.sh`
2. Score past posts: `python3 engine/metrics.py` (reads YouTube view counts into experiments/log.csv)
3. Pick tonight's settings: `python3 engine/pick.py story` and `python3 engine/pick.py meme` (also rewrites experiments/REPORT.md)
4. Write the story (3 parts) and memes to match the picked settings; render with `engine/make_video.sh <json> <mp4>`
5. Upload via Postiz (raw.githubusercontent.com URLs), schedule, and log each YouTube post with `engine/log_post.py`
6. Commit + push

Experiment variables and their options live in experiments/arms.json. The scoreboard is experiments/REPORT.md.
YouTube is the scoreboard because it is the only platform readable without logins; posts go to Facebook/Instagram with the same settings.
