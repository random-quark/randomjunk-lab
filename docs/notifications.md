# Notifications — hosted ntfy

Decision (2026-09-07): use `https://ntfy.sh`. Expected usage is at most about
50 messages/day, not a software-enforced quota. Keep this simple: no self-hosted
notification server, extra domain, database or service to maintain.

The owner uses Android and wants iPhone compatibility. Hosted ntfy supports both
native apps; no self-hosted iOS upstream-relay configuration is needed. Experiment
websites also target both phones, but ntfy compatibility does not establish that
an experiment's browser APIs or PWA behavior work on iPhone.

## During the eventual installation phase

1. Install the ntfy app on the phone(s) and allow notifications.
2. Choose a long, randomly generated topic name and subscribe on the default
   ntfy.sh server. Keep the topic out of chat, source control, URLs in reports,
   and public documentation. No actual topic has been chosen in this review.
3. Root sets `NTFY_URL=https://ntfy.sh` and `NTFY_TOPIC=<chosen-topic>` in
   `/etc/lab/notify.env` (root:lab 0640). Use the same destination in
   `/etc/lab/backup.env` (root:root 0600) if backup alerts should reach that phone.
4. Send a single agreed setup test, confirm receipt with the app in the background
   and the phone locked, and record the outcome. Repeat on iPhone when available;
   until then, record iPhone delivery as untested.

Anonymous hosted topics are not authenticated private channels: anyone who knows
the name can subscribe/publish. Use an unguessable name and send only minimal
status and an app link. Never send credentials, private passwords, provider keys
or sensitive application content. A future need for stronger channel access
control can be addressed separately.

## Readiness policy

Once delivery is configured/tested, the owner's request authorizes one readiness
message per completed requested experiment/change. Send it only after actual
behavioral testing and `labctl verify NAME` succeed. Don't send success on mere
scaffold creation, failed verification or an incomplete task. No new permission
question is needed for every requested readiness message.

As lab, after those checks, the existing command is:

```sh
notify "tetris is ready" "https://tetris.EXPERIMENT-DOMAIN"
```

Use the real app URL. For private apps the link still requires their own login;
never include the password. Notifications are deliberately sent by the agent
at completion, not automatically by `newlab` or every service start. Backup
failure alerts use the separate root notification path already documented.

Sources: [ntfy FAQ](https://docs.ntfy.sh/faq/),
[publication and limits](https://docs.ntfy.sh/publish/).
