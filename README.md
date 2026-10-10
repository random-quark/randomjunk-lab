# Randomjunk Lab

A small experiments platform for Ubuntu 24.04: Caddy, static sites, optional
FastAPI, SQLite or PostgreSQL/pgvector, and restic backups. Python dependencies
use uv and committed lockfiles.

## Set up your own machine

**Give your agent [SETUP.md](SETUP.md). That is the single installation entry point.**
It guides the agent through the questionnaire, installation, selected integrations,
backups, monitoring and verification. Use a fresh Ubuntu 24.04 server and your own
domain/accounts. No AI subscription or provider key is needed for static apps.

Copy this instruction to your agent after downloading/cloning the repository:

> Read SETUP.md and help me set up this server. Bring the settings questionnaire
> to my attention first, ask for missing information as needed, and follow the
> linked instructions. Keep secrets outside the repo and chat. Verify the setup
> and tell me what is still pending before declaring it finished.

The agent creates ignored `.local/settings.txt` and `.local/setup-status.md` from
blank templates. Your answers and progress stay local; secret values go in
protected server files. Source tests are not proof that a new installation works.

Other entry points:

- **Develop the platform:** [AGENTS.md](AGENTS.md), mirrored in [CLAUDE.md](CLAUDE.md).
- **Build apps after installation:** launch your agent **as lab in `/srv/lab`**;
  it reads the installed `AGENTS.md` / `CLAUDE.md`.
- **Tests and tooling:** [docs/development.md](docs/development.md).
- **Sharing/audit scope:** [docs/sharing.md](docs/sharing.md).

Repository: [random-quark/randomjunk-lab](https://github.com/random-quark/randomjunk-lab).
If private, the owner must grant students access or provide a source-only archive.
This contains the platform and starter templates, not the running experiments or
server credentials. Use separate machines/keys for independent student ownership;
`lab` is a trusted deployer, not a sandbox for mutually untrusted users.

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

The original server has daily encrypted **Restic backups to Backblaze B2**, running at
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
not activated by cloning the repository; a new installation must configure and verify its own
backup repository and monitoring check.
