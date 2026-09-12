# Building and finishing an experiment

Lessons from Neon Blocks, 2026-09-07. Use the existing lab/VPS workflow for this
owner's experiments. Domain and hosted ntfy are already configured; ask only for
missing resources required by the actual app. No provider keys are needed for a
local game. Do not redirect an experiment to another hosting service by default.

## Start with a short preflight

As lab, select static or backend plus the smallest suitable database. Use
`newlab NAME --app --db sqlite --prepare-only` for a small persistent app;
use `--static --prepare-only` when no backend is required. Preparation creates
resources before a first preview. Publish a rough, labeled building preview early;
finish behavioral verification before claiming readiness. The installed helper remains the
only route for privileged lifecycle changes; do not rerun bootstrap.

In app/, check `git var GIT_AUTHOR_IDENT`. If no identity is configured, use a
clearly labeled repository-local agent identity, without impersonating the owner:

```sh
git config user.name 'Lab Agent'
git config user.email 'lab-agent@localhost'
```

Preserve an existing identity. Commit source, dependency manifests/locks, original
assets and install.md. Keep runtime DB files, credentials, caches and virtualenvs
out of Git. A source archive is useful for transfer but does not back up runtime data.

## Prepare only the tooling the app needs

Use uv and the system Python as lab. For an app needing browser verification:

```sh
uv add --dev pytest httpx playwright
UV_PYTHON_DOWNLOADS=never uv sync --locked --python /usr/bin/python3
.venv/bin/playwright install chromium
```

Dependency addition is deliberate and updates the lock; subsequent reproduction
uses the committed lock. Check browser launch before writing the whole app.
The browser download alone may not supply OS graphics/audio/accessibility libraries.
Run `.venv/bin/playwright install-deps --dry-run chromium` **as lab** to inspect
requirements. An administrator reviews the package names and installs them using
the trusted system apt executable. Never pipe that output to a privileged shell,
or execute an app-owned `.venv/bin/playwright` as root. Record actual packages and
versions in install.md. These dependencies are optional testing tools, not a new
requirement for every experiment or for production game execution.

Browser binaries/cache belong to lab. Run the test browser and all app code as
lab, with isolated test databases and loopback listeners. Privileged platform
administration must not import or execute deployment-owned code.

## Verify the requested behavior

Match checks to the app instead of stopping at the health endpoint. For a game:
exercise touch/keyboard input, collisions/rotation/line clears, game over, pause,
score submission and persistence. For a persistent app, verify a committed record
survives a service restart. Use isolated fixtures; remove any necessary live test
record by its exact ID, under the runtime identity, without deleting real data.

Mobile-sized browser tests should check that primary controls fit, dialogs work,
and there are no JavaScript errors. Headless mobile emulation is useful evidence,
but does not prove real Android/iPhone installation, speakers, or browser gestures.
Record those remaining owner checks explicitly. Do not add tests that merely
repeat markup or implementation details.

For a PWA, test the first-visit Install app button, dismissal and reopening, actual shell
caching, offline reload/play, and reconnect behavior. An install button must use
native prompting only when the browser exposes it; provide manual instructions
otherwise. Never open install dialogs automatically, including on timers or install
events; keep gameplay and forms usable. An optional non-modal banner must not
steal focus. iPhone installation requires its own device check. Start sound from a
user gesture and silence it on pause/background. Browser policy references:
https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event

Offline writes need a bounded persistent queue and idempotent server handling.
Do not rely solely on the online event: transient failures can outlast it. Retry
pending writes on returning to the app and on a bounded schedule while online;
stop requests when there is no work. Test offline-to-online recovery directly.
New templates preserve public/sw.template.js; labctl publish hashes regular public
files and regenerates public/sw.js as lab for both app kinds. No skipWaiting is
used, so existing tabs keep their worker until closed. Existing custom sw.js files
without a template are left alone. To migrate, preserve the custom logic in
sw.template.js, add __LAB_CACHE__ (optionally __LAB_ASSETS__), explicitly remove the
old generated target as lab, then publish and test update/offline behavior. Never
blindly replace an existing app's worker. Backend Python edits also need a restart.
Hashed cache names prevent missed version bumps; this is not atomic versioned
backend deployment, and clients must finish caching while their assets are available.

## Show it before you polish it

Look up a named real-world referent or visual style before rendering it. State the assumed shape
concretely and continue without waiting for optional feedback. A Price Is Right
wheel, for example, must not be guessed from the generic word “wheel”.

Publish an early preview within the requested privacy/billing constraints and
capture and inspect a phone-sized screenshot before sending its building link.
Fix obvious layout errors, then share that screenshot through the available
user-visible attachment mechanism; SendUserFile is one option, not a universal
requirement. A screenshot visible only to the agent does not count as sharing.
Ask for correction and continue working. Repeat after substantial visual changes.

