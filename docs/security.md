# Privilege and failure model

## Identities

- Root owns installed helpers, `/srv/lab` and each app container, metadata,
  locks, secret files, systemd definitions, and immutable static snapshots.
- `lab` owns only each app's `app/` source tree and its home. It can request the
  fixed labctl operations through sudo. It cannot supply arbitrary Caddy text,
  executable paths, unit names, root destination paths or a lock-bypass marker.
- `labapp-NAME` runs a backend and owns its `data/` (0700). Runtime identities
  cannot write deployment code or read another runtime's data/environment file.
- Caddy serves immutable static snapshots or proxies a validated loopback port.
  It never reads a deployment-writable static tree, so index/content symlinks
  cannot expose Caddy's own certificate material through file_server.

Source files are normally world-readable (0755 directories, 0644 files). Runtime
isolation protects data and injected secrets, not confidential source code.
Never put secrets in source. The deployer can edit all app code and request named
master keys; granted secrets are therefore within its trust boundary. This is
an experiments platform for one trusted owner, not hostile multi-tenant hosting.
A public endpoint may still be reachable by another local user; applications
requiring local caller isolation need authentication too.

## Filesystem and command boundaries

Root creates container entries in root-owned parents; it never opens app-owned
files for scaffolding or static export. Fixed trusted workers run those steps as
lab. SQLite opens run as the corresponding runtime identity. App build hooks run
as lab via uv. Root recursive removal requires Python's fd-based symlink-safe
rmtree on Linux. Root JSON/env/config publication uses temporary files in a
protected parent, fsync, atomic rename, and parent-directory fsync.

Static export rejects symlinks and special files, limits output to 64 MiB/10,000
files/32 nested directories, and publishes new immutable revisions. An app name
is matched with an exact revision suffix when cleaning snapshots. The backend
opens each static path component using O_NOFOLLOW, rejects traversal, verifies a
regular final file, and streams that same descriptor to avoid path-replacement
races. Deployment-controlled backend code can intentionally change its own
behavior; it still runs as the runtime identity, never root.

The base systemd template specifies User/Group even without a drop-in and requires
the identity file. The helper checks recorded provisioning, the exact identity
file, effective systemd User/Group and env-file ownership before start/restart.
It never treats status/is-active failures as success.

## Lifecycle and durability

One root-only flock covers each complete helper operation and each backup. No
environment variable bypasses it. App ports are selected under that lock and
checked for an existing listener; unrelated software can still bind a port
before startup, so the backend health response must identify the expected app.

Create saves ownership intent before provisioning. Failure retains records and
resources rather than deleting possibly useful data. Remove stops and verifies
the service first, then disables/unpublishes, drops only a recorded Postgres
resource, removes code/data/identity, and deletes the record last. A failed stop
blocks all destructive steps. A failed later step preserves a retry record.
Corrupt/missing records are not treated as permission to delete unknown resources.

Caddy publication validates the whole generated candidate before replacing the
single imported sites file. The top-level managed config must match. Reload
failure restores and reloads the previous file; a failed rollback reload is
reported explicitly. Records and live Caddy state are separate resources, so a
crash between them is detectable/reconcilable, not a magical multi-file atomic
transaction. `labdoctor` compares disk configuration and records; it does not
query the active Caddy API. `reconcile-caddy` republishes the recorded site set.

## Limits and references

This is source-level hardening with isolated evidence, not a formal security
proof. OS package integration, real identity access, concurrent daemon state,
reboot recovery, and remote restores still need the documented installation test
phase. Root administrators and unrelated root services are trusted.

Primary references checked during this revision:

- [Caddy CLI](https://caddyserver.com/docs/command-line): stdin password hashing,
  adaptation/validation and explicit reload.
- [Caddy basic_auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth):
  configuration accepts password hashes.
- [systemd exec source documentation](https://github.com/systemd/systemd/blob/main/man/systemd.exec.xml):
  system-service default identity and environment-file behavior.
