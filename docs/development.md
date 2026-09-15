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

## Deployment CLI follow-up — 2026-09-07

Owner's launch failed because Claude existed only under /root/.local/bin. Install
with the official native installer as lab; verify command discovery in a fresh lab
login shell. Existing shells need ~/.local/bin added to PATH. Keep owner login
pending until checked interactively; do not reuse root credentials. Added this
missing prerequisite to SETUP.md, settings.txt and setup-status.md.

## ntfy tap destination fix — 2026-09-07

The sender previously assigned the full body to Click, breaking prose-plus-link
notifications. Added a separate optional URL argument, kept URL-only callers
compatible, omitted click actions for plain text, and used a quoted header array
and literal request data. Added captured-curl regression tests; no test topics or
credentials are used. Actual phone tap confirmation remains an owner check.

## Owner-confirmed notification actions — 2026-09-07

Made the tested URL-only body plus Copy link/Open in browser buttons the default
for app-link notifications. Removed the custom click override so tapping the
notification retains ntfy's normal behavior. Owner confirmed both actions work on
Android. Updated JSON payload regression tests and operating instructions; iPhone
behavior remains untested. No extra readiness test notification is necessary.

## Experiment tooling revision — 2026-09-09

Applied reviewed Claude feedback from /home/lab/platform-feedback/2026-09-09-platform-feedback.md.
Added common dev fixtures/tools copied into both app kinds, locked pytest/Playwright/
xdist dependencies without default parallelism/skips, labdev and labshot wrappers,
and an unprivileged opt-in content-hash PWA builder invoked by publication.
Updated bootstrap installs these files only on fresh machines. Existing app sources
and custom workers are not migrated automatically. Existing-server deployment
copies reviewed helpers/templates/docs; never rerun bootstrap.

New scaffold test/development source is in templates/common, copied by scaffold.py.
Template projects have independent uv locks. Run uv lock --project templates/app
and templates/static when intentionally changing dependencies. Browser binaries
remain per-lab-user tooling and are not downloaded by scaffold generation.

Reproduce isolated runtime checks: make a readable staging copy of templates/,
bin/lib/ and tools/ outside /root (excluding .venv and __pycache__), then run as lab:
`python3 STAGE/tools/check-experiment-runtime.py --source STAGE`.
This creates only temporary apps, runs browser/tests as lab and deletes their
source and test databases on exit. It does not call labctl or publish sites.

Existing-server update used `python3 -I tools/deploy-feedback.py --apply` from the
trusted root-owned checkout. It serializes with the platform lifecycle lock,
backs up replaced files and records modes/ownership before installing helpers,
templates and docs. It removes only the two obsolete installed template sw.js
files; it never migrates app workers. Backup manifest is an administrator rollback
record: restore listed preexisting files with their saved ownership/mode and remove
only listed newly introduced files under the same lifecycle lock. Do not roll back
live app data or rerun bootstrap. Current backup directory:
/root/workspaces/labserver-review/deployments/feedback-mk0e1qvc.

## Second feedback update — 2026-09-09

Reproduce with `uv run --locked pytest`, `uv run --locked python tools/check-source.py`,
then the staged unprivileged runtime check described above. Regression checks cover
explicit installation, uninterrupted form input and independent clean backend DBs.
Deploy from the trusted checkout using `python3 -I tools/deploy-feedback.py --apply`,
then `python3 -I tools/verify-installed.py`; compare the three installed operating
instruction copies and installed docs with source. This refreshes platform files
only; existing experiment code/data and service workers are preserved.

## Optional SQLAlchemy — 2026-09-09

Removed unused SQLAlchemy from new backend defaults; keep psycopg in the Postgres
extra. Agents add SQLAlchemy explicitly when useful. The live integration DB probe
now adds its own SQLAlchemy dependency as lab before using it. Platform test
dependencies retain SQLAlchemy. Existing experiments retain their dependencies.
Reproduce with `uv lock --project templates/app`, required source checks, and the
staged runtime check as lab; deploy with tools/deploy-feedback.py --apply.

## Yamyam workflow feedback — 2026-09-12

Added unprivileged labbuild NAME [--check] and labpreflight NAME [--engines ...].
Build reuses publication's generator; freshness checking never writes. Preflight
checks source/Git/tool access and real browser launch/screenshots, without secrets.
New runbooks separate current state, owner notes and history; operator guidance
links detailed workflow instead of accumulating app-specific rules. Existing apps
are not rewritten. Backend working-tree assets still require an isolated checkout
for unpublished development. Backups remain deferred by the owner.
Reproduce: required source checks, staged runtime check as lab, then deploy with
python3 -I tools/deploy-feedback.py --apply and verify-installed.py.

Standard development packages now include ripgrep; on this existing host use
`apt-get install -y ripgrep`, without rerunning bootstrap.

## 2026-09-12 — additional app hostnames

`sudo /usr/local/sbin/labctl alias yamyam yumyum` adds yumyum.randomjunk.dev
to the same site and keeps the original hostname, runtime identity and data.
Aliases are validated same-domain labels in authoritative app records, persist
through publish/reconcile, cannot collide with app names or other aliases, and
retain the same private-site authentication. Failed Caddy publication restores
the previous record; the existing publisher restores its live file.

Validation: `uv run --locked pytest` (81 passed);
`uv run --locked python tools/check-source.py`.
Deploy the reviewed helper changes using `python3 tools/deploy-hostnames.py`,
then run the alias command and verify HTTPS on both hostnames.

## Resend toolkit discovery — 2026-09-13

Added a short operating-instruction pointer, provider-table entry and focused
email guide covering sender domain, backend grants, reusable reference and safe
delivery checks. Confirmed RESEND_API_KEY presence, yamyam grant and reference
file without exposing values. No email sent or DNS/app configuration changed.
Reproduce installed docs from this checkout with the documented deployment tool;
compare docs and operating copies afterwards.

## Portable optional email configuration — 2026-09-13

Replaced server-specific email guidance with placeholders and an explicit opt-in.
Added optional owner settings; actual sending choices live in /etc/lab/email.json
(root:lab 0640), separate from root-only credentials. This file informs agents; it
does not automatically inject app settings. Existing email apps remain unchanged.
No email sent and no DNS or credentials changed.

## Optional OpenRouter — 2026-09-15

Added OPENROUTER_API_KEY to optional credential import and provider guidance,
with openrouter selectable in the owner questionnaire. Existing host credential
was merged under the platform lock and verified root-only without printing it.
No app grants, restarts or paid API calls. Reproduce through protected provider
staging during full provisioning, or an administrator merge on an existing host.
