# Randomjunk Lab

A small experiments platform for Ubuntu 24.04: Caddy, static sites, optional
FastAPI, SQLite or PostgreSQL/pgvector, and restic backups. Python dependencies
use uv and committed lockfiles.

**Status:** installed and live-tested on `randomjunk.dev`. See the
[installation record](docs/installation.md), [test evidence](docs/verification.md)
and [review checklist](docs/review-checklist.md). Remote backup configuration
and iPhone checks remain separate follow-up tasks. Other
machines still require an explicitly authorized installation and validation.

## Start here

**Setting up or continuing setup?** Review [settings.txt](settings.txt) with your
agent. Fill in what you know; leave unknowns blank and use `skip` for deliberate
omissions. Never enter secrets there. The agent must raise this with you and keep
[setup-status.md](setup-status.md) current. See [the workflow](docs/settings-workflow.md).

- **Develop this platform:** read [AGENTS.md](AGENTS.md). [CLAUDE.md](CLAUDE.md)
  contains the same instructions for Claude Code.
- **Install on a fresh machine:** read [SETUP.md](SETUP.md).
- **Create experiments on an installed server:** read `/srv/lab/AGENTS.md`.
  Its source is [the operating-instructions template](templates/operating-instructions.md).
- **Reproduce development and tests:** read [docs/development.md](docs/development.md).

The private GitHub repository is [random-quark/randomjunk-lab](https://github.com/random-quark/randomjunk-lab). This repository contains the
platform and its starter templates; generated experiments keep separate Git
repositories. Never commit live credentials, databases, certificates or caches.

## Work on this repository

Read [development instructions](docs/development.md) for exact tooling setup and
commands. `uv run --locked pytest` runs isolated tests; it does not install the
platform. `bootstrap.sh` is an explicitly gated **fresh installer**, never a test
command or upgrade mechanism.

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

Read [SETUP.md](SETUP.md), [security](docs/security.md),
[recovery](docs/recovery.md), [hosted notifications](docs/notifications.md), [migration](docs/migration.md), and
[agent operating instructions](templates/operating-instructions.md) before installing or administering.

## Experiment development workflow

New static and backend scaffolds include an in-app PWA offer, content-hashed shell
worker generation, uv-locked test tooling, and tools/tests shared fixtures. Start a
local preview with labdev, publish an early safe preview, and share screenshots
with labshot. See [the workflow](docs/experiment-workflow.md). Existing apps are
not rewritten: custom workers opt in only through an explicit migration.

## Server backups and monitoring

This server has daily encrypted **Restic backups to Backblaze B2**, running at
**03:30 Europe/Berlin**. The whole-machine backup covers data and configuration,
with exclusions for replaceable OS files, caches, logs and selected secrets.
It includes PostgreSQL dumps and discovered SQLite snapshots; new database
engines or unusual storage locations still need a backup review.

Retention is **7 daily, 4 weekly and 6 monthly snapshots**. Each run checks 1% of
repository data. **Healthchecks.io** receives start, success and failure signals
and monitors for missed or stalled runs, using a one-day period and one-hour
grace. Email notifications are selected; inbox delivery still needs confirmation.

Logs: `/var/log/restic-backup.log`. See [backup setup and recovery instructions](docs/server-backups.md)
for exclusions, protected configuration and restore commands. These services are
configured on this machine; a new installation must configure and verify its own
backup repository and monitoring check.
