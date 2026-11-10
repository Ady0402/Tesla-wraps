#!/bin/bash
# Toolchain for tools/build.py (the wrap PNG generator). Debian/Ubuntu, run as root.
# Safe to re-run. Never fails hard: a missing tool only matters when rebuilding wraps.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq || echo "setup: apt-get update failed, using cached package lists"
apt-get install -y -qq --no-install-recommends pngquant optipng \
  fonts-montserrat fonts-bebas-neue fonts-play fonts-liberation fonts-inter fonts-dejavu-core \
  || echo "setup: apt packages were not installed"
fc-cache -f || true
python3 -m pip install --quiet --root-user-action=ignore numpy pillow scipy \
  || echo "setup: python packages were not installed"
exit 0
