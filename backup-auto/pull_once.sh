#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${NEWAPI_BACKUP_AUTO_HOME:-/home/daytona/newapi_backup_auto}"
LOG_DIR="$BASE/logs"
mkdir -p "$LOG_DIR" /home/daytona/backups/newapi
LOG="$LOG_DIR/pull-$(date -u +%Y%m%d_%H%M%S).log"
exec >>"$LOG" 2>&1
cd "$BASE"

echo "[$(date -u +%FT%TZ)] pull_once start"
set -a
source "$BASE/secrets.env"
set +a

python3 "$BASE/pull_release_backup.py"

find /home/daytona/backups/newapi -maxdepth 1 -name 'full-backup-*.tar.gz' -type f -printf '%T@ %p\n' |
  sort -nr | awk -v keep="${NEWAPI_BACKUP_KEEP_COUNT:-8}" 'NR > keep {print $2}' | xargs -r rm -f
find /home/daytona/backups/newapi -maxdepth 1 -name 'full-backup-*.tar.gz.sha256' -type f -printf '%T@ %p\n' |
  sort -nr | awk -v keep="${NEWAPI_BACKUP_KEEP_COUNT:-8}" 'NR > keep {print $2}' | xargs -r rm -f

echo "[$(date -u +%FT%TZ)] pull_once done"
