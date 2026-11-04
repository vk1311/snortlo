#!/usr/bin/env bash
# One-time setup: Python packages + open-source voice model (~350 MB).
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || (sudo apt-get update && sudo apt-get install -y ffmpeg libcairo2 fonts-inter)
pip install --break-system-packages -q -r requirements.txt 2>/dev/null || pip install -q -r requirements.txt
# Kaggle CLI for the Qwen3 house voices (token: ~/.kaggle/access_token, written by the nightly task from Drive)
pip install --break-system-packages -q kaggle 2>/dev/null || pip install -q kaggle
mkdir -p models
# Download to a .part file and rename only when complete (Nov 4: a reset connection left a
# truncated model that the old "[ -f ]" check would have kept forever). Retries 3 times.
fetch() {  # fetch <dest> <url>
  [ -f "$1" ] && return 0
  for i in 1 2 3; do
    curl -sSL --retry 3 -C - -o "$1.part" "$2" && mv "$1.part" "$1" && return 0
    sleep 5
  done
  echo "download failed: $2" >&2; return 1
}
fetch models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
fetch models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
echo "setup done"
