# Operating the installed lab platform

These instructions apply after installation. To develop the platform itself,
use AGENTS.md in the platform source repository. Everyday experiments run under the deployment identity `lab`; root
installation/administration is a separately authorized task.

## Create and edit

Use `newlab NAME --static` by default. Use `--app` for server-side persistence,
provider keys, or work requiring a backend. Optional flags: `--db sqlite`,
`--db postgres`, `--private`, `--secrets KEY,KEY`, `--title TEXT`.
Names are 2–24 lowercase alphanumeric/hyphen characters, with no end hyphens.
Postgres provisioning requires pgvector; unavailable vector support is a failure.

Edit `/srv/lab/NAME/app/`. Commit application source and uv.lock. Runtime data
is `/srv/lab/NAME/data/`, owned by `labapp-NAME`; deployment code must not contain
secrets. The helper injects environment values through systemd, so don't create
or load a local .env in the production scaffold.

For a new requested app, prefer `newlab NAME ... --prepare-only`, implement and
exercise the actual experience locally, then `sudo /usr/local/sbin/labctl publish NAME`.
Preparation also supports development; do not publish a scaffold as a finished app.
Check repository-local Git identity and required test tooling before implementation.
See /usr/local/share/lab/docs/experiment-workflow.md for the completion workflow,
browser setup, offline/PWA checks and reproducibility records.

Never run app-owned scripts, virtualenv executables or dependency hooks as root,
including browser dependency installers. Browser tests/downloads run as lab; an
administrator installs reviewed OS package names through the system package manager.

After static edits: `sudo /usr/local/sbin/labctl publish NAME`.
After backend edits: `sudo /usr/local/sbin/labctl service restart NAME`.
For dependencies, run `uv sync --locked --python /usr/bin/python3` as lab in app/;
include `--extra postgres` for Postgres apps. Deliberate dependency changes use
uv to update and commit the lock before syncing.

## Diagnose, grant and remove

- `labs` and `labdoctor` report records and inconsistencies.
- `sudo /usr/local/sbin/labctl logs NAME` reads the app journal. Logs may contain
  application-written secrets: do not paste them without checking.
- `sudo /usr/local/sbin/labctl secrets-list` shows key names.
- `sudo /usr/local/sbin/labctl secrets-grant KEY,KEY NAME` merges grants; restart
  to apply. Existing database settings and earlier grants are preserved.
- `labrm NAME` confirms removal. `labrm --yes NAME` is noninteractive.

Do not edit installed helpers, Caddy configuration, unit files or authoritative
records from the deployment account. Changes belong in the platform repository.
Failure leaves metadata for diagnosis; don't assume automatic rollback. A stop
failure blocks destructive cleanup. Corrupt metadata needs administrator recovery,
not an unrecorded --force deletion. Shared packages and retained backups survive
app removal.

## Trust and completion

The deployer controls runtime code and can request named master keys, so it can
recover granted secrets through that code. File permissions isolate runtime
users; they do not make a fully authorized deployer unable to read granted keys.
Never hardcode, print, commit or send secrets. Private-site passwords are stored
root-only at `/var/lib/lab/credentials/NAME.basic`; ask the administrator to
retrieve/deliver them securely.

`labctl verify NAME` checks authenticated HTTPS when private, active backend
service, and a matching liveness response. It does not test database connectivity,
business behavior, phone installation, or backup recovery. Test those separately.
Public apps spending provider money require their own authentication/rate limits.

The owner has requested hosted ntfy readiness notifications. Once the topic is
configured and delivery is tested, send one notification after the requested
behavior and `labctl verify NAME` pass; no separate approval is needed each time.
Include the app URL, never credentials or private content. Do not notify merely
because scaffolding or installation completed. See /usr/local/share/lab/docs/notifications.md.

Target Android and iPhone compatibility for experiments. Test relevant browser
features on both when possible; report any iPhone/PWA behavior that still needs
owner testing rather than claiming it was verified.

Record external resources and manual steps in app/install.md; do not overwrite
hand-written notes.

Provider selection defaults and key names are documented in /usr/local/share/lab/docs/providers.md.
