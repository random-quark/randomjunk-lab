# Future installation — not performed during source review

## Information needed from the owner

Choose a domain, configure wildcard A/AAAA records for the server's reachable
addresses, and confirm SSH access/port before enabling a firewall. Remove stale
AAAA records if IPv6 is unavailable. Decide which apps are private, which provider
keys may be granted, and whether remote backup/notification accounts are ready.
No domain or real credentials are needed for source tests.

The installer expects a fresh Ubuntu 24.04 machine. Existing lab paths/accounts
or Caddy configuration trigger refusal; use [migration.md](docs/migration.md).
It installs apt packages, creates lab, writes sudoers/configuration, enables the
web/database services, and enables a firewall allowing OpenSSH/80/443. Review
those effects and obtain installation authorization first. A custom SSH port
needs an explicit reviewed adjustment before running it.

## Install after approval

Copy/clone the reviewed repository including lockfiles to the new server.
Run source tests first as described in [development.md](docs/development.md).
Then, only in the installation phase:

```sh
sudo bash bootstrap.sh --install-fresh experiments.example.com
```

uv is pinned to 0.8.22. Ubuntu/PostgreSQL/Caddy packages track apt repositories;
exact installed versions are captured in `/var/lib/lab/install-versions.txt`.
Apt's future repository contents are not reproducible solely from this repo;
use an OS image/repository snapshot if byte-for-byte rebuilding is required.
The installer is intentionally not idempotent: failure leaves a machine for
inspection, not a safe invitation to rerun it blindly.

## Configure without exposing values

Root edits `/etc/lab/secrets.env` and `/etc/lab/backup.env` (0600). These use
literal, single-line `KEY=value`: no shell expansion or quote decoding. Values
must not contain newline/NUL. Do not source these files. The helper writes a
separately quoted systemd EnvironmentFile; the runtime does not open it itself.

`/etc/lab/notify.env` is root:lab 0640. A private ntfy topic/endpoint is a secret
and must not be world-readable. Notification sending is optional and explicit.

Caddy's admin Unix socket lives under a 0700 **caddy-owned** runtime directory;
root and Caddy can access it, deployment and runtime users cannot. Check actual
ownership/socket access during integration. It is not described as root-only.
Certificates are requested when sites are published. Use a dedicated disposable
integration environment with ACME staging or local test TLS for repeated tests;
never repeatedly exercise creation against production ACME during debugging.
The committed production config has no on-demand TLS.

## Operate as lab

Root handles installation; `sudo -iu lab` enters the deployment account.
Copy the repository's CLAUDE.md/AGENTS operating guidance to the agent's configured
instructions deliberately, or keep the repository available read-only. Do not
run the everyday experiment agent as root. The controller runs fixed scaffolding
and static export workers as lab; systemd runs each app as labapp-NAME.

Create one disposable app at a time, test, and remove it. Run the matrix in
[verification.md](docs/verification.md). Record outcomes, versions and leftovers.
Use `/srv/lab/NAME/app` for source, not the root-owned container itself.

## Backups

Set B2_ENDPOINT, B2_BUCKET, B2_KEY_ID, B2_APP_KEY and RESTIC_PASSWORD in backup.env.
Keep an independent copy of the restic password and access credentials outside
this server. `/etc/lab` is included in encrypted backups, but a password trapped
inside its own encrypted backup cannot recover that backup.

Use root's protected configuration to initialize the repository (Python parses
values without printing or sourcing them):

```sh
sudo /usr/bin/python3 -I - <<'PY'
import subprocess, sys
sys.path.insert(0, '/usr/local/lib/lab')
from backup import backup_environment
from labcore import read_env
subprocess.run(['restic', 'init'], env=backup_environment(read_env('/etc/lab/backup.env')), check=True)
PY
```

Run `sudo systemctl start lab-backup.service` once and inspect its result. Complete
a staged restore drill per [recovery.md](docs/recovery.md). Only then enable:

```sh
sudo systemctl enable --now lab-backup.timer
```

The installer leaves the backup timer disabled. Backups hold the lifecycle lock
and may delay create/remove/publish. App writes may continue: each SQLite backup
is consistent individually, and each Postgres dump is a database snapshot; this
is not one atomic snapshot spanning every app and filesystem. Quiesce apps for
cross-resource consistency if their application semantics require it.

Backup failure notifications use systemd OnFailure, covering ordinary failure,
timeout and killed/OOM processes while the manager remains running. Direct manual
execution uses the script's exception notifier instead. Delivery itself depends
on network/provider availability; host power loss cannot send its own alert.
