# Changelog

## Revision 2 — after external review

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
