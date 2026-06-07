# New API Backup Automation

This directory contains public scripts only. Do not commit `GITHUB_TOKEN`,
`NEWAPI_BACKUP_AES_KEY_HEX`, `DAYTONA_B_KEY`, plaintext backups, or decrypted
databases.

## Install on the main Daytona sandbox

```bash
cd /home/daytona/NEW-API
git pull
bash backup-auto/install.sh
vi /home/daytona/newapi_backup_auto/secrets.env
bash backup-auto/install.sh --start
```

The scheduler runs immediately, then every 12 hours by default.

Logs:

```bash
tail -f /home/daytona/newapi_backup_auto/scheduler.out
ls -lt /home/daytona/newapi_backup_auto/logs/
```

Stop:

```bash
kill "$(cat /home/daytona/newapi_backup_auto/scheduler.pid)"
```

## Read-only production probe

Run this manually or from an external scheduler. It does not restart services,
delete files, create backups, or mutate SQLite state.

```bash
cd /home/daytona/NEW-API
git pull
python3 backup-auto/prod_probe.py
```

The probe checks local New API status, public Worker health, Docker container
state, disk free space, SQLite integrity, and latest full-backup age. It prints
JSON and exits `0` only when all hard checks pass. Because Daytona egress can
reset requests back to the public Cloudflare hostname, public Worker health is a
warning by default inside the sandbox; set `NEWAPI_PUBLIC_HEALTH_REQUIRED=true`
when running the probe from an external network that should reach the public
hostname directly.

## Install on backup-only Daytona B

```bash
cd /home/daytona/NEW-API
git pull
bash backup-auto/install_b.sh
vi /home/daytona/newapi_backup_auto/secrets.env
bash backup-auto/install_b.sh --start
```

B pulls the latest encrypted GitHub Release asset, decrypts it locally, and
verifies the `.sha256` file.
