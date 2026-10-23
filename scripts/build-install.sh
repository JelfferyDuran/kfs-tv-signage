#!/usr/bin/env bash
# build-install.sh — package + install the KFS Kitchen Display app on the TVs.
# Run AFTER: Tizen Studio installed, Developer Mode enabled on each TV,
#           certificate profile created (see README Path B).
#
# Usage:
#   ./build-install.sh [tv_ip ...]     # default: all 3 TVs
#   ./build-install.sh 10.1.10.46      # just menu1
set -euo pipefail

TIZEN_BIN="${TIZEN_BIN:-/c/tizen-studio/tools/ide/bin/tizen}"
SDB_BIN="${SDB_BIN:-/c/tizen-studio/tools/sdb}"
APP_DIR="$(cd "$(dirname "$0")/../tizen-app" && pwd)"
OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/build"
PROFILE="${PROFILE:-KFS}"
TVS=("${@:-10.1.10.46 10.1.10.91 10.1.10.185}")

mkdir -p "$OUT_DIR"

echo "==> Building wgt (profile: $PROFILE)"
"$TIZEN_BIN" build-web -e "$APP_DIR" -o "$OUT_DIR" 2>/dev/null || \
  "$TIZEN_BIN" build -e "$APP_DIR" -o "$OUT_DIR"
"$TIZEN_BIN" package -t wgt -s "$PROFILE" -o "$OUT_DIR" -- "$OUT_DIR"

WGT=$(ls "$OUT_DIR"/*.wgt | head -1)
echo "==> Package: $WGT"

for tv in "${TVS[@]}"; do
  echo "==> Connecting $tv"
  "$SDB_BIN" connect "$tv"
  echo "==> Installing on $tv"
  "$SDB_BIN" -s "$tv:26101" install "$WGT"
  echo "==> Launching on $tv"
  "$SDB_BIN" -s "$tv:26101" shell 0 launch KFSKitchenDisplay
done

echo "DONE. TVs should now show the KFS display app."
