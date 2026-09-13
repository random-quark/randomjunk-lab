# Transactional email — Resend

Hosted Resend is configured for outbound email from `notify.randomjunk.dev`.
No local SMTP server is required. The owner reported domain verification; current
DNS, key scope, quota and billing must be checked in the Resend dashboard when needed.
Receiving is disabled according to the handoff; preserve existing mail routing.

## Connect a backend

The shared key is `RESEND_API_KEY` in root-only `/etc/lab/secrets.env`. As lab:

```sh
# New experiment:
newlab NAME --app --secrets RESEND_API_KEY --prepare-only
# Existing experiment:
sudo /usr/local/sbin/labctl secrets-grant RESEND_API_KEY NAME
sudo /usr/local/sbin/labctl service restart NAME
```

Grants merge with existing grants. Systemd injects generated app environment values;
never copy master keys, edit generated env files or create a production .env.
Choose an app-specific sender such as `Example <example@notify.randomjunk.dev>`
and that app's public origin. Confirm the key permits this sending domain.

Use server-side `POST https://api.resend.com/emails` with Bearer authentication
and from/to/subject/text/html fields. No SDK or MCP is required. Reference pattern:
`/srv/lab/yamyam/app/email_auth.py`; public branding is yumyum but its deployment
name is yamyam. Sender and public URL are app-specific constants, not platform defaults.
Reuse the sending pattern, not its book/account schema.

## Verification and delivery

Mock sends first. A real test requires an explicitly authorized recipient; do not
consume an owner's invitation to test login. Protect sending with authentication
or bounded account-flow rate limits, escape user HTML, and use bounded retries
with a stable idempotency key for the same intended message. Never expose a public
mail relay. Keep keys and login links out of logs, screenshots and source control.

Record sanitized provider message IDs for troubleshooting. API acceptance is not
inbox delivery: confirm receipt and check spam. Apps share this key's quota and
sending reputation; app limits are not provider allowances.

Source: 2026-09-13 Resend handoff in /home/lab/platform-feedback/. Platform review
confirmed key presence, yamyam grant and reference-file existence without exposing
values. No test email was sent; dashboard/DNS and delivery were not reverified.
