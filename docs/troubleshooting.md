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
