#!/usr/bin/env bash
# build-install.sh — package + install the KFS Kitchen Display app on the TVs.
# Run AFTER: Tizen Studio installed, Developer Mode enabled on each TV,
#           certificate profile created (see docs/DEVICES.md).
#
# Each TV gets its own build with its own TV_ID baked into app.js, so
# menu1/menu2/menu3 can show different scenes. (Previously one wgt with
# TV_ID="menu1" was installed everywhere, so all TVs polled as menu1.)
#
# Usage:
#   ./build-install.sh                       # all 3 TVs (default map below)
#   ./build-install.sh menu1=10.1.10.46      # just menu1
#   ./build-install.sh kitchen4=10.1.10.50   # any device id
set -euo pipefail

TIZEN_BIN="${TIZEN_BIN:-/c/tizen-studio/tools/ide/bin/tizen}"
SDB_BIN="${SDB_BIN:-/c/tizen-studio/tools/sdb}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$REPO_DIR/tizen-app"
OUT_ROOT="$REPO_DIR/tizen-app/build"
PROFILE="${PROFILE:-KFS}"
APP_ID="KFS0000001.KFSKitchenDisplay"

if [ "$#" -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=(menu1=10.1.10.46 menu2=10.1.10.91 menu3=10.1.10.185)
fi

for target in "${TARGETS[@]}"; do
  case "$target" in
    *=*) tv_id="${target%%=*}"; tv_ip="${target#*=}" ;;
    *) echo "bad target '$target' (expected id=ip, e.g. menu1=10.1.10.46)" >&2; exit 1 ;;
  esac

  src="$OUT_ROOT/src-$tv_id"
  out="$OUT_ROOT/$tv_id"
  mkdir -p "$src" "$out"
  cp "$APP_DIR"/config.xml "$APP_DIR"/index.html "$APP_DIR"/app.js "$src"/
  sed -i.bak "s/var TV_ID = \"[^\"]*\"/var TV_ID = \"$tv_id\"/" "$src/app.js" && rm -f "$src/app.js.bak"
  grep -q "var TV_ID = \"$tv_id\"" "$src/app.js" || { echo "failed to set TV_ID in app.js" >&2; exit 1; }

  echo "==> [$tv_id] Building wgt (profile: $PROFILE)"
  "$TIZEN_BIN" build-web -out "$out/.buildResult" -- "$src"
  "$TIZEN_BIN" package -t wgt -s "$PROFILE" -- "$out/.buildResult"
  WGT=$(ls "$out"/.buildResult/*.wgt | head -1)
  echo "==> [$tv_id] Package: $WGT"

  echo "==> [$tv_id] Connecting $tv_ip"
  "$SDB_BIN" connect "$tv_ip"
  echo "==> [$tv_id] Installing on $tv_ip"
  "$TIZEN_BIN" install -n "$WGT" -s "$tv_ip:26101"
  echo "==> [$tv_id] Launching on $tv_ip"
  "$TIZEN_BIN" run -p "$APP_ID" -s "$tv_ip:26101"
done

echo "DONE. TVs should now show the KFS display app."
