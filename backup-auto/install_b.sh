#!/usr/bin/env bash
set -Eeuo pipefail

TARGET="${NEWAPI_BACKUP_AUTO_HOME:-/home/daytona/newapi_backup_auto}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$TARGET/logs"
cp "$SOURCE/pull_release_backup.py" "$TARGET/pull_release_backup.py"
cp "$SOURCE/pull_once.sh" "$TARGET/pull_once.sh"
cp "$SOURCE/pull_scheduler.sh" "$TARGET/pull_scheduler.sh"
chmod 700 "$TARGET" "$TARGET"/*.py "$TARGET"/*.sh

if [[ ! -f "$TARGET/secrets.env" ]]; then
  cat > "$TARGET/secrets.env" <<'EOF'
GITHUB_TOKEN=''
NEWAPI_BACKUP_AES_KEY_HEX=''
NEWAPI_BACKUP_PULL_INTERVAL_SECONDS='43200'
NEWAPI_BACKUP_KEEP_COUNT='8'
EOF
  chmod 600 "$TARGET/secrets.env"
fi

python3 -m py_compile "$TARGET/pull_release_backup.py"

case "${1:-}" in
  --start)
    if [[ -f "$TARGET/pull_scheduler.pid" ]] && kill -0 "$(cat "$TARGET/pull_scheduler.pid")" 2>/dev/null; then
      kill "$(cat "$TARGET/pull_scheduler.pid")" || true
      sleep 2
    fi
    nohup "$TARGET/pull_scheduler.sh" > "$TARGET/pull_scheduler.out" 2>&1 &
    echo $! > "$TARGET/pull_scheduler.pid"
    echo "started pull scheduler pid=$(cat "$TARGET/pull_scheduler.pid")"
    ;;
  --once)
    "$TARGET/pull_once.sh"
    ;;
  *)
    echo "installed B puller to $TARGET"
    ;;
esac
