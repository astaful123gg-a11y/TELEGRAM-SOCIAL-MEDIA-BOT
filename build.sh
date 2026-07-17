#!/usr/bin/env bash
# Render build script — installs ffmpeg (needed for the TikTok/Instagram/
# Pinterest "Audio" button, which extracts audio locally since those APIs
# only return video/image).
set -e

echo "==> Installing system packages..."
apt-get update -qq
apt-get install -y -qq ffmpeg

echo "==> Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Build complete."
