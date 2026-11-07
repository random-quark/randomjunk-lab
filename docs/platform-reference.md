# Platform reference for agents

Human setup starts in [README.md](../README.md). Installation agents must follow
[SETUP.md](../SETUP.md); platform contributors follow [AGENTS.md](../AGENTS.md).

## Installed layout

| Path | Ownership and purpose |
| --- | --- |
| `/srv/lab/NAME/` | root-owned container |
| `/srv/lab/NAME/app/` | lab-owned source and uv environment; edit here |
| `/srv/lab/NAME/data/` | runtime-owned 0700 persistent data |
| `/var/lib/lab/` | root-only records, credentials and lifecycle lock |
| `/var/lib/lab-public/NAME-REVISION/` | immutable root-owned static publication |
| `/etc/lab/apps/NAME.env` | root-only environment injected by systemd |

`newlab` and `labrm` call one privileged controller. The controller serializes
operations, runs code/dependency work as `lab`, and generates Caddy configuration
from structured records. Failed creation preserves resources for diagnosis;
failed service stop blocks destructive teardown.

After installation, typical commands **as lab** are:

```sh
newlab hello --static
newlab notes --app --db postgres --private
sudo /usr/local/sbin/labctl publish hello
sudo /usr/local/sbin/labctl verify notes
labs
labdev hello  # local preview; Ctrl-C cleans up
labshot hello --out /tmp/hello-preview
labdoctor
labrm hello
```

Shell edits in either app kind need `labctl publish NAME` to regenerate the worker.
Backend Python edits also need `labctl service restart NAME`. HTTP verification
is not application testing.

Read [SETUP.md](../SETUP.md), [security](security.md),
[recovery](recovery.md), [hosted notifications](notifications.md), [migration](migration.md), and
[agent operating instructions](../templates/operating-instructions.md) before installing or administering.

## Experiment development workflow

New static and backend scaffolds include an in-app PWA offer, content-hashed shell
worker generation, uv-locked test tooling, and tools/tests shared fixtures. Start a
local preview with labdev, publish an early safe preview, and share screenshots
with labshot. See [the workflow](experiment-workflow.md). Existing apps are
not rewritten: custom workers opt in only through an explicit migration.

## Server backups and monitoring

Historical example only: the original server has daily encrypted **Restic backups to Backblaze B2**, running at
**03:30 Europe/Berlin**. The whole-machine backup covers data and configuration,
with exclusions for replaceable OS files, caches, logs and selected secrets.
It includes PostgreSQL dumps and discovered SQLite snapshots; new database
engines or unusual storage locations still need a backup review.

Retention is **7 daily, 4 weekly and 6 monthly snapshots**. Each run checks 1% of
repository data. **Healthchecks.io** receives start, success and failure signals
and monitors for missed or stalled runs, using a one-day period and one-hour
grace. Email notifications are selected; inbox delivery still needs confirmation.

Logs: `/var/log/restic-backup.log`. See [backup setup and recovery instructions](server-backups.md)
for exclusions, protected configuration and restore commands. These services are
not activated by cloning the repository; a new installation must configure and verify its own
backup repository and monitoring check.

## Desktop connection and recovery notes

SSH and SFTP must work from the owner’s computer. With Tailscale, both computers
need access to the same permitted network; use the reachable Tailscale address.
A reboot ends running agents. Reconnect and resume from the saved setup checklist;
a dropped connection is different from a reboot. Keep normal SSH access for recovery.
No additional public agent port or tmux session is required for Claude Desktop.

The repository contains platform source and starter templates, not experiments or
credentials. For private source, grant repository access or provide a source-only
archive. Separate owners should use separate machines and credentials. Everyone
using lab shares its apps, files and granted services; lab is a trusted deployer,
not a sandbox for mutually untrusted users. See [sharing](sharing.md).
