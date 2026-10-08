#!/usr/bin/env bash
# Usage: engine/make_video.sh stories/<series>/partN.json media/<series>-partN.mp4
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STORY="$ROOT/$1"; OUT="$ROOT/$2"
cd "$ROOT/engine"
python3 voice2.py "$STORY"
python3 anim_render.py "$STORY" "$OUT"
