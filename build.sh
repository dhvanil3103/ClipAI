#!/usr/bin/env bash
set -o errexit

echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "Setting up ffmpeg..."

# Try apt-get first (works on most Render environments)
if command -v apt-get &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq ffmpeg
    echo "ffmpeg installed via apt-get"

# Try sudo apt-get
elif sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg; then
    echo "ffmpeg installed via sudo apt-get"

# Fall back to static binary via curl
else
    echo "apt-get unavailable, downloading static ffmpeg binary..."
    curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
        -o /tmp/ffmpeg.tar.xz
    tar -xf /tmp/ffmpeg.tar.xz -C /tmp
    mkdir -p bin
    mv /tmp/ffmpeg-*-amd64-static/ffmpeg bin/
    mv /tmp/ffmpeg-*-amd64-static/ffprobe bin/
    rm -rf /tmp/ffmpeg* 
    echo "ffmpeg installed via static binary"
fi

echo "Verifying ffmpeg..."
ffmpeg -version | head -1 || echo "Warning: ffmpeg not on PATH yet"

echo "Build complete!"