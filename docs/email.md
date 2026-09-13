# Optional transactional email — Resend

Configure or grant email access only when the owner requests it. Email is not a
requirement for platform installation or every experiment. Blank, skip or disabled
EMAIL_PROVIDER means no new email setup; reuse existing local configuration when
present. Never disable an existing integration merely because a template is blank.

## Owner choices and local configuration

During setup, bring the optional email fields in settings.txt to the owner's
attention alongside provider choices. If selected, collect EMAIL_PROVIDER=resend,
EMAIL_SENDING_DOMAIN and EMAIL_DEFAULT_FROM. The sending domain can differ from
the platform domain. Ask for RESEND_API_KEY through protected secret entry, not
settings.txt, chat or Git. Preserve existing mail routing and verify the selected
sending domain in the provider dashboard before sending. No local SMTP server is
needed. Do not enable inbound mail as part of this setup.

After authorized setup, the administrator records non-secret choices in
/etc/lab/email.json (root:lab, mode 0640), using this schema:

```json
{
  "provider": "resend",
  "sending_domain": "notify.example.com",
  "default_from": "Example <mail@notify.example.com>"
}
```

These are placeholders, not usable defaults. This local file is agent-readable
configuration, not automatic app environment injection. Keep actual deployment
values outside the reusable repository. A default_from of null means choose an
app-specific sender under the configured domain. Apps must explicitly configure
their sender and public origin. Missing file/provider means not configured.

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
Choose an app-specific sender such as `Example <example@SENDING_DOMAIN>`
and that app's public origin. Confirm the key permits this sending domain.

Use server-side `POST https://api.resend.com/emails` with Bearer authentication
and from/to/subject/text/html fields. No SDK or MCP is required. Read the sending
domain and optional default sender from local configuration; do not assume a
particular existing app or domain is present on another machine.

## Verification and delivery

Mock sends first. A real test requires an explicitly authorized recipient; do not
consume an owner's invitation to test login. Protect sending with authentication
or bounded account-flow rate limits, escape user HTML, and use bounded retries
with a stable idempotency key for the same intended message. Never expose a public
mail relay. Keep keys and login links out of logs, screenshots and source control.

Record sanitized provider message IDs for troubleshooting. API acceptance is not
inbox delivery: confirm receipt and check spam. Apps share this key's quota and
sending reputation; app limits are not provider allowances.
