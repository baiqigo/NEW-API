#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${NEWAPI_BACKUP_AUTO_HOME:-/home/daytona/newapi_backup_auto}"
REMOTE_BACKUP_DIR="${NEWAPI_REMOTE_BACKUP_DIR:-/home/daytona/backups/newapi}"
NEWAPI_BACKUP_SCRIPT="${NEWAPI_BACKUP_SCRIPT:-/home/daytona/newapi/backup.sh}"
LOG_DIR="$BASE/logs"
KEEP_COUNT="${NEWAPI_BACKUP_KEEP_COUNT:-8}"

mkdir -p "$LOG_DIR" "$REMOTE_BACKUP_DIR"
LOG="$LOG_DIR/backup-$(date -u +%Y%m%d_%H%M%S).log"
exec >>"$LOG" 2>&1
cd "$BASE"

echo "[$(date -u +%FT%TZ)] backup_once start"

if [[ ! -f "$BASE/secrets.env" ]]; then
  echo "missing $BASE/secrets.env"
  exit 1
fi

set -a
source "$BASE/secrets.env"
set +a

python3 - <<'PY'
import cryptography
print("cryptography-ok")
PY

chmod +x "$NEWAPI_BACKUP_SCRIPT"
"$NEWAPI_BACKUP_SCRIPT"

LATEST="$(ls -1t "$REMOTE_BACKUP_DIR"/full-backup-*.tar.gz | head -1)"
SHA="$(sha256sum "$LATEST" | awk '{print $1}')"
SIZE="$(stat -c %s "$LATEST")"
echo "latest=$LATEST size=$SIZE sha256=$SHA"

python3 "$BASE/upload_release_backup.py" --backup-file "$LATEST"

find "$REMOTE_BACKUP_DIR" -maxdepth 1 -name 'full-backup-*.tar.gz' -type f -printf '%T@ %p\n' |
  sort -nr | awk -v keep="$KEEP_COUNT" 'NR > keep {print $2}' | xargs -r rm -f
find "$REMOTE_BACKUP_DIR" -maxdepth 1 -name 'full-backup-*.tar.gz.sha256' -type f -printf '%T@ %p\n' |
  sort -nr | awk -v keep="$KEEP_COUNT" 'NR > keep {print $2}' | xargs -r rm -f

if [[ -n "${DAYTONA_B_KEY:-}" ]]; then
  echo "DAYTONA_B_KEY present, triggering B restore"
  python3 "$BASE/trigger_b_restore.py"
else
  echo "DAYTONA_B_KEY not configured; B restore skipped"
fi

echo "[$(date -u +%FT%TZ)] backup_once done"
