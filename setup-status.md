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
| Stripe credentials | configured | 2026-09-16: test-key presence and root-only permissions verified in /etc/lab/stripe.env; API access untested, no app grants or webhook setup. |
| AI credentials | configured | OpenAI/Gemini/Replicate key presence checked; OpenRouter added 2026-09-15 (presence/0600 checked, API untested); no values recorded here. |
| AI access / spending | needed | Agree test budget, verify intended model access, and distinguish provider spending controls from preferences. |
| B2 credentials / endpoint | tested | 2026-09-17: restricted credentials initialized and accessed the private server1 repository; values remain outside Git. |
| Backup schedule / retention | configured | Whole-server root cron installed for 03:30 Europe/Berlin with 7 daily, 4 weekly and 6 monthly retention. Older lab-backup.timer remains disabled. |
| Recovery password / access | tested | Owner confirmed an independent password-manager copy; repository unlock and staged restore passed. |
| Remote backup / restore drill | tested | 2026-09-17: encrypted B2 upload, 1% data check and byte-identical `/etc/hostname` restore passed. |
| Scheduled backups / failure alerts | configured | 2026-10-01: daily cron success observed; Healthchecks start and success accepted on manual snapshot 55849e3e. Failure and network handling passed mocked tests. One-day period/one-hour grace and email selected in owner screenshot; owner email receipt still unverified. |
| Reboot / boot-service review | needed | Existing cloud-init and network wait failures; agree maintenance window and verify recovery. No reboot authorized by blank settings. |
| Android game PWA / audio | needed | Browser emulation passed; owner device installation and sound checks outstanding. |
| iPhone PWA / audio | needed | Actual device installation/play/audio checks outstanding. |

## Completion rule

Do not describe the whole setup as complete while required rows remain needed or
merely configured. Say which part is ready and surface the outstanding items.
Ask whether optional work should be completed now or explicitly deferred; do not
silently classify it as optional/deferred to finish the checklist. An individual
app can be ready while platform backup setup remains incomplete.
