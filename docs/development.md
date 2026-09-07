# Reproduce source development and tests

## Prerequisites and scope

Tested on Ubuntu 24.04.4 LTS, x86_64, Python 3.12.3, with bash/curl/git available.
Python dependencies use uv 0.8.22 with committed `uv.lock` files. Caddy 2.10.2 is
an optional local **parser-only** test binary, verified using the release's
SHA-512 checksum list. Nothing requires an installed Caddy/Postgres/systemd lab
service for these tests.

Some tests verify root ownership/locks. Run this suite in a disposable root-owned
development workspace (or a disposable container as root), not an experiment
runtime or everyday deployment-agent session. Tests never create OS users or
invoke real service operations. Controller.run is blocked by an autouse fixture;
operation tests replace it with recording/failure doubles. HTTP tests use an
in-process FastAPI client; SQLite tests use temporary dummy databases.

## Tooling on another machine

From a writable copy of this repository:

```sh
bash tools/setup-dev.sh
.dev-tools/uv/uv run --locked pytest
.dev-tools/uv/uv run --locked python tools/check-source.py
.dev-tools/uv/uv run --locked python tools/check-caddy.py .dev-tools/caddy
```

The setup script downloads a pinned uv installer and installs uv under
`.dev-tools/uv` with no shell-profile edits. It downloads/extracts only the Caddy
binary after checking its SHA-512 release checksum. Python packages go into the
project `.venv`; uv may also use the user's normal cache. No pip, global Python
packages, apt packages, host service configuration or platform installation is
part of development setup. Network access is needed to download the tools and
locked wheels. The setup script is documented scaffolding; the equivalent
commands below were the ones used in this session.

The app template has a separate `templates/app/uv.lock`. Its stable project name
means rendering NAME/TITLE does not invalidate that lock. To intentionally change
application dependencies, edit its pyproject and run:

```sh
.dev-tools/uv/uv lock --project templates/app
```

Commit both pyproject and lock. Scaffolding uses `uv sync --locked` with system
Python and adds `--extra postgres` when needed; there is no silent fallback to an
unlocked dependency resolution. OS/Caddy package versions during future installation
are recorded separately by bootstrap, not pinned by uv.

## What was done on this server

1. Extracted the supplied ZIP into `/root/workspaces/labserver-review/lab-server`,
   rejecting absolute/traversing archive paths and symlinks. Copied the pasted
   handoff alongside it. The original detailed R1–R15 markdown was absent.
2. Verified every extracted file byte-for-byte against the ZIP, and saved an
   archive SHA-256 alongside the workspace. Initialized a local Git repository
   with an unchanged-source checkpoint before implementation.
3. Installed uv 0.8.22 under `/root/workspaces/labserver-review/tools/uv`, using
   `UV_UNMANAGED_INSTALL` and the downloaded installer. No shell profile changed.
4. Generated both committed lockfiles using that uv executable; installed test
   dependencies only into the project's .venv (plus uv's cache).
5. Downloaded Caddy 2.10.2 under the sibling tools directory, checked SHA-512
   against the release list, and extracted only its binary. Ran `version`,
   `hash-password` on dummy input, and `adapt` on temporary test configs.
6. Implemented the changes described in CHANGELOG and security.md, added isolated
   tests, and updated all current operator guidance. Removed bundled bytecode
   from source. Kept the original changelog section as explicitly historical.
7. Ran the verification commands below. Temporary test/Caddy directories are
   cleaned automatically. Source, lockfiles, .venv, tool downloads and normal
   caches remain for continuing work. No live test resources were created.

Commands actually used (from the project directory):

```sh
/root/workspaces/labserver-review/tools/uv/uv run --locked pytest
/root/workspaces/labserver-review/tools/uv/uv run --locked python tools/check-source.py
/root/workspaces/labserver-review/tools/uv/uv run --locked python tools/check-caddy.py /root/workspaces/labserver-review/tools/caddy
```

The API command sandbox failed before process startup because its visualization
mount was read-only. Workspace commands therefore used the approved execution
path outside that broken sandbox. This did not authorize or cause platform
installation. All mutations were source/development tooling, Git checkpointing,
virtual environments/caches or disposable test fixtures.

