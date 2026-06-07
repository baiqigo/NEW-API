#!/usr/bin/env python3
"""Read-only production probe for the New API Daytona sandbox.

The probe is intentionally side-effect free: it does not restart services,
delete files, create backups, or mutate SQLite state. It prints a JSON report
and exits non-zero if any hard check fails.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


LOCAL_STATUS_URL = os.environ.get("NEWAPI_LOCAL_STATUS_URL", "http://127.0.0.1:3000/api/status")
PUBLIC_HEALTH_URL = os.environ.get("NEWAPI_PUBLIC_HEALTH_URL", "https://newapi.baiqi.xyz/__newapi_gateway_health")
DB_PATH = Path(os.environ.get("NEWAPI_DB_PATH", "/home/daytona/newapi/data/one-api.db"))
BACKUP_DIR = Path(os.environ.get("NEWAPI_BACKUP_DIR", "/home/daytona/backups/newapi"))
MAX_BACKUP_AGE_HOURS = float(os.environ.get("NEWAPI_MAX_BACKUP_AGE_HOURS", "13"))
MIN_FREE_BYTES = int(os.environ.get("NEWAPI_MIN_FREE_BYTES", str(1024 * 1024 * 1024)))


def http_json(url: str, timeout: int = 20) -> tuple[bool, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(1024 * 1024).decode("utf-8", "replace")
        return 200 <= resp.status < 300, json.loads(body)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, str(exc)


def run(args: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output


def docker_container(name: str) -> dict[str, Any]:
    ok, output = run(["docker", "inspect", name, "--format", "{{.State.Status}}|{{.Config.Image}}"])
    if not ok:
        return {"ok": False, "error": output}
    status, _, image = output.partition("|")
    return {"ok": status == "running", "status": status, "image": image}


def sqlite_integrity(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "error": f"missing db: {path}"}
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": result == "ok", "result": result}


def backup_age(directory: Path) -> dict[str, Any]:
    backups = sorted(directory.glob("full-backup-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        return {"ok": False, "error": f"no full-backup-*.tar.gz in {directory}"}
    latest = backups[0]
    age_hours = (time.time() - latest.stat().st_mtime) / 3600
    sha_file = latest.with_suffix(latest.suffix + ".sha256")
    return {
        "ok": age_hours <= MAX_BACKUP_AGE_HOURS and sha_file.exists(),
        "path": str(latest),
        "age_hours": round(age_hours, 2),
        "sha256_file": str(sha_file),
        "sha256_exists": sha_file.exists(),
    }


def disk_free(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "ok": usage.free >= MIN_FREE_BYTES,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "min_free_bytes": MIN_FREE_BYTES,
    }


def main() -> int:
    local_ok, local_status = http_json(LOCAL_STATUS_URL)
    public_ok, public_health = http_json(PUBLIC_HEALTH_URL)
    checks: dict[str, Any] = {
        "local_status": {"ok": local_ok, "result": local_status},
        "public_worker_health": {"ok": public_ok, "result": public_health},
        "new_api_container": docker_container("new-api-public"),
        "grok2api_container": docker_container("grok2api"),
        "disk_free": disk_free(Path("/")),
        "sqlite_integrity": sqlite_integrity(DB_PATH),
        "latest_backup": backup_age(BACKUP_DIR),
    }

    hard_ok = all(item.get("ok") for item in checks.values() if isinstance(item, dict))
    report = {"ok": hard_ok, "checked_at": int(time.time()), "checks": checks}
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if hard_ok else 2


if __name__ == "__main__":
    sys.exit(main())
