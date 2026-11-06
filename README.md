# Randomjunk Lab

A small experiments platform for Ubuntu 26.04 LTS: Caddy, static sites, optional
FastAPI, SQLite or PostgreSQL/pgvector, and restic backups. Python dependencies
use uv and committed lockfiles.

## Start here: connect your desktop agent over SSH

Use a fresh **Ubuntu 26.04 LTS** server and your own desktop agent account.
The new target still needs live installation validation; historical test evidence
in this repository is from Ubuntu 24.04. Do not upgrade an existing lab by running
bootstrap again.

1. Confirm SSH works from your laptop using the server address, administrator
   account and your SSH key. Root (or a sudo administrator) is for platform setup;
   everyday experiment work will use `lab`. If using Tailscale, connect your laptop
   to it and use the server's Tailscale address. Claude also needs working SFTP.
2. In that initial SSH session, install `curl` and `git` with the administrator's
   package manager, then clone the source:

   ```sh
   git clone https://github.com/random-quark/randomjunk-lab.git
   ```

   Note the checkout's absolute path. Choose one desktop connection below.
3. **Claude Desktop:** in the Code tab, open the environment selector → New
   environment → SSH → Add SSH connection. Enter `user@hostname` (or your SSH
   config alias), port and key; select the checkout folder. Desktop installs its
   helper and Claude Code automatically for that SSH user. No separate Claude CLI
   installation, tmux session or Remote Control command is required.
4. **Codex / ChatGPT desktop:** current official instructions require `codex` on
   the remote SSH user's login-shell PATH. Install it once on the server using
   the [official CLI instructions](https://learn.chatgpt.com/docs/cli), then follow
   the [authentication instructions](https://learn.chatgpt.com/docs/auth) for that
   same user. In the desktop app, open Settings → Connections, add/enable the SSH
   host, and choose the checkout folder. The app starts the remote app server;
   do not manually launch an interactive CLI or tmux session first.
5. Ask the connected agent to confirm `hostname`, `whoami` and the checkout path,
   then give it the setup instruction below. After installation, authorize your
   SSH public key for `lab`, add a separate desktop connection as `lab`, and select
   `/srv/lab` for experiment work. Claude provisions its engine for this user;
   for Codex, verify this user's PATH and authentication separately.

A server reboot ends running agent processes. Reconnect from the desktop app and
resume from the saved setup checklist; this is not a promise that an interrupted
command continues. A dropped connection and a reboot are different events. No
extra public agent port is needed. Keep a normal SSH client available for recovery.

Official connection references (checked 2026-11-06):
[Codex SSH](https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host),
[Claude Desktop SSH](https://code.claude.com/docs/en/desktop#ssh-sessions).
The Claude third-party-provider guide is only needed for that deployment mode.

## Set up your own machine

**Give your agent [SETUP.md](SETUP.md). That is the single installation entry point.**
It guides the agent through the questionnaire, installation, selected integrations,
backups, monitoring and verification. Use a fresh Ubuntu 26.04 LTS server and your own
domain/accounts. No AI subscription or provider key is needed for static apps.

Copy this instruction to your agent after downloading/cloning the repository:

> Read SETUP.md and help me set up this server. Bring the settings questionnaire
> to my attention first, ask for missing information as needed, and follow the
> linked instructions. Keep secrets outside the repo and chat. Verify the setup
> and tell me what is still pending before declaring it finished.

The agent creates ignored `.local/settings.txt` and `.local/setup-status.md` from
blank templates. Your answers and progress stay local; secret values go in
protected server files. Source tests are not proof that a new installation works.

**Prefer a form for settings and keys?** Use the
[private setup form](docs/setup-wizard.md). It runs on the VPS through an SSH
tunnel, puts ntfy/Replicate/OpenAI first, and securely hands your choices to the
setup agent. No paid API is required; installation and verification follow SETUP.md.

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
