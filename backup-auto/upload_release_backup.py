#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


DEFAULT_OWNER = "baiqigo"
DEFAULT_REPO = "NEW-API"
DEFAULT_TAG = "newapi-backup-latest"

DECRYPT_SCRIPT = """#!/usr/bin/env python3
import hashlib
import os
import pathlib
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if len(sys.argv) != 3:
    raise SystemExit("usage: decrypt_newapi_backup.py <encrypted-file> <output-file>")
key_hex = os.environ.get("NEWAPI_BACKUP_AES_KEY_HEX", "").strip()
if not key_hex:
    raise SystemExit("NEWAPI_BACKUP_AES_KEY_HEX is required")
blob = pathlib.Path(sys.argv[1]).read_bytes()
plain = AESGCM(bytes.fromhex(key_hex)).decrypt(blob[:12], blob[12:], None)
out = pathlib.Path(sys.argv[2])
out.write_bytes(plain)
print("wrote", out)
print("sha256", hashlib.sha256(plain).hexdigest())
"""


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class GitHub:
    def __init__(self, token: str, owner: str, repo: str) -> None:
        self.owner = owner
        self.repo = repo
        self.base = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "newapi-sandbox-backup-scheduler",
        }

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, object]:
        data = None
        headers = dict(self.headers)
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                text = resp.read().decode("utf-8")
                return resp.status, json.loads(text) if text else {}
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            try:
                obj = json.loads(text)
            except Exception:
                obj = {"message": text}
            return exc.code, obj

    def get_release(self, tag: str) -> dict | None:
        status, obj = self.request("GET", f"/repos/{self.owner}/{self.repo}/releases/tags/{tag}")
        if status == 200 and isinstance(obj, dict):
            return obj
        if status == 404:
            return None
        raise SystemExit(f"get release failed: {status} {obj}")

    def create_release(self, tag: str) -> dict:
        body = {
            "tag_name": tag,
            "name": tag,
            "body": "Encrypted New API backup transport. Do not upload plaintext backups or AES keys.",
            "draft": False,
            "prerelease": True,
        }
        status, obj = self.request("POST", f"/repos/{self.owner}/{self.repo}/releases", body)
        if status != 201 or not isinstance(obj, dict):
            raise SystemExit(f"create release failed: {status} {obj}")
        return obj

    def delete_backup_assets(self, release: dict) -> None:
        for asset in release.get("assets", []) or []:
            name = asset.get("name", "")
            if name.endswith(".aesgcm") or name.endswith(".sha256") or name in {"LATEST.txt", "decrypt_newapi_backup.py"}:
                status, obj = self.request("DELETE", f"/repos/{self.owner}/{self.repo}/releases/assets/{asset['id']}")
                if status != 204:
                    raise SystemExit(f"delete asset {name} failed: {status} {obj}")

    def upload_asset(self, release: dict, name: str, data: bytes, content_type: str) -> None:
        upload_url = release["upload_url"].split("{", 1)[0]
        url = upload_url + "?" + urllib.parse.urlencode({"name": name})
        headers = dict(self.headers)
        headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                if resp.status != 201:
                    raise SystemExit(f"upload {name} failed: {resp.status}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SystemExit(f"upload {name} failed: {exc.code} {body}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-file", required=True, type=pathlib.Path)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    key_hex = os.environ.get("NEWAPI_BACKUP_AES_KEY_HEX", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    if not key_hex:
        raise SystemExit("NEWAPI_BACKUP_AES_KEY_HEX is required")

    backup = args.backup_file.resolve()
    expected_sha = sha256_file(backup)
    key = bytes.fromhex(key_hex)
    nonce = secrets.token_bytes(12)
    encrypted = nonce + AESGCM(key).encrypt(nonce, backup.read_bytes(), None)
    enc_name = backup.name + ".aesgcm"
    sha_name = backup.name + ".sha256"
    latest = (
        f"backup={backup.name}\n"
        f"encrypted={enc_name}\n"
        f"sha256={expected_sha}\n"
        f"updated_at={time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
    ).encode("ascii")

    gh = GitHub(token, args.owner, args.repo)
    release = gh.get_release(args.tag) or gh.create_release(args.tag)
    gh.delete_backup_assets(release)
    release = gh.get_release(args.tag) or release
    gh.upload_asset(release, enc_name, encrypted, "application/octet-stream")
    release = gh.get_release(args.tag) or release
    gh.upload_asset(release, sha_name, f"{expected_sha}  {backup.name}\n".encode("ascii"), "text/plain")
    release = gh.get_release(args.tag) or release
    gh.upload_asset(release, "LATEST.txt", latest, "text/plain")
    release = gh.get_release(args.tag) or release
    gh.upload_asset(release, "decrypt_newapi_backup.py", DECRYPT_SCRIPT.encode("utf-8"), "text/x-python")

    print(f"release={args.tag}")
    print(f"asset={enc_name}")
    print(f"sha256={expected_sha}")


if __name__ == "__main__":
    main()
