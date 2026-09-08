# Troubleshooting revision 3

`labs` summarizes status. `labdoctor` performs read-only reconciliation and
continues past bad records; it is not a public-readiness certificate. Installed
commands require the protected v3 layout. No commands here were run against live
services during source review.

- **create-failed / prepared:** resources are retained. Inspect the record and
  app journal, fix the cause, then publish only if preparation completed. If
  abandoning the app, use labrm; no --force metadata bypass exists.
- **verification-pending:** run `labctl verify NAME` after checking DNS, reachability,
  certificate issuance and the service. Private probes use stored credentials.
- **environment-pending:** a grant update was interrupted. Desired grants are in
  the record. Reissue the grant or publish to regenerate the environment, then
  restart and verify. Never hand-edit generated env files.
- **removal-failed:** stop failure prevents destructive steps; fix the service
  problem before retrying. Later cleanup failures retain a record. Do not delete
  data manually to hide a failed stop.
- **corrupt/missing record:** restore protected metadata from a checkpoint and
  reconcile actual resources as administrator. Don't invent permission to remove
  unrecorded resources. A repeated already-clean removal is harmless.
- **Caddy mismatch:** inspect why the generated file and records differ. A failed
  reload restores the prior file; a failed rollback reload needs administrator
  action. `labctl reconcile-caddy` republishes recorded sites under the lock.
  Doctor checks files, not the active admin API.
- **static edit not visible:** publish it. Caddy serves an immutable snapshot.
  Symlinks/special files or more than 64 MiB/10,000 files/32 levels are rejected.
- **backend won't read code:** code/venv files must be readable/traversable by the
  runtime. Build as lab with system Python; don't use a home-only interpreter.
  Secrets are injected, not read through python-dotenv.
- **backup failure:** inspect lab-backup.service and its failure notification.
  Missing config, enumeration, snapshots, upload, retention and check errors fail
  the job. Incomplete local generations are not reused. Keep independent backup
  credentials and test actual recovery; a successful upload alone is insufficient.

Do not paste raw logs, env files, DB URLs, private passwords or dump contents.

## Development helper and browser pitfalls

- Never use pkill -f from the agent shell: its pattern may match the agent's own
  command/process tree. Retain process handles/PIDs; labdev owns and terminates
  its own process group. SIGKILL/power loss cannot run cleanup: inspect leftover
  /tmp/labdev-* and exact process ownership before cleanup.
- Playwright input timing differs from human touch. Velocity-sensitive behavior
  needs deterministic timestamp/model tests plus a separate event-wiring check.
  Do not mistake a slow automation gesture for proof of broken physics.
- labshot returns nonzero for console/page errors, failed requests or HTTP errors.
  A screenshot can still be produced on failure: inspect report.json. It observes
  initial load, not later interaction. Private sites may return 401: use an app
  test with an explicitly authenticated context; don't put passwords in URLs.
- A custom worker is not overwritten. New template apps edit sw.template.js then
  publish to regenerate sw.js. For backend source changes, restart as well.
- Install native Playwright Chromium as lab after uv sync. Missing OS libraries
  are an administrator task using reviewed apt packages, never lab-owned code as root.
