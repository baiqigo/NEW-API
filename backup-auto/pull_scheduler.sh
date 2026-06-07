#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${NEWAPI_BACKUP_AUTO_HOME:-/home/daytona/newapi_backup_auto}"
INTERVAL_SECONDS="${NEWAPI_BACKUP_PULL_INTERVAL_SECONDS:-43200}"
cd "$BASE"
echo $$ > "$BASE/pull_scheduler.pid"

while true; do
  if mkdir "$BASE/pull.lock" 2>/dev/null; then
    trap 'rmdir "$BASE/pull.lock" 2>/dev/null || true' EXIT
    "$BASE/pull_once.sh" || true
    rmdir "$BASE/pull.lock" 2>/dev/null || true
    trap - EXIT
  else
    echo "[$(date -u +%FT%TZ)] previous pull still active" >> "$BASE/pull_scheduler.out"
  fi
  sleep "$INTERVAL_SECONDS"
done
