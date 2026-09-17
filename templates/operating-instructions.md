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

For a new app, use `newlab NAME ... --prepare-only` while preparing its first
rough preview, then publish early with `sudo /usr/local/sbin/labctl publish NAME`.
A clearly labeled building preview is encouraged; never present it as finished.
Keep private apps private and protect costly or shared-data endpoints from the start.
Start as lab in the app directory; run `labpreflight NAME` before implementation.
For shared web apps use `--engines chromium webkit` and test both engines.
Browser setup and device-test limits: /usr/local/share/lab/docs/browser-testing.md.
See /usr/local/share/lab/docs/experiment-workflow.md for the completion workflow,
browser setup, offline/PWA checks and reproducibility records.

Never run app-owned scripts, virtualenv executables or dependency hooks as root,
including browser dependency installers. Browser tests/downloads run as lab; an
administrator installs reviewed OS package names through the system package manager.

Before tests: `labbuild NAME`, then `labbuild NAME --check`.
After static edits: `sudo /usr/local/sbin/labctl publish NAME`.
After backend edits: `sudo /usr/local/sbin/labctl service restart NAME`.
After shell edits in either kind: `sudo /usr/local/sbin/labctl publish NAME`
regenerates the opt-in content-hashed service worker. Edit public/sw.template.js,
not generated public/sw.js. Existing custom workers remain unchanged unless migrated.
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

## Who uses these

The owner uses Brave and Chrome on Android. Always provide manual install
instructions when the browser does not offer beforeinstallprompt. For a personal
experiment prioritize that phone; do not silently drop an explicitly requested
platform. Apps with any shared component (including a leaderboard) must also work on iPhone Safari and desktop. Record
personal/shared scope and tested devices versus assumptions in install.md.

## Reference and preview before polish

When a request names a real object/show/product or visual style, look it up or inspect the supplied
reference before rendering. Describe the intended shape in one or two concrete
sentences. State assumptions and keep working; do not block on optional feedback.
Get a rough working preview on the real URL early. Capture and inspect a phone-sized
screenshot before notifying or sharing; fix obvious layout errors first. Share it through the
available attachment/image tool (SendUserFile if available), not merely a tool
image only you can see. If attachments are unavailable, share the preview URL.
Invite correction without waiting for it; show major visual changes again.

## Every user-facing experiment ships with

- [ ] Manifest with name, scope, start URL, display and theme colours.
- [ ] Original appropriate icons: PNG 180/192/512 and maskable 512, committed.
- [ ] Shell service worker with an automatically content-hashed cache revision.
- [ ] Visible Install app button: opens native-prompt guidance or browser-menu fallback
      only on a user tap; hidden in standalone. Never auto-open a modal on load,
      a timer, or an install event. An optional non-modal banner must not steal focus.
- [ ] Phone viewport checked for layout and console errors; shared apps checked
      at desktop size and iPhone Safari when available, with limits recorded.
- [ ] Offline shell works and network-dependent features explain their status.
- [ ] Short install.md: URL, data, reproduction, current test result and caveats.

Non-web experiments or explicitly requested exceptions should record why a PWA
item is not applicable. A clean manifest alone does not prove the install flow.
Exercise the visible offer on the live URL. New templates provide this flow in
pwa.js: preserve it when replacing app.js, or supply an equivalent tested UX.

## Progress and completion notifications

For a requested new experiment, send two timestamped ntfy messages with the URL:
after first publish, reachability check and screenshot inspection: “NAME · started HH:MM · building”; after behavior tests
and labctl verify pass: “NAME · ready HH:MM”. Use machine-local time (check its
zone). Do not send duplicates for every republish. No extra permission is needed.
Stay quiet between them while the owner is active; at most one useful milestone
when they are away on a long build. Never call an incomplete preview ready.
For a change to an existing app, don't invent another first-publish event; send
its completion message after checks. See docs/notifications.md for examples.

## Development and tests

Use `labdev NAME` for a loopback preview with a reserved ephemeral port and temporary
SQLite database; Ctrl-C/SIGTERM cleans up its process group and test data. It does
not load production keys or support automatic Postgres test provisioning.
Use `labshot NAME --viewport 390x844 --out DIR [--url /path]` for a published-page
screenshot plus error report. Local URLs use app/tools/labshot.py directly.
Run these as lab. Browser tooling lives in the experiment's uv dev dependencies.
Keep private credentials out of screenshots, command lines and shared reports.

Test direction against a fixed landmark, including the relevant axis. Step models
or control the browser clock instead of sleeping through animations. Real elapsed
time is only for tests of actual timing/network/lifecycle behavior. Run the full
suite before completion; no default slow-test exclusion or unbounded parallelism.
Use exact process handles/PIDs for cleanup, never pkill -f from the agent shell.

Keep install.md current: behavior, reproduction, latest evidence link and open checks.
Move release history to CHANGELOG.md and dated artifacts/; preserve owner notes.
Keep optional decisions in decisions.md. Do not append session narratives here.

Provider defaults and key names: /usr/local/share/lab/docs/providers.md.
Payments only when requested: /usr/local/share/lab/docs/payments.md explains
Stripe credential access, test mode and per-app setup.

PostgreSQL and SQLite are covered by the server backup job. Before adding another
database engine or separate data mount, notify the administrator and read
/usr/local/share/lab/docs/server-backups.md.
Only when email is requested: consult /etc/lab/email.json if present and
/usr/local/share/lab/docs/email.md. Missing configuration does not authorize setup.

## When resuming server setup

For server-wide configuration, read settings.txt and setup-status.md in the
platform source checkout (this server: /root/workspaces/labserver-review/lab-server).
If lab cannot access it, have the administrator conduct that review; do not change
permissions to expose root files. Proactively bring settings.txt to the owner,
reuse known answers and surface unresolved steps at handoff. See
/usr/local/share/lab/docs/settings-workflow.md. This review applies to server setup,
not a requirement to re-answer every setup question for each ordinary experiment.

## App-link notification format

Use `notify "Title" "https://app.example.com"` for app readiness. The message body
contains only the URL, with Copy link and Open in browser buttons. No custom click
destination is set, so the notification opens normally in ntfy. Link text inside
ntfy still follows the client's link behavior; the Copy link button copies exactly
the URL. The owner confirmed both buttons work on Android.

Legacy `notify "Title" "Description" "https://app.example.com"` calls remain valid,
but the explicit URL replaces the body to preserve the same format. Put meaningful
context in the title. Plain-text messages without a URL retain their body and have
no actions. Copy support varies by client/version; real iPhone behavior is untested.

## Database library choice

For small SQLite apps, Python's sqlite3 with parameterized queries is sufficient.
SQLAlchemy is optional, independent of database choice; add it deliberately as lab
with `uv add 'sqlalchemy>=2.0,<3'` in app/ when Core or ORM helps the design. Commit
the updated pyproject.toml and uv.lock. Postgres includes psycopg, not SQLAlchemy.
Installing SQLAlchemy alone does not make an existing app portable between databases.
