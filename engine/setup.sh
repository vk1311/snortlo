#!/usr/bin/env bash
# One-time setup: Python packages + open-source voice model (~350 MB).
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || (sudo apt-get update && sudo apt-get install -y ffmpeg libcairo2 fonts-inter)
pip install --break-system-packages -q -r requirements.txt 2>/dev/null || pip install -q -r requirements.txt
mkdir -p models
[ -f models/kokoro-v1.0.onnx ] || curl -sSL -o models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -f models/voices-v1.0.bin ] || curl -sSL -o models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
echo "setup done"
