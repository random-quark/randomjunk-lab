# {{TITLE}}

FastAPI scaffold for {{NAME}}. Code lives in app/; persistent data lives in the
sibling data/ directory. Settings and secrets arrive through systemd. Do not add
a production .env or put provider secrets in source.

Use uv with the committed lockfile. Postgres requires `uv sync --locked --extra
postgres --python /usr/bin/python3`; other variants omit the extra.

`/api/health` is liveness only. Test database connectivity and application
behavior separately. Static routing rejects traversal, symlinks and special files;
missing assets return 404 while HTML navigation can use the SPA shell.

After edits, restart through labctl and verify. Record external resources in
install.md. Phone/PWA behavior must be tested on the actual client when needed.
