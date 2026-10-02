# Changelog

## First experiment workflow lessons — 2026-09-07

- Document unpublished development, early local Git/browser checks, meaningful
  mobile/PWA/offline tests, persistence checks and clean release notifications.
- Clarify that root must not execute lab-owned browser dependency installers;
  use reviewed system package installation for missing browser libraries.
- Synchronize installed operating guidance and retain reproduction instructions.

## Installation and live validation — 2026-09-07

- Installed the platform for randomjunk.dev with explicit owner authorization;
  no VPS snapshot, as requested. Imported OpenAI/Gemini/Replicate and hosted ntfy
  configuration without exposing values. Android setup delivery confirmed.
- Added .test-only internal TLS for repeatable live checks without public ACME;
  trust is per-client, never installed machine-wide. Added Caddy timeout rollback.
- Added reproducible credential import, live integration and installed/source
  comparison tools. Installed operating instructions for lab.
- Passed actual app/identity/DB/vector/concurrency/stop-failure/Caddy-rollback and
  isolated local restore tests, then removed all disposable apps. Kept one
  welcome site for the real public HTTPS/readiness link.
- Source tests: 61 passing; 28 source parse checks; 30 installed files match.
  See docs/installation.md and docs/verification.md for limits and exact evidence.
- Backup scheduling remains disabled pending remote storage configuration;
  GitHub access, provider API/billing checks and iPhone/reboot testing remain open.

## Configuration decision — hosted ntfy, 2026-09-07

- Use hosted ntfy.sh, with expected usage at most about 50 notifications/day.
  No self-hosted ntfy server, additional domain or service is needed.
- Document Android/iPhone subscription setup and one readiness notification after
  application testing and HTTP verification. The owner requested these messages;
  no repeated approval is needed after configuring/testing delivery.
- Keep experiment compatibility with both phones as a requirement, with actual
  iPhone/PWA verification recorded separately. Corrected a stale world-readable
  notification-config comment; installer permissions remain root:lab 0640.
- Documentation/comment changes only; nothing installed and no messages sent.

## Revision 3 — source hardening and isolated review, 2026-09-07

This revision has not been installed. Live integration remains a separate phase.
The original detailed R1–R15 report was absent; the source checklist is in
`docs/review-checklist.md`.

- Replaced the shell privileged helper with a Python standard-library controller
  and fixed unprivileged workers. This boundary change was required to avoid
  root traversal of deployment-owned paths and to serialize entire lifecycles.
- Root-owned app containers now contain lab-owned `app/` and runtime-owned
  `data/`. Authoritative JSON, credentials and locks moved to `/var/lib/lab`.
- Base units specify an unprivileged identity and require provisioning. Start
  operations check effective identity. Environment files are mandatory/root-only.
- Secret grants merge with earlier grants/database settings; intended grants
  survive interrupted env writes. Removed runtime dotenv loading. Postgres has
  an explicit psycopg extra and a committed app lockfile; vector absence fails.
- Caddy uses structured records and a complete generated site set. Candidate
  validation precedes publication; reload failures restore the prior file.
  Static files are unprivileged-exported immutable snapshots with no symlinks.
- Backend static routing opens and serves contained regular-file descriptors,
  including index/fallback branches, with no symlink-following race.
- Creation failures preserve diagnostic resources/intents. Teardown stops first
  and blocks dependent destruction on failure. Removed unrecorded force cleanup.
- Private HTTP checks authenticate and do not follow redirects/use env proxies.
  HTTP verification is explicitly distinct from application/database readiness.
- Backup SQLite engines run as runtime users and use the backup API, encoded
  filenames and a manifest. Unique generations avoid reused/colliding dumps.
  Missing config/producer failures fail explicitly; systemd OnFailure covers process
  failures. Timer stays disabled at install.
- Added isolated restore staging and stopped prepare-only provisioning. Corrected
  restore ordering, stale WAL handling and restic-password documentation.
- Added fresh-install refusal for existing drafts, migration guidance, reproducible
  development setup, regression tests and an explicit deferred integration matrix.
