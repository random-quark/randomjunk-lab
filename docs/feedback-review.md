# Applied feedback — 2026-09-09

Source: owner's /home/lab/platform-feedback/2026-09-09-platform-feedback.md.
The owner authorized the reviewed changes, including the adjustments discussed.

| Item | Applied decision |
| --- | --- |
| 1 Referents | Research/inspect first; state concrete assumptions, proceed without waiting for optional feedback. |
| 2 Early visuals | Early safe building preview and user-visible screenshot; use available tools rather than require SendUserFile. |
| 3 Environment | Brave/Chrome Android; shared apps also target iPhone Safari/desktop. Never silently remove previously requested scope. |
| 4 Done checklist | Visible install flow provided by both templates; manifest/icons/offline/test/documentation checklist. |
| 5 Direction | Assert a fixed landmark, direction and relevant axis, not magnitude alone. |
| 6 Duration | Explicit bounded adapter/browser clock; no guessed model names/eval helper. All tests included by default, optional small-count xdist. |
| 7 Helpers | labshot and labdev; common fixtures for both app kinds; generated SW hash from preserved template. |
| 8 Notifications | Two timestamped messages for new experiments, building then verified ready; preserve copy/open buttons. |
| 9 Gotchas | Own-process cleanup, no pkill -f; model velocity timestamps rather than a claimed fixed Playwright event rate. |
| 10 Documentation | Short factual install.md with current evidence; reports/commits hold detail. |

Limits: labdev automates static/SQLite/no-DB apps, not Postgres provisioning. It
cannot clean up after SIGKILL or power loss. labshot captures initial load and
errors, not interactive behavior or actual phone installation. Existing custom
workers and apps are preserved; only new scaffolds get these defaults. Automatic
hashing is not a fully atomic versioned backend asset deployment. No promise of
sub-20-second suites is made; timing improvements depend on each app's tests.

## Scaffolding in practice — 2026-09-09

Adopted user-initiated installation without timed dialogs, matching shell tests,
per-test server/SQLite isolation with a shared browser, and named bounded-model
failures. Rejected top-score-plus-offset as a substitute for isolation. Adopted
visual-style reference research, screen-relative sensor guidance, inspected
screenshots before preview notifications, and desktop checks for shared components.
Existing experiments are not migrated. Reported build/test speedups are anecdotal,
not platform benchmark guarantees.
