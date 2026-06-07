#!/usr/bin/env python3
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
key = bytes.fromhex(key_hex)
blob = pathlib.Path(sys.argv[1]).read_bytes()
nonce, ciphertext = blob[:12], blob[12:]
plain = AESGCM(key).decrypt(nonce, ciphertext, None)
out = pathlib.Path(sys.argv[2])
out.write_bytes(plain)
print("wrote", out)
print("sha256", hashlib.sha256(plain).hexdigest())
