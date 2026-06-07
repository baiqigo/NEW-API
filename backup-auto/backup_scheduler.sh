#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${NEWAPI_BACKUP_AUTO_HOME:-/home/daytona/newapi_backup_auto}"
INTERVAL_SECONDS="${NEWAPI_BACKUP_INTERVAL_SECONDS:-43200}"
cd "$BASE"
echo $$ > "$BASE/scheduler.pid"

while true; do
  if mkdir "$BASE/run.lock" 2>/dev/null; then
    trap 'rmdir "$BASE/run.lock" 2>/dev/null || true' EXIT
    "$BASE/backup_once.sh" || true
    rmdir "$BASE/run.lock" 2>/dev/null || true
    trap - EXIT
  else
    echo "[$(date -u +%FT%TZ)] previous run still active" >> "$BASE/scheduler.out"
  fi
  sleep "$INTERVAL_SECONDS"
done