- Documented that deployment-code control includes access to granted secrets.
  Caddy's private admin socket is caddy-owned, not inaccurately called root-only.
- Removed packaged bytecode. Retained prior revisions below as historical notes;
  their layouts and guarantees no longer describe current behavior.

## Historical revision 2 (superseded)


The first draft was reviewed and found not ready for unattended use. The problems
were privilege boundaries, partial-failure recovery, reliable teardown, and
announcing success before anything was verified. Changes:

### Privilege boundaries

- **The root backup job no longer sources a lab-writable file.** `.env.shared`
  was owned by `lab`; sourcing it ran arbitrary shell as root. Backup credentials
  now live in `/etc/lab/backup.env` (root-owned, in a root-owned directory) and
  are parsed line by line, never sourced. Root-run notification uses its own
  trusted path, `lab-notify-root`.
- **Sudoers argument globs replaced by a single validated helper.** Patterns like
  `systemctl stop lab-app@*` also match a trailing unrelated unit. There is now
  one rule — `lab ALL=(root) NOPASSWD: /usr/local/sbin/labctl` — and `labctl`
  validates its own operation and arguments, reconstructing every resource name
  from a checked app name.
- **Per-app runtime identity.** Each experiment runs as `labapp-<name>`, not as
  `lab`. One compromised app can no longer read another's credentials or connect
  to Postgres as the provisioning role.
- **Per-app secrets.** The master key file is root-only and unreadable by agents.
  Apps are granted named keys with `labctl secrets-grant`, copied into a
  root-owned per-app env file injected by systemd.
- **Caddy's admin API moved to a root-only Unix socket.** On the default
  `localhost:2019` any local process could reconfigure the proxy regardless of
  sudo restrictions.
- **Resource limits** (`MemoryMax`, `TasksMax`, `CPUQuota`) per experiment.

### Correctness

- **Malformed private-site config fixed.** `$(printf ...)` stripped the trailing
  newline, emitting `}}` — which Caddy tokenises as one token, not two.
- **Service command mismatch fixed.** `enable --now` did not match the sudoers
  rule; `disable --now` failed and was hidden by `|| true`, so an app directory
  could be deleted while its service kept running.
- **Postgres provisioning moved to the superuser.** Under PG16, a non-superuser
  creating a database owned by another role needs `SET ROLE` rights it did not
  have. `CREATE EXTENSION vector` also requires superuser — it previously warned
  and silently continued without vector support. It is now reported honestly.
- **Template rendering no longer uses `sed`.** A title containing `/` broke the
  expression and `&` re-inserted the match (`R&D` became `R{{TITLE}}D`).
  Rendering is now format-aware per file type.
- **SPA fallback fixed.** `StaticFiles` mounted at `/` captured every request, so
  the fallback route was unreachable and missing assets returned index.html.
- **Name validation** rejects trailing hyphens; the domain is validated too.
- **System Python is selected explicitly**, since a uv-managed interpreter under
  a home directory is unreachable with `ProtectHome=true`.

### Recoverability

- **Resource records** in `/srv/lab/.state/<name>.json`, written before creation
  and updated as each resource is acquired. `install.md` is generated from them.
- **A shared `flock`** serialises creation, removal and port allocation.
- **One teardown implementation** (`labrm`), used both for deletion and for
  rollback after a failed creation. Idempotent; the record is deleted last, and
  a partial failure is reported rather than swallowed.
- **`labdoctor`** reconciles records against actual directories, services, ports
  and Caddy sites, and flags orphans and experiments older than 90 days.
- **Caddy deployment is explicit**: stage, validate the whole candidate config,
  install, reload, roll back on failure. `--watch` was dropped — it is documented
  as a development feature, and in v2.10.2 its loop exits on a parse error, so a
  partially written file silently stops automatic reloading.

### Backups

- Cluster globals (`pg_dumpall --globals-only`) are now captured; per-database
  dumps omit roles and memberships.
