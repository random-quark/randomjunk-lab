# Setup status template

Copy to `.local/setup-status.md`. This file is a blank checklist, not evidence that
anything is installed on the target. Keep real machine results in the local copy.
States: needed, configured, tested, deferred. Deferral requires an owner decision
and reason. Record dates, evidence and next action; never record secret values.

| Item | State | Evidence / next action |
| --- | --- | --- |
| Owner settings and target review | needed | Proactively review .local/settings.txt with owner. |
| Fresh Ubuntu 24.04 / SSH / domain / DNS | needed | Confirm target and SSH port before firewall changes. |
| Source tests and installation | needed | Follow SETUP.md; do not rerun bootstrap on an installed host. |
| HTTPS / identities / service isolation | needed | Verify a disposable experiment and labdoctor. |
| Deployment agent executable and login | needed | Choose agent; install and authenticate as lab. |
| Chromium / WebKit development tooling | needed | Run browser preflight as lab. |
| Optional AI providers / spending | needed | Select or defer; key presence is not API access validation. |
| Optional GitHub / student access | needed | Own account and repos, never copy the original owner's credentials. |
| Optional notifications | needed | Select or defer; confirm delivery on owner's device. |
| Optional email | needed | Select or defer; verify domain and authorized test delivery. |
| Optional payments | needed | Select or defer; start with test mode. |
| Backup method / bucket / repository | needed | Select or defer; one schedule, unique repository. |
| Recovery credentials stored elsewhere | needed | Owner confirms independent password-manager copy. |
| Manual backup / staged restore | needed | Verify data, not only upload success. |
| Backup schedule / retention | needed | Confirm timezone, then enable only the selected scheduler. |
| External backup monitoring / receipt | needed | Select or defer; verify check and notification delivery. |
| Reboot / maintenance | needed | Only if authorized; otherwise record explicit deferral. |
| Physical Android / iPhone checks | needed | Browser emulation is not real-device verification. |

At handoff, list every pending item and next action. Do not describe the complete
setup as finished while required integrations are untested. Optional features
may be explicitly deferred; never invent approval or infer a deferral from blanks.
