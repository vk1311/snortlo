#!/usr/bin/env bash
# Shrink a long-form video under GitHub's 100 MB file limit (needed because Postiz pulls media from raw.githubusercontent.com).
# Usage: engine/shrink.sh media/long-x.mp4 media/long-x-web.mp4   (720p, 12 fps, CRF 30: ~1.1 MB per minute for calm scenes)
set -e
ffmpeg -v error -y -i "$1" -vf "scale=1280:720,fps=12" -c:v libx264 -preset slow -crf ${CRF:-30} -tune animation \
  -c:a aac -b:a 80k -ac 1 -movflags +faststart "$2"
SIZE=$(stat -c %s "$2"); echo "$2: $((SIZE/1048576)) MB"
[ "$SIZE" -lt 99000000 ] || { echo "still over 99 MB, retry with CRF=33"; exit 1; }
