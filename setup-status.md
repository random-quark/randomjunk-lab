# Setup status — agent maintained

This is the current status for randomjunk.dev. settings.txt contains owner
preferences; protected server files contain secrets. This checklist contains no
secret values. Installation history is evidence, not the authoritative current
list of unfinished work. On a different machine start every verification anew.

Allowed states: needed, configured, tested, deferred. Deferred requires an explicit
owner decision and a reason; missing credentials do not mean deferred. Record the
date, evidence and next action after each setup step. Never infer tested from
configured. Review unresolved rows with the owner at each setup handoff.

| Item | State | Evidence / next action |
| --- | --- | --- |
| Owner settings review | needed | New settings.txt introduced; bring it to owner and review remaining blanks/defaults. Previously accepted decisions need no repeat approval. |
| Domain / DNS / HTTPS | tested | 2026-09-07: wildcard/apex DNS and public app HTTPS passed; confirm target IP for another machine. |
| SSH / firewall / lab identities | tested | 2026-09-07 installation evidence in docs/installation.md. |
| Hosted ntfy | tested | Owner confirmed Android receipt; readiness sends succeeded. iPhone delivery not yet checked. |
| Platform GitHub | tested | Private random-quark/randomjunk-lab pushed as lobodelmar; remote commit checked. |
| Experiment GitHub access | needed | Decide restricted access for lab separately; root GitHub credentials are not shared with lab. |
| Deployment agent executable | tested | 2026-09-07: fresh lab login resolves /home/lab/.local/bin/claude; version 2.1.263 verified. |
| Deployment agent login | needed | Owner must launch Claude as lab and complete interactive account login. Root login does not establish lab access. |
| AI credentials | configured | OpenAI/Gemini/Replicate key presence checked; OpenRouter added 2026-09-15 (presence/0600 checked, API untested); no values recorded here. |
| AI access / spending | needed | Agree test budget, verify intended model access, and distinguish provider spending controls from preferences. |
| B2 credentials / endpoint | needed | Bucket, endpoint, key ID and application key missing. Collect securely. |
| Backup schedule / retention | needed | Confirm settings.txt proposals and timezone; current timer defaults to server-local 03:30. |
| Recovery password / access | needed | Generate or collect restic password securely; confirm independent off-server recovery copy. |
| Remote backup / restore drill | needed | Local dummy restore passed only; upload and staged B2 restore still required. |
| Scheduled backups / failure alerts | needed | Timer disabled until successful remote backup/restore; verify alert delivery and next run when enabled. |
| Reboot / boot-service review | needed | Existing cloud-init and network wait failures; agree maintenance window and verify recovery. No reboot authorized by blank settings. |
| Android game PWA / audio | needed | Browser emulation passed; owner device installation and sound checks outstanding. |
| iPhone PWA / audio | needed | Actual device installation/play/audio checks outstanding. |

## Completion rule

Do not describe the whole setup as complete while required rows remain needed or
merely configured. Say which part is ready and surface the outstanding items.
Ask whether optional work should be completed now or explicitly deferred; do not
silently classify it as optional/deferred to finish the checklist. An individual
app can be ready while platform backup setup remains incomplete.
