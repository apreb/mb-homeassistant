#!/usr/bin/env bash
# Deploy custom_components/apr_evse to the Home Assistant host and restart HA.
#
#   ./scripts/deploy.sh            # deploy + restart
#   ./scripts/deploy.sh --no-restart
#   HA_HOST=other ./scripts/deploy.sh
set -euo pipefail

HOST="${HA_HOST:-ha}"
TARGET="${HA_TARGET:-/root/homeassistant/custom_components}"
COMPONENT="apr_evse"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/custom_components/$COMPONENT"

RESTART=1
[ "${1:-}" = "--no-restart" ] && RESTART=0

[ -f "$SRC/manifest.json" ] || { echo "no manifest.json in $SRC" >&2; exit 1; }

echo "removing $HOST:$TARGET/$COMPONENT"
ssh "$HOST" "rm -rf '$TARGET/$COMPONENT'"

# tar over ssh instead of scp so __pycache__ never lands on the host
echo "uploading $SRC"
tar -czf - -C "$(dirname "$SRC")" --exclude='__pycache__' "$COMPONENT" \
  | ssh "$HOST" "mkdir -p '$TARGET' && tar -xzf - -C '$TARGET'"

ssh "$HOST" "ls '$TARGET/$COMPONENT/manifest.json' >/dev/null" \
  || { echo "upload failed" >&2; exit 1; }

if [ "$RESTART" = 1 ]; then
  echo "restarting Home Assistant (takes ~30s)"
  ssh "$HOST" "ha core restart"
fi

echo "done"