## Changed behavior to remember

- Source moves into app/ below a root-owned app container.
- Static publication is explicit and snapshots regular files; symlinks are rejected.
- State/locks/credentials move to root-only /var/lib/lab.
- Failed create keeps resources; failed stop blocks destructive teardown.
- `--prepare-only` supports unpublished development and stopped restoration; `publish` activates afterward.
- HTTP-verified means only the documented HTTP/service checks passed.
- Bootstrap is fresh-only and leaves backup scheduling disabled pending setup.

The original outside `REVIEW.md` and `review_checks.py` describe/reproduce the
**original archive**, not the changed source. Use this repository's current tests
and docs/review-checklist.md for the revision-3 status.

## Checkpoints and transfer

The unchanged input is Git commit `9b229047a93d910ff223c791d1ba60761528531b`. Tool/archive hashes are in
`docs/provenance.json`. The final source changes are saved in a separate local
commit. No branch was pushed and nothing was published externally.

A source-only ZIP is generated from the final commit at
`/root/workspaces/labserver-review/labserver-review-v3.zip`. Recreate it with:

```sh
git archive --format=zip --prefix=lab-server/ --output=../labserver-review-v3.zip HEAD
```

It includes documentation/tests/lockfiles, excludes Git history and ignored
virtual environments/tooling, and is the candidate to transfer after review.
Keep this local Git repository if you want the original-to-revised diff.

## Follow-up decision: hosted notifications

The owner chose hosted ntfy.sh (expected at most about 50 messages/day), Android
as their current phone, and iPhone compatibility as a requirement. Added
notifications.md, updated setup/agent guidance and corrected the stale permission
comment in bin/notify. This was a documentation-only configuration decision; no
server, credentials, topic subscription or notification was created. The source
ZIP was refreshed from the follow-up Git commit.

## First experiment lessons — 2026-09-07

Added docs/experiment-workflow.md and linked it from installed agent guidance.
The Neon Blocks run exposed missing lab Git identity, missing browser OS libraries,
and an offline reconnect retry gap. The reusable workflow now covers early tooling
checks, prepare/build/test/publish, explicit PWA/device limits and fixture cleanup.
Corrected browser dependency guidance: app-owned executables must never run as root;
review package requirements as lab and install approved names through system apt.
This is a documentation update; no platform runtime code or services changed.
Authoritative docs and agent guidance are synchronized to the installed paths,
and the source-only ZIP is refreshed from the documentation commit.

## Repository entry points — 2026-09-07

Root AGENTS.md and CLAUDE.md now contain identical platform-development guidance.
The installed operator instructions moved to templates/operating-instructions.md;
bootstrap installs that template under the existing three agent paths. README
Start here links distinguish development, fresh installation and experiment use.
GitHub repository name: randomjunk-lab. GitHub CLI is installed from Ubuntu apt
(`apt-get install --no-install-recommends gh`) for interactive browser authorization;
credentials must remain outside source and must never be pasted into chat.

GitHub target chosen by the owner: random-quark/randomjunk-lab, using the
lobodelmar account; private visibility initially. GitHub CLI version installed:
2.45.0-1ubuntu0.3 (Ubuntu package). Authorize interactively with
`gh auth login --hostname github.com --git-protocol https --web` in the platform
admin session; never place a token in source, chat or a remote URL. Authentication
here does not grant the lab deployment user access to GitHub credentials.

## GitHub publication completed

Authenticated as lobodelmar through browser device authorization and created
https://github.com/random-quark/randomjunk-lab as a private organisation repository.
Pushed the existing commit history on master and configured origin/upstream.
Repeat updates from this checkout with `git push origin master` after checks.
GitHub credentials stay in the root user's gh configuration outside this repository;
lab has not been granted them. Individual experiments have not been pushed.

## Owner settings workflow — 2026-09-07

Added settings.txt (non-secret owner choices), setup-status.md (agent-maintained current evidence), and docs/settings-workflow.md. These guide agents, not bootstrap parsing; no live settings were applied. Root and installed agent instructions require surfacing this review and unresolved setup work.