- SQLite databases are snapshotted with `VACUUM INTO` rather than copied live.
- Caddy's data directory is included, so a restore does not re-issue every
  certificate.
- Database enumeration failure is detected instead of yielding an empty loop.
- An `ERR` trap alerts on failure anywhere in the job, not only the final check.

### Documentation

- Corrected: certificates are managed when a hostname is configured, not on
  first visit; TLS-ALPN-01 is also available; rapid creation can still exhaust
  the 50-certificates-per-domain-per-week limit.
- Corrected: static sites do have something to back up.
- Corrected: preinstalled Postgres removes installation work, not SQLite-to-
  Postgres migration work.
- `newlab` no longer notifies. Notification happens once, after the app is
  verified. `CLAUDE.md` defines completion and failure behaviour explicitly.
- Removal no longer claims to leave "literally nothing" — retained backups and
  installed PWA state on a phone are called out.

### Not adopted

- Regenerating `install.md` wholesale from the record on every `labdoctor` run:
  it would discard hand-added notes, which are the part that matters. `labdoctor
  --write-install-md` reports instead of overwriting.

## Agent entry points and GitHub preparation — 2026-09-07

- Name the project Randomjunk Lab (`randomjunk-lab`) and add README Start here links.
- Align root AGENTS.md/CLAUDE.md around platform development; move experiment
  operating guidance to templates/operating-instructions.md and update bootstrap.
- Preserve installed experiment guidance independently of source-development rules.

## Owner settings workflow — 2026-09-07

Added owner settings.txt, current setup-status.md and mandatory proactive owner review instructions; secrets remain outside Git.

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

## Reviewed experiment feedback — 2026-09-09

- Research named referents, share early previews/screenshots and distinguish building
  from ready; timestamped two-notification workflow with existing copy/open buttons.
- Explicit personal/shared browser scope and a visible PWA completion checklist.
- Scaffold install-offer UX and opt-in content-hashed shell generation at publish,
  preserving existing workers and waiting before service-worker activation.
- labdev temporary local servers/SQLite/process cleanup; labshot screenshots/errors;
  common fixtures for both app kinds and bounded deterministic animation adapters.
- Directional tests, explicit slow runs/limited parallelism, shorter factual app docs.

## Scaffolding in practice — 2026-09-09

- Install dialogs open only from the Install app button; install events do not
  interrupt input. Updated generated shell and browser regression checks.
- Fresh server/SQLite database per test prevents ranking-state leakage; reuse
  the browser per worker. Bounded model failures include model name and limit.
- Clarified style references, screen-relative sensors, inspected previews before
  notification, and desktop coverage for any shared component.

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

## WebKit testing profile — 2026-09-16

Installed reviewed Ubuntu graphics/media/text dependencies for Playwright WebKit.
Browser installation and testing run as lab, OS packages through trusted apt.
See docs/browser-testing.md (browser-testing.md from this docs directory) for exact
reproduction and engine/device coverage limits. No bootstrap rerun or app changes.

## Stripe discovery — 2026-09-16

Documented optional Stripe setup and separate administrator-controlled credential
access. Owner-entered test key presence/0600 verified without printing values.
No Stripe API requests, app grants, webhook setup or live activation performed.
Installed guidance contains names/paths only; credentials remain outside Git.

## Whole-server encrypted backups — 2026-09-17

Added reproducible Restic script, exclusions, log rotation and recovery guidance
for owner-authorized private B2 backups. The job starts at `/`, excludes replaceable
OS/runtime content, snapshots PostgreSQL and SQLite consistently, retains daily /
weekly / monthly history and verifies 1% after upload. Credentials and repository
passwords remain root-only outside Git. Live B2 backup and single-file restore
passed; the first autonomous scheduled run and full-machine rebuild remain pending.

## Backup monitoring — 2026-10-01

Added optional Healthchecks start/success/failure signals to whole-server backups, with protected configuration and external missed-run monitoring.

## Parcel storage — 2026-10-02

Excluded /srv/lab/parcel/data/transient/** from live and source Restic exclusions
at owner request. App source and SQLite metadata remain included.
