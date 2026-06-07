#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request


DEFAULT_B_SID = "2e205885-1e58-4589-8bb8-deed47aa3d85"


def main() -> None:
    b_sid = os.environ.get("DAYTONA_B_SID", DEFAULT_B_SID).strip()
    b_key = os.environ.get("DAYTONA_B_KEY", "").strip()
    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    aes_key = os.environ.get("NEWAPI_BACKUP_AES_KEY_HEX", "").strip()
    if not b_sid:
        raise SystemExit("DAYTONA_B_SID is required")
    if not b_key:
        raise SystemExit("DAYTONA_B_KEY is required")
    if not github_token:
        raise SystemExit("GITHUB_TOKEN is required")
    if not aes_key:
        raise SystemExit("NEWAPI_BACKUP_AES_KEY_HEX is required")

    remote_py = f"""
import json
import urllib.request

headers = {{
    "Authorization": "Bearer {github_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "newapi-backup-b-restore",
}}
req = urllib.request.Request(
    "https://api.github.com/repos/baiqigo/NEW-API/releases/tags/newapi-backup-latest",
    headers=headers,
)
with urllib.request.urlopen(req, timeout=120) as resp:
    release = json.loads(resp.read().decode("utf-8"))
for asset in release["assets"]:
    name = asset["name"]
    req = urllib.request.Request(asset["browser_download_url"], headers=headers)
    with urllib.request.urlopen(req, timeout=300) as resp:
        open(name, "wb").write(resp.read())
"""
    remote_script = f"""
set -e
rm -rf /tmp/newapi-backup-release
mkdir -p /tmp/newapi-backup-release /home/daytona/backups/newapi
cd /tmp/newapi-backup-release
python3 - <<'PY'
{remote_py}
PY
BACKUP="$(sed -n 's/^backup=//p' LATEST.txt)"
ENC="$(sed -n 's/^encrypted=//p' LATEST.txt)"
NEWAPI_BACKUP_AES_KEY_HEX="{aes_key}" python3 decrypt_newapi_backup.py "$ENC" "/home/daytona/backups/newapi/$BACKUP"
cp "$BACKUP.sha256" "/home/daytona/backups/newapi/$BACKUP.sha256"
cd /home/daytona/backups/newapi
sha256sum -c "$BACKUP.sha256"
rm -rf /tmp/newapi-backup-release
"""
    command = "bash -lc " + json.dumps(remote_script)
    url = f"https://proxy.app-eu.daytona.io/toolbox/{b_sid}/process/execute"
    req = urllib.request.Request(
        url,
        data=json.dumps({"command": command}).encode("utf-8"),
        headers={"Authorization": f"Bearer {b_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        obj = json.loads(resp.read().decode("utf-8"))
    print(obj.get("result", ""))
    if obj.get("exitCode") != 0:
        raise SystemExit(obj)


if __name__ == "__main__":
    main()
