#!/usr/bin/env bash
set -Eeuo pipefail

TARGET="${NEWAPI_BACKUP_AUTO_HOME:-/home/daytona/newapi_backup_auto}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$TARGET/logs"
cp "$SOURCE/upload_release_backup.py" "$TARGET/upload_release_backup.py"
cp "$SOURCE/trigger_b_restore.py" "$TARGET/trigger_b_restore.py"
cp "$SOURCE/backup_once.sh" "$TARGET/backup_once.sh"
cp "$SOURCE/backup_scheduler.sh" "$TARGET/backup_scheduler.sh"
chmod 700 "$TARGET" "$TARGET"/*.py "$TARGET"/*.sh

if [[ ! -f "$TARGET/secrets.env" ]]; then
  cat > "$TARGET/secrets.env" <<'EOF'
# Required.
GITHUB_TOKEN=''
NEWAPI_BACKUP_AES_KEY_HEX=''

# Optional. Add this to let the scheduler trigger backup-only Daytona B.
DAYTONA_B_SID='2e205885-1e58-4589-8bb8-deed47aa3d85'
DAYTONA_B_KEY=''

# Optional tuning.
NEWAPI_BACKUP_INTERVAL_SECONDS='43200'
NEWAPI_BACKUP_KEEP_COUNT='8'
EOF
  chmod 600 "$TARGET/secrets.env"
fi

python3 -m py_compile "$TARGET/upload_release_backup.py" "$TARGET/trigger_b_restore.py"

case "${1:-}" in
  --start)
    if [[ -f "$TARGET/scheduler.pid" ]] && kill -0 "$(cat "$TARGET/scheduler.pid")" 2>/dev/null; then
      kill "$(cat "$TARGET/scheduler.pid")" || true
      sleep 2
    fi
    nohup "$TARGET/backup_scheduler.sh" > "$TARGET/scheduler.out" 2>&1 &
    echo $! > "$TARGET/scheduler.pid"
    echo "started scheduler pid=$(cat "$TARGET/scheduler.pid")"
    ;;
  --once)
    "$TARGET/backup_once.sh"
    ;;
  *)
    echo "installed to $TARGET"
    echo "edit $TARGET/secrets.env, then run: $TARGET/backup_once.sh or $TARGET/backup_scheduler.sh"
    ;;
esac
