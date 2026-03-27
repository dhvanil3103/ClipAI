#!/usr/bin/env bash
set -o errexit

echo "Installing system dependencies..."
apt-get update && apt-get install -y ffmpeg

echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "Build complete!"