## Tests that catch the actual mistake

For directional behavior, pick a fixed panel/grid line/particle and assert its
final location and sign on the axis the user sees. “Rotation changed” is inadequate
for checking drag direction. Bound settling distance as well as reaching idle.

Use the scaffolded tests/conftest.py fixtures and tools/README.md. Drive dt-based
models to completion with an explicit adapter and a bounded step count that fails
if rest is never reached. Use controllable browser clocks for timers/RAF. Do not
wait through whole decorative animations; retain real-time tests only when real
timing itself is the subject. Playwright move timing is not representative of a
finger's velocity; use controlled input timestamps for velocity-model tests and
separately check actual browser event wiring. Do not assume a universal event rate.

Plain pytest runs all tests. Mark genuinely slow integration cases; an explicit
`pytest -m 'not slow'` is useful during iteration, not completion evidence. xdist is
available but off by default: use a small explicit worker count only after proving
isolation. Each test gets a fresh server and SQLite database; each worker reuses one browser.
Seed known records for ranking/retention tests. Do not compensate for leaked state
by choosing the current highest score plus an offset. API and browser checks of
one scenario must target the same isolated database. Measure with
`pytest --durations=10`; don't promise a speedup without a before/after measurement.

## Release and handoff

1. First safe preview: publish, check reachability, capture and inspect a screenshot,
   fix obvious visual errors, then send the building notification and share it. Continue without waiting for optional input.
2. Iterate with focused checks; preserve scope/privacy and protect costly endpoints.
3. Run `labbuild NAME` and `labbuild NAME --check`, then the full relevant suite; publish final assets (and restart backend code when
   changed), then check the visible install flow and labctl verify NAME.
4. Keep install.md short: URL, data location, reproduce commands, current evidence,
   known limits and outstanding owner checks. Detailed results belong in saved test
   reports/commit history, not repeated chronological prose in install.md.
5. Stop temporary servers/remove exact fixtures and send timestamped ready message.
6. Commit code, lockfiles and documentation; share the final URL and actual limits.

For small public leaderboards, validate and parameterize input, bound retention,
and document that client-submitted scores are not cheat-proof. SQLite backups
must include committed WAL content via the SQLite backup API/platform workflow.
A successful source commit or service restart is not evidence of remote backup.

Apps with any shared component, including a leaderboard in a personal game, need
a desktop viewport check as well as phone coverage. Record actual browser/device
evidence and untested iPhone behavior.

## Database library choice

For small SQLite apps, Python's sqlite3 with parameterized queries is sufficient.
SQLAlchemy is optional, independent of database choice; add it deliberately as lab
with `uv add 'sqlalchemy>=2.0,<3'` in app/ when Core or ORM helps the design. Commit
the updated pyproject.toml and uv.lock. Postgres includes psycopg, not SQLAlchemy.
Installing SQLAlchemy alone does not make an existing app portable between databases.

## Supported preflight and build

Launch ordinary work as lab with /srv/lab/NAME/app as the writable workspace.
Run `labpreflight NAME` (optionally `--engines chromium webkit firefox`). It checks
identity, source writes, Git, tool discovery, engine launch/version and phone/desktop
screenshot output without reading provider keys or touching runtime data. Failure
returns nonzero. Install browser downloads as lab; review missing OS packages with
an administrator. Never broaden permissions or Git safe-directory globally to fix
a session. The checker cannot inspect a coding client's sandbox policy.

Run `labbuild NAME` before offline tests; `labbuild NAME --check` fails for stale
generated workers without modifying them. Custom workers remain app-managed.
Both build and publish use the same deterministic shell generator. Publish still
regenerates from current source, so avoid edits between tests and publication.
These commands do not activate a release or restart services. Backend apps serve
public files from their working tree: use an isolated checkout for truly unpublished
changes. This is not immutable-release deployment or atomic rollback.

Keep install.md to current facts and links (aim for one screen, not a hard truncation).
Update current-state sections in place; preserve owner notes. Put release history in
CHANGELOG.md and reports/screenshots in artifacts/YYYY-MM-DD/. Keep evidence locally
with a useful index; artifacts are ignored by Git, so deliberately retain sanitized
reports elsewhere when needed for portable reproduction. Optional decisions.md holds
accepted requirements/corrections, not transcripts. Never load all history by default.

Physical-device checklist, only where relevant: install/reopen, permission denial,
microphone, sharing, wake lock, background push and offline reopening. Record actual
Android/iPhone results separately from Linux Chromium/WebKit emulation.
