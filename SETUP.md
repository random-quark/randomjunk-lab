# SETUP.md — how the box is put together, and why

`bootstrap.sh` does the work. This file explains the reasoning, the manual steps,
and the tests that must pass before this is trusted unattended.

## Before you run it

1. **Buy the domain**, then add exactly one DNS record:

       Type: A    Host: *    Answer: <server IP>    TTL: 300

   Any subdomain with no record of its own resolves here. Explicit records always
   win, so a wildcard never breaks an existing name.

2. **Ports 80 and 443 must be reachable.** Both: HTTP-01 uses 80, TLS-ALPN-01
   uses 443, and Caddy may use either.

3. **If the VPS has two disks**, format and mount the second at `/srv` before
   bootstrapping. `bootstrap.sh` does not do this.

## Running it

    sudo git clone <this repo> /opt/lab-server
    sudo chown -R theo:theo /opt/lab-server
    cd /opt/lab-server
    sudo ./bootstrap.sh sand.box

Keep the repo at `/opt/lab-server` owned by you — not under `/root`, so you can
edit it without sudo, and readable-but-not-writable by `lab`, which is exactly
the relationship `CLAUDE.md` describes: agents propose changes to the platform,
they do not edit the installed tools.

Idempotent. It will not overwrite files under `/etc/lab` that already exist.

## Where everything lives

Standard locations, so nothing is in a surprising place:

| Path | Owner | What |
|---|---|---|
| `/opt/lab-server/` | you | this repo — the source of truth, pushed to GitHub |
| `/usr/local/sbin/labctl` | root | the only privileged tool |
| `/usr/local/bin/` | root | `newlab`, `labrm`, `labs`, `labdoctor`, `notify`, `lab-backup` |
| `/usr/local/lib/lab/` | root | shared shell library and the template renderer |
| `/usr/local/share/lab/templates/` | root | app skeletons `newlab` copies |
| `/etc/lab/` | root | secrets, notification and backup config |
| `/etc/caddy/sites/` | root | one file per subdomain |
| `/etc/systemd/system/lab-app@*` | root | the unit template and per-app drop-ins |
| `/srv/lab/` | `lab` | experiments, `.state/`, `CLAUDE.md`, `docs/` |
| `/srv/lab/<name>/data/` | `labapp-<name>` | the only directory an experiment may write |

Nothing the platform installs lives in a home directory, so the machine can be
rebuilt from this repo plus `/etc/lab` and a restic snapshot.

## Who runs what

| Identity | Runs |
|---|---|
| `root` | `bootstrap.sh` once, `labctl` via sudo, the nightly backup timer |
| `lab` | `newlab`, `labrm`, `labs`, `labdoctor`, `notify` — **and Claude** |
| `labapp-<name>` | one experiment's own process |

**Run Claude as `lab`, never as root:**

    ssh theo@<box>
    sudo -u lab -i
    claude

Launching it as root collapses every boundary here in a single step — the
sudoers rule, the per-app users and the root-only secrets file all stop meaning
anything.

## Decisions worth knowing

### One privileged entry point

The `lab` user has exactly one sudo right: `/usr/local/sbin/labctl`. Everything
privileged — creating the per-app user, the database, the Caddy site — happens
inside that root-owned script, which validates its own arguments and derives
every resource name from a checked app name.

This replaces per-command sudoers rules with argument globs. `systemctl stop
lab-app@*` looks narrow but also matches `lab-app@x.service unrelated.service`,
because sudoers wildcards match spaces.

### Identity separation

Three identities, deliberately:

| Identity | Is | Can |
|---|---|---|
| `lab` | the agent / deployment identity | write `/srv/lab`, run `labctl` |
| `labapp-<name>` | one experiment's runtime | read its own directory, write its `data/`, read only the secrets it was granted |
| `root` | the platform | everything, including backups |

`ProtectSystem=strict` limits writes, not reads — so a single shared runtime user
would let any experiment read every other experiment's credentials. Hence one
user per experiment.

Backup credentials are never exposed to `lab` or to any experiment: they can
delete the backup repository, which is the one thing that must survive a mistake.

### Secrets by grant, not by default

`/etc/lab/secrets.env` is root-only. Agents cannot read it. They see key *names*
via `labctl secrets-list` and request them:

    newlab weather --app --secrets OPENAI_API_KEY
    labctl secrets-grant TAVILY_API_KEY weather

Only the granted keys are copied into `/etc/lab/apps/<name>.env`, owned by root
and readable by that app's user alone.

### Caddy: explicit deployment, not `--watch`

Deployment is stage → validate the whole candidate config → install → reload →
roll back if the reload fails. `--watch` was tried and dropped: Caddy documents it
as a local-development feature, and in v2.10.2 the watch loop exits on a parse
error — so one partially written file silently stops automatic reloading, and you
find out much later. Explicit deployment costs the agent nothing, since it is
inside `newlab` either way.

