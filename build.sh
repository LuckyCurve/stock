#!/usr/bin/env bash
# build.sh — Generate munger-dashboard.html from roic_cache/ YAML data
# Usage: bash build.sh
# Output: ./munger-dashboard.html
# Requires: Python 3 (stdlib only), curl or wget (for ECharts download)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE_DIR="$SCRIPT_DIR/roic_cache"
OUTPUT="$SCRIPT_DIR/munger-dashboard.html"
ECHARTS_CACHE="$SCRIPT_DIR/.cache/echarts.min.js"
ECHARTS_URL="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"

# Detect Python
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3 not found" >&2
    exit 1
fi

# Check cache dir
if [ ! -d "$CACHE_DIR" ]; then
    echo "ERROR: $CACHE_DIR not found" >&2
    exit 1
fi

yaml_count=$(find "$CACHE_DIR" -name "*.yaml" | wc -l | tr -d ' ')
echo "Found $yaml_count YAML files in $CACHE_DIR"

# Step 1: Download ECharts (cached)
echo "Preparing ECharts..."
mkdir -p "$(dirname "$ECHARTS_CACHE")"
if [ ! -s "$ECHARTS_CACHE" ]; then
    echo "Downloading ECharts from CDN..."
    if command -v curl &>/dev/null; then
        curl -sL "$ECHARTS_URL" -o "$ECHARTS_CACHE" 2>/dev/null || true
    elif command -v wget &>/dev/null; then
        wget -q "$ECHARTS_URL" -O "$ECHARTS_CACHE" 2>/dev/null || true
    fi
    if [ ! -s "$ECHARTS_CACHE" ]; then
        echo "WARNING: ECharts download failed, will use CDN fallback" >&2
        rm -f "$ECHARTS_CACHE"
    fi
fi

if [ -s "$ECHARTS_CACHE" ]; then
    ECHARTS_SIZE=$(wc -c < "$ECHARTS_CACHE" | tr -d ' ')
    echo "ECharts embedded inline ($ECHARTS_SIZE bytes)"
else
    echo "ECharts via CDN (download failed)"
fi

# Step 2: Run the Python build script (src/build.py), passing script_dir as argument
echo "Parsing, computing, and assembling HTML..."
$PYTHON "$SCRIPT_DIR/src/build.py" "$SCRIPT_DIR"
