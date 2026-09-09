# Local development tools

Run as lab, from app/:

```sh
uv sync --locked --python /usr/bin/python3
.venv/bin/playwright install chromium
.venv/bin/python tools/labdev.py
# Separate terminal, using the printed loopback URL:
.venv/bin/python tools/labshot.py http://127.0.0.1:PORT --out artifacts/preview
.venv/bin/pytest
```

labdev binds an OS-selected port until the child inherits it. Ctrl-C/SIGTERM stops
only its process group and removes its temporary SQLite DB. It never imports
production credentials. It supports static and SQLite/no-DB apps; Postgres needs
an explicit isolated test database and is refused by the automatic fixture.
SIGKILL or host failure cannot run cleanup; /tmp/labdev-* may need later inspection.
No live reload is assumed: restart after backend code changes. Public assets are
read from disk; use a fresh browser context to avoid old SW caches during tests.

Browser fixtures: page (fresh context), base_url and app_server (fresh server and
temporary DB for EACH test), browser (one reusable browser per worker).
No tests are silently excluded. Optional: `pytest -m 'not slow'` during iteration;
run plain `pytest` before handoff. Use xdist only after independence is established,
with an explicit small worker count, e.g. `pytest -n 2`. Each worker gets a separate
server, port and DB. Default fixtures also isolate tests within a worker. Seed
known records for ranking/retention tests; fixed scores are appropriate with known
data. Do not mask pollution by repeatedly choosing current-highest + 1000.
API test clients must use the same isolated test DB if mixed with browser checks.
Do not reset arbitrary app tables or production data through a generic fixture.
If deliberately overriding to session scope for read-only tests, document that
shared state and provide an app-specific reset/seed strategy for mutations.

For deterministic model animation, install an explicit adapter:

```python
fast_forward('''() => {
    window.labTestStep = dt => {
        window.myTestModel.update(dt);
        return window.myTestModel.state === 'idle';
    };
}''')
```

The helper fails when its step limit is exhausted. Provide a deliberate testing
adapter; it does not guess globals. For timers/RAF, use Playwright's clock instead
of mutating production durations. Assert direction against a fixed landmark, not
just that a value changed. Keep real-time checks only where timing itself matters.
Reports and screenshots can contain app content/errors; review before sharing.
labshot observes page load, not arbitrary later interactions or full device behavior.
