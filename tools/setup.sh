#!/bin/bash
# Tesla-wraps: fonts, PNG tools and Python packages for tools/build.py (wrap generator).
# Never fails hard: a missing tool only matters when rebuilding wraps. Debian/Ubuntu, run as root.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq || echo "setup: apt-get update failed, using cached lists"
apt-get install -y -qq --no-install-recommends pngquant optipng \
  fonts-montserrat fonts-bebas-neue fonts-jura fonts-liberation fonts-inter fonts-dejavu-core \
  || echo "setup: apt packages were not installed"
fc-cache -f || true
python3 -m pip install --quiet --root-user-action=ignore numpy pillow scipy \
  || echo "setup: python packages were not installed"
exit 0
