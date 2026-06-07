#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import urllib.request


DEFAULT_OWNER = "baiqigo"
DEFAULT_REPO = "NEW-API"
DEFAULT_TAG = "newapi-backup-latest"
DEFAULT_REMOTE_DIR = "/home/daytona/backups/newapi"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN", "").strip()
    aes_key = os.environ.get("NEWAPI_BACKUP_AES_KEY_HEX", "").strip()
    if not github_token:
        raise SystemExit("GITHUB_TOKEN is required")
    if not aes_key:
        raise SystemExit("NEWAPI_BACKUP_AES_KEY_HEX is required")

    work = pathlib.Path("/tmp/newapi-backup-release")
    remote_dir = pathlib.Path(args.remote_dir)
    if work.exists():
        for child in work.iterdir():
            child.unlink()
    else:
        work.mkdir(parents=True)
    remote_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "newapi-backup-b-puller",
    }
    api = f"https://api.github.com/repos/{args.owner}/{args.repo}/releases/tags/{args.tag}"
    req = urllib.request.Request(api, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        release = json.loads(resp.read().decode("utf-8"))

    for asset in release["assets"]:
        name = asset["name"]
        req = urllib.request.Request(asset["browser_download_url"], headers=headers)
        with urllib.request.urlopen(req, timeout=300) as resp:
            (work / name).write_bytes(resp.read())

    latest = {}
    for line in (work / "LATEST.txt").read_text(encoding="ascii").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            latest[k] = v
    backup = latest["backup"]
    encrypted = latest["encrypted"]

    decrypt_script = work / "decrypt_newapi_backup.py"
    output = remote_dir / backup
    env = os.environ.copy()
    env["NEWAPI_BACKUP_AES_KEY_HEX"] = aes_key

    import subprocess

    subprocess.run(
        ["python3", str(decrypt_script), str(work / encrypted), str(output)],
        check=True,
        env=env,
    )
    sha_file = work / f"{backup}.sha256"
    target_sha = remote_dir / sha_file.name
    target_sha.write_bytes(sha_file.read_bytes())
    subprocess.run(["sha256sum", "-c", target_sha.name], cwd=remote_dir, check=True)
    print(f"restored={output}")


if __name__ == "__main__":
    main()
