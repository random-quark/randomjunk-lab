# Notifications — hosted ntfy

Decision (2026-09-07): use `https://ntfy.sh`. Expected usage is at most about
50 messages/day, not a software-enforced quota. Keep this simple: no self-hosted
notification server, extra domain, database or service to maintain.

The owner uses Android and wants iPhone compatibility. Hosted ntfy supports both
native apps; no self-hosted iOS upstream-relay configuration is needed. Experiment
websites also target both phones, but ntfy compatibility does not establish that
an experiment's browser APIs or PWA behavior work on iPhone.

## Configuration

1. Install the ntfy app on the phone(s) and allow notifications.
2. Choose a long, randomly generated topic name and subscribe on the default
   ntfy.sh server. Keep the topic out of chat, source control, URLs in reports,
   and public documentation. This server already has a configured topic; never print it.
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

For each requested new experiment, send two messages, not a stream:

1. After the first successful publication, reachability check, and screenshot
   capture/inspection (fix obvious visual errors first), send a building
   link even if functionality is incomplete. Keep privacy and costly endpoints safe.
2. After behavioral testing and labctl verify NAME pass, send the ready message.

Use machine-local HH:MM in the title; inspect `date '+%H:%M %Z'` if unsure of its
zone. Preserve the URL-only body and Copy link/Open in browser actions. As lab:

```sh
notify "Movie Wheel · started $(date +%H:%M) · building" "https://movie-wheel.EXPERIMENT-DOMAIN"
# Only after full verification:
notify "Movie Wheel · ready $(date +%H:%M)" "https://movie-wheel.EXPERIMENT-DOMAIN"
```

No new permission is needed. Record sends to avoid duplicates after context
switches. Send nothing between them while the owner is active; one extra useful
milestone is acceptable if they are away during a long build. Republish/restart
alone never triggers another notification. Changes to existing experiments need
a completion notification, not a fictitious new first-publish notification.

Use the real app URL. For private apps the link still requires their own login;
never include the password. Notifications are deliberately sent by the agent
at completion, not automatically by `newlab` or every service start. Backup
failure alerts use the separate root notification path already documented.

Sources: [ntfy FAQ](https://docs.ntfy.sh/faq/),
[publication and limits](https://docs.ntfy.sh/publish/).

## App-link notification format

Use `notify "Title" "https://app.example.com"` for app readiness. The message body
contains only the URL, with Copy link and Open in browser buttons. No custom click
destination is set, so the notification opens normally in ntfy. Link text inside
ntfy still follows the client's link behavior; the Copy link button copies exactly
the URL. The owner confirmed both buttons work on Android.

Legacy `notify "Title" "Description" "https://app.example.com"` calls remain valid,
but the explicit URL replaces the body to preserve the same format. Put meaningful
context in the title. Plain-text messages without a URL retain their body and have
no actions. Copy support varies by client/version; real iPhone behavior is untested.
