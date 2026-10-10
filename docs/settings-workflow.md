# Owner settings and resumable setup

## Required first interaction

The setup agent must proactively link .local/settings.txt and explain: “Please review
these server choices. Fill what you know; I will ask only for missing essentials.
Do not put passwords or API keys in this file.” This applies at first setup and
when resuming incomplete setup. Do not rely on the owner finding it in README.
Existing session answers remain authoritative; do not ask for them again.

First copy tracked settings.txt and setup-status.md into ignored .local/ if missing.
Never overwrite existing local answers. Use three places:

- .local/settings.txt: owner-editable non-secret choices, not committed.
- Protected secrets.env: secret input entered directly on the server, never in chat
  or Git. Use the existing protected provider/backup/notification files after import.
- .local/setup-status.md: agent-maintained progress, test evidence and next actions.

No new password file is committed or required just to start. If a staging file is
needed, create it outside the checkout with root ownership and mode 0600, give the
owner its exact path, and describe the required key names. Never print its contents.
Do not overwrite existing configured secrets. Reuse the platform's literal KEY=value
parser/import workflow; never shell-source settings or secrets. A secret topic is
also a secret. File ignore rules are defense in depth, not permission to store keys
in the checkout. Only mark credentials configured after a presence/permissions
check; verify the actual integration separately.

## Read, ask, execute, verify

1. Read .local/settings.txt, .local/setup-status.md and existing session decisions. Identify the
   actual target machine. Tracked settings are blank/suggested defaults, never proof of owner choices. Validate selected providers, domain, SSH port, timezone,
   backup endpoint and ranges before constructing commands.
2. Bring .local/settings.txt to the owner explicitly. Accept file edits OR chat answers;
   update non-secret answers in the file so the owner need not duplicate work.
3. Group missing inputs for selected features into a short question. A blank means
   unresolved, skip means explicitly omitted. Ask about backup recovery/scheduling
   before declaring setup complete. Do not demand optional accounts before doing
   independent work; keep the affected step pending.
4. Explain the concrete proposed configuration and honor already granted authority.
   This file is agent guidance, not a new automatic installer input or permission
   for spending, a reboot, or unrequested changes. The current bootstrap still takes
   its domain argument; schedule/retention changes require reviewed platform changes.
5. Perform authorized steps and record outcomes immediately. For backups, test a
   remote upload and staged restore, confirm recovery credentials are saved outside
   the host, then enable/verify only the selected scheduler and failure notifications.
   Whole-server backup uses cron; leave the alternative lab-backup.timer disabled.
6. Before every setup handoff, summarize unresolved items and the next requested
   owner action. Explicit deferrals include the reason and what resumes them.
   Keep a single current checklist rather than burying outstanding work in logs.

Editing a questionnaire does not reconfigure a running host. Historical installation
records remain historical; the target's .local/setup-status.md carries current evidence.

## Optional email

Bring EMAIL_PROVIDER, EMAIL_SENDING_DOMAIN and EMAIL_DEFAULT_FROM to the owner's
attention during setup. Do not require email or ask for email credentials when it
is unselected, skip or disabled. If requested, collect the key securely and record
verified non-secret deployment choices in /etc/lab/email.json as described in
docs/email.md. Reuse existing local choices; a blank questionnaire is not an
instruction to remove a working integration. Email availability does not authorize
adding sends to every app.
