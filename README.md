# Snortlo

Animated, meme-heavy story shorts, made 100% with free and open-source tools.

- `engine/`: the animation engine (stick-figure rig, sets, props, camera), voice (Qwen3 house voices on Kaggle's free GPU via engine/voice_backend.py, with a Chatterbox/Kokoro fail-safe; Whisper timing) and synthesized meme sounds
- `stories/`: each story is a folder of parts; each part is a JSON script with stage directions per line
- `media/`: rendered videos

Make a video:

    engine/setup.sh            # once
    engine/make_video.sh stories/lunch-thief/part1.json media/lunch-thief-part1.mp4

One scheduled task, "All channels nightly", runs everything (Snortlo, sleep stories, Keegix/Staffkin podcasts) using engine/nightly.py; see NIGHTLY.md. See PIPELINE.md for the nightly routine and STORY_FORMAT.md for how scripts are written.
