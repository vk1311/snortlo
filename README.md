# Snortlo

Animated, meme-heavy story shorts, made 100% with free and open-source tools.

- `engine/`: the animation engine (stick-figure rig, sets, props, camera), voice (Kokoro TTS + Whisper timing) and synthesized meme sounds
- `stories/`: each story is a folder of parts; each part is a JSON script with stage directions per line
- `media/`: rendered videos

Make a video:

    engine/setup.sh            # once
    engine/make_video.sh stories/lunch-thief/part1.json media/lunch-thief-part1.mp4

See PIPELINE.md for the nightly routine and STORY_FORMAT.md for how scripts are written.
