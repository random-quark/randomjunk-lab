# Randomjunk Lab

A small experiments platform for Ubuntu 24.04: Caddy, static sites, optional
FastAPI, SQLite or PostgreSQL/pgvector, and restic backups. Python dependencies
use uv and committed lockfiles.

**Status:** installed and live-tested on `randomjunk.dev`. See the
[installation record](docs/installation.md), [test evidence](docs/verification.md)
and [review checklist](docs/review-checklist.md). Remote backup configuration,
and iPhone checks remain separate follow-up tasks. Other
machines still require an explicitly authorized installation and validation.

## Start here

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
labdoctor
labrm hello
```

Static source edits need `labctl publish NAME`. Backend source edits need
`labctl service restart NAME`. HTTP verification is not application testing.

Read [SETUP.md](SETUP.md), [security](docs/security.md),
[recovery](docs/recovery.md), [hosted notifications](docs/notifications.md), [migration](docs/migration.md), and
[agent operating instructions](templates/operating-instructions.md) before installing or administering.
