# The lab server

A machine for building small experiments fast. Each experiment gets its own
subdomain, directory, unprivileged user, and teardown.

Read this before acting. Engineering rationale is in `SETUP.md`; troubleshooting
is in `docs/`. Keep this file short.

## Layout

    /srv/lab/<name>/          one experiment, self-contained; you may write here
    /srv/lab/.state/          resource records (JSON) — the source of truth
    /srv/lab/ports.tsv        port registry, maintained by newlab
    /etc/lab/secrets.env      master API keys — root-only, you CANNOT read this
    /etc/lab/apps/<name>.env  the keys one app was granted — root-owned
    /etc/caddy/sites/         one file per subdomain, deployed only via labctl
    /srv/lab/docs/            longer notes; read when relevant

## Creating an experiment

**Always use `newlab`. Never create a service, port, database, user or Caddy
file by hand.**

    newlab <name> --static                          static files only (default)
    newlab <name> --app                             FastAPI + service
    newlab <name> --app --db sqlite                 ... with SQLite
    newlab <name> --app --db postgres               ... with Postgres + pgvector
    newlab <name> --app --private                   ... behind HTTP basic auth
    newlab <name> --app --secrets OPENAI_API_KEY    ... granted those keys only

`newlab` records every resource before creating it and rolls back completely if
any step fails. **It creates scaffolding, not a working app, and deliberately
notifies no one.**

### Choosing the type

**Default to `--static`.** Games, visualisations, drawing tools, calculators,
sensor demos and most PWAs need no backend. Add `--app` only for: data that must
persist across devices, an API key that must not reach the browser, or work the
browser genuinely cannot do.

Use `--private` for anything Theo would not want a stranger finding. **A public
app that spends money through a provider API needs its own authentication and
rate limiting** — keeping the key server-side stops the key leaking, not the
spending.

## Privileged operations

You are the `lab` user (if you are root, stop and tell Theo — that is a
misconfiguration). Your only privilege is `sudo /usr/local/sbin/labctl`:

    labctl service <start|stop|restart|status|is-active> <name>
    labctl logs <name>
    labctl secrets-list                     names only, never values
    labctl secrets-grant KEY,KEY <name>

Everything else — database creation, Caddy deployment, user creation — happens
inside `newlab` and `labrm`. **If you need a privilege labctl does not offer,
stop and ask Theo.** Do not work around it.

## Conventions

- **Stack:** Python + FastAPI, `uv`, SQLAlchemy when there is a database.
  Front end is plain HTML/CSS/JS unless there is a real reason otherwise.
- **Dependencies** go in `pyproject.toml` and are locked in `uv.lock`. Commit
  both — `.venv` is excluded from backups and rebuilt from the lock.
- **Secrets** arrive as environment variables via systemd. Read them with
  `os.getenv`. Never hardcode, print, log or commit them.
- **Restart after editing:** `sudo /usr/local/sbin/labctl service restart <name>`
- **Logs:** `sudo /usr/local/sbin/labctl logs <name>`
- **List / diagnose:** `labs`, `labdoctor`

## Recording what exists

`install.md` is generated from the resource record. **If you create anything
outside the experiment's directory, add it to `install.md`**: cron jobs or
timers, B2 buckets, external accounts, webhooks, system packages.

System packages are shared infrastructure. Record them and tell Theo, but
**never remove a system package during teardown** — another experiment may
depend on it. Installing one is a platform change: ask first.

## Never

- **Never touch another experiment's directory, database, user or Caddy file.**
- **Never edit `/etc/caddy/Caddyfile`**, or write into `/etc/caddy/sites/`
  directly. Caddy deployment goes through `newlab`/`labrm` only.
- **Never enable `on_demand_tls`.**
- **Never put a secret in code, git, `install.md`, or a notification.**
  Basic-auth credentials live in `/srv/lab/.state/<name>.secret`; reference the
  path, do not repeat the value.
- **Never edit the installed `newlab`, `labrm` or `labctl`** — they are
  root-owned platform tools. Propose a change to Theo's `lab-server` repo instead.
- **Never delete or modify anything under `/srv/lab/` you did not create.**

## Finishing

An experiment is done when **all** of these hold:

1. The requested behaviour works, and you have exercised it — not just started it.
2. `curl -fsS https://<name>.<domain>` succeeds over public HTTPS.
3. For an `--app`: `/api/health` returns 200 and the service is `active`.
4. The layout works at phone width, and a PWA installs if that was asked for.
5. Changes are committed to the experiment's git repo.

Only then, one message:

    notify "<name> is ready" "https://<name>.<domain>"

For a `--private` app, tell Theo the credentials are in
`/srv/lab/.state/<name>.secret` — do not paste them.

## When something fails

Do not announce readiness. Leave the resource record and logs in place, and
report: what you were doing, the failing command, and its output. If creation
failed, `newlab` has already rolled back; run `labdoctor` to confirm nothing was
left behind.

## Keeping the docs current

If you hit a gotcha worth remembering, add it to the right file in `docs/` and
keep this file short. If a rule can be enforced by `newlab` instead of written
here, say so in your report — **encoding a rule in the tool beats documenting it.**
