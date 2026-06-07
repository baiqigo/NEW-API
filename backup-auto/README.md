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