Caddy's admin API is on a root-only Unix socket. On the default `localhost:2019`,
any local process — including an experiment — can reconfigure the proxy.
Restricting `systemctl` does not restrict the admin API.

### Certificates

Per-site certificates, issued automatically. Two corrections to common belief:
certificate management starts when a hostname appears in the configuration, not
on the first visit; and Caddy will use HTTP-01 or TLS-ALPN-01, which is why both
ports are open.

**Rapid creation can still exhaust Let's Encrypt's limit** of 50 certificates per
registered domain per seven days (replenishing gradually). If you are testing the
platform itself rather than building experiments, point Caddy at the staging
issuer first. Preserve `/var/lib/caddy` across rebuilds — it holds the
certificates and the ACME account key, and it is in the backup set for that reason.

`on_demand_tls` is deliberately off: with a wildcard DNS record it would let
anyone trigger unlimited issuance.

### Postgres and SQLite

SQLite is the default: a file inside the experiment, so the experiment stays
self-contained. Postgres is installed and ready for concurrent writers,
background workers, or `pgvector`.

**Having Postgres preinstalled removes installation work, not migration work.**
Moving an existing SQLite app to Postgres still means schema differences, data
transfer and application changes. If you suspect something will grow, start it on
Postgres.

All provisioning runs as the postgres superuser inside `labctl`. Under PostgreSQL
16 a non-superuser creating a database owned by another role needs `SET ROLE`
rights it does not have by default, and `CREATE EXTENSION vector` requires
superuser outright. The `lab` role exists only for read-only `psql`.

### No Redis

Postgres handles queues (`SELECT ... FOR UPDATE SKIP LOCKED`) and sessions at
this scale.

### Nothing precious lives here

The VPS is expendable. Credentials are not, which is what the identity separation
is protecting.

## Manual steps after bootstrap

### 1. `/etc/lab/notify.env`

    NTFY_TOPIC=lab-$(head -c 9 /dev/urandom | base64 | tr -d '/+=')

On public ntfy the topic name is the only secret. Subscribe on your phone.

### 2. `/etc/lab/secrets.env`

The API keys you want available. **Set a hard spending cap on each at the
provider** — an unattended agent loop overnight is expensive.

Note that hiding a key server-side stops the key leaking, not the spending: a
public app that calls a paid API needs its own authentication and rate limiting.

### 3. `/etc/lab/backup.env` and `restic init`

Create a B2 bucket and application key, fill in `B2_*`, and choose a
`RESTIC_PASSWORD` you store somewhere safe — **lose it and the backups are
unreadable.** Then:

    set -a; . /etc/lab/backup.env; set +a
    export RESTIC_REPOSITORY="s3:${B2_ENDPOINT}/${B2_BUCKET}/lab"
    export AWS_ACCESS_KEY_ID="$B2_KEY_ID" AWS_SECRET_ACCESS_KEY="$B2_APP_KEY"
    restic init

The nightly timer is already enabled. About $0.12/month at 20 GB.

### 4. SSH hardening

`bootstrap.sh` deliberately does not touch your SSH config. Once key login is
confirmed, set `PasswordAuthentication no` and `PermitRootLogin prohibit-password`.

### 5. Snapshot

Take the VPS snapshot now, with the platform installed and no experiments. It is
not a backup, but it is a fast way back to a known-good machine.

## Validation matrix — run before trusting this unattended

On a disposable Ubuntu 24.04 machine with real systemd and Postgres. None of this
was exercised by the review, which was static inspection plus mocked fragments.

1. Create and remove: public and private static sites; `--app` with no database,
   with SQLite, and with Postgres.
2. Confirm pgvector is genuinely usable when requested (`SELECT '[1,2,3]'::vector`),
   not merely reported as installed.
3. Confirm `labctl` rejects extra arguments, unrelated units, path traversal,
   trailing-hyphen names, and reserved names — and still allows intended actions.
4. Confirm one app's user cannot read another app's `/etc/lab/apps/*.env`, cannot
   connect to Postgres as `lab`, and cannot reach the Caddy admin socket.
5. Inject a failure after each creation step; confirm rollback and retry work.
6. Kill `newlab` mid-run and reboot; confirm `labdoctor` sees the partial state
   and `labrm --force` clears it.
7. Create and delete two experiments concurrently; confirm no port collision and
   a consistent Caddy config.
8. Reboot: enabled apps return. Remove them, reboot again: they stay removed.
9. Deploy a deliberately invalid site file; confirm the previous working config
   survives and Caddy keeps serving.
10. Restore a static site, a SQLite app and a Postgres app onto a fresh machine —
    including dependencies from `uv.lock`, service enablement, database ownership
    from the globals dump, and working HTTPS.
11. On your actual phone: install the PWA, update it, use it offline, and check a
    private app's authentication. Then reuse a subdomain for a different app and
    confirm the old service worker does not resurrect the old one.
12. Confirm a notification arrives only after an app genuinely works, and that a
    forced backup failure alerts.

## Troubleshooting

See `docs/troubleshooting.md` and `docs/recovery.md`.
