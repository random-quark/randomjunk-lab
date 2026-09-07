# Building and finishing an experiment

Lessons from Neon Blocks, 2026-09-07. Use the existing lab/VPS workflow for this
owner's experiments. Domain and hosted ntfy are already configured; ask only for
missing resources required by the actual app. No provider keys are needed for a
local game. Do not redirect an experiment to another hosting service by default.

## Start with a short preflight

As lab, select static or backend plus the smallest suitable database. Use
`newlab NAME --app --db sqlite --prepare-only` for a small persistent app;
use `--static --prepare-only` when no backend is required. Preparation creates
resources without publishing a placeholder. The installed helper remains the
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

For a PWA, test first-visit install guidance, dismissal and reopening, actual shell
caching, offline reload/play, and reconnect behavior. An install button must use
native prompting only when the browser exposes it; provide manual instructions
otherwise. iPhone installation requires its own device check. Start sound from a
user gesture and silence it on pause/background. Browser policy references:
https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event

Offline writes need a bounded persistent queue and idempotent server handling.
Do not rely solely on the online event: transient failures can outlast it. Retry
pending writes on returning to the app and on a bounded schedule while online;
stop requests when there is no work. Test offline-to-online recovery directly.
Version shell caches and avoid mixing a new shell into a running game.

## Release and handoff

1. Record the commands, dependencies, data location, tests and limits in install.md.
2. Commit and publish with `sudo /usr/local/sbin/labctl publish NAME` as lab.
3. Check live behavior and run `sudo /usr/local/sbin/labctl verify NAME`.
4. Stop temporary servers and remove exact test fixtures. Preserve useful evidence.
5. Send one configured ntfy readiness notification with the real URL after success.
6. Record the result and hand over the link plus any real-device checks still needed.

For small public leaderboards, validate and parameterize input, bound retention,
and document that client-submitted scores are not cheat-proof. SQLite backups
must include committed WAL content via the SQLite backup API/platform workflow.
A successful source commit or service restart is not evidence of remote backup.
