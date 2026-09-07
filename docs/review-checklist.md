# R1–R15 source checklist

The detailed `labserver-revised-review.md` was not provided. This mapping uses
only the pasted summary. Individual numbering within R6/R9/R11–R14 is unknown;
those topics are grouped below rather than assigned invented numbers.

“Implemented” means source changes plus the stated isolated evidence, **not**
verification against installed infrastructure. No finding is declared fully
production-verified in this phase.

| Reference | Source status | Evidence / remaining validation |
| --- | --- | --- |
| R1 | Implemented: base runtime User/Group, mandatory identity/environment, effective identity checks | Unit/source assertion; unprovisioned and effective-root refusal tests. Real systemd start refusal deferred. |
| R2 | Implemented: runtime-user SQLite API snapshots, encoded URI path, hashed manifest names | Real unusual filenames, WAL/committed-state consistency and integrity checks. Root backup invokes fixed runtime worker; complete backup daemon integration deferred. |
| R3–R5 | Implemented: readable code/venvs, root-only injected env, no dotenv read; immutable Caddy static snapshots; durable merged grants; psycopg optional dependency/lock | Grant preservation and failed-grant tests, snapshot permissions/serving path tests, declared driver import. Actual uid permissions and Postgres connections deferred. |
| R7 | Implemented boundary change: root-owned container/metadata, unprivileged workers, fd-safe removal | Root-container link refusal, child symlink deletion safety, atomic link replacement and static export tests. Adversarial real-identity stress tests deferred. |
| R8 | Implemented: structured-only Caddy, whole candidate, protected lock, replacement/rollback, static snapshots | Four real Caddy parser variants; simulated validation/reload failures; failed republish preserves prior revision. Live reload/rollback deferred. |
| R10 | Implemented: fd-based no-follow static serving in every branch | Real FastAPI requests for traversal/index/fallback symlinks and path replacement. |
| R15 | Unsafe implicit upgrades removed; old installs refused and migration procedure documented | Fresh-only guard inspected and source parsed. Automated old-draft migration deliberately not implemented; an actual old-install inventory/migration remains an administrator task. |

R6/R9/R11–R14 topics:

| Topic | Source status | Evidence / remaining validation |
| --- | --- | --- |
| Teardown | Stop/verify first; recorded DB only; retry metadata retained; record last | Failed-stop blocks data/DB deletion, static removal avoids Postgres, repeated removal, safe link deletion. Live stop/userdel/DB failure matrix deferred. |
| Restore | New isolated staging; stopped prepare-only provisioning; source/data/lock restored before publish | Real SQLite staged restore with stale-WAL removal; static source and opaque Postgres artifact staging; prepare-only does not start/publish. Actual pg_restore, remote restic and full activation deferred. |
| Readiness / notification | Authenticated private probes, no redirect/proxy credential forwarding, identity-specific liveness, explicit HTTP state; no automatic success notifications | Private-credential forwarding to probe and pending-state tests. External notifications require deliberate use after behavioral testing. Live TLS/DNS/private auth deferred. |
| Locking | Root-only full-operation flock, no marker bypass; backup uses same lock | Real cross-process exclusion despite LAB_LOCK_HELD=1. Installed concurrent lifecycle/backup stress deferred. |
| State writes | fsync/atomic replace, resource intents, failed-create retention, grant desired-state journal | Interrupted replacement preserves old JSON; interrupted creation retains intent; corrupt records block mutation. Real power loss/reboot deferred. |
| Backup failures | Explicit exception path; producer exit checks; unique generations; manifest only after snapshots; no unmatched drop-in glob | Missing-config failure path tested with notification double; SQLite API tests. Remote retention/upload/check failures and notification delivery deferred. |
| Reconciliation | Continues past corrupt records; checks code/data, services, identities, env/credential files, static revisions, Postgres resources and generated Caddy file | Corrupt-record continuation and source inspection. Active Caddy API, mounted permissions and live DB/port inventory still need integration; doctor is not a full readiness audit. |

See verification.md for the exact current results and the deferred acceptance
matrix. Root trust and deployer access to granted secrets are documented in
security.md; the earlier absolute secret-boundary claims were removed.
