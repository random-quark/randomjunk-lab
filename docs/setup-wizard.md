# Private setup form

The working form is in `tools/setup-wizard.py` and `tools/setup-ui/`. It collects
owner choices and credentials before or after core installation. It does not run
bootstrap from a web request. SETUP.md remains the agent's installation entry point.
The form uses Python's standard library, with no Node build or Python dependencies.

## What the owner sees

- **Popular services:** hosted ntfy.sh, Replicate and OpenAI, in that order.
  Replicate covers models available on Replicate, not every model everywhere.
- **Your lab:** name, domain, SSH port, backup timezone, desktop agent and an
  optional budget preference for later API tests (not an enforced cap).
- **More connections:** Backblaze B2 / Restic, Healthchecks.io, Gemini, Anthropic,
  OpenRouter, Resend, GitHub username and Stripe test credentials.
- **Finish:** selected integrations, untested keys and explicit deferrals.

No paid provider is a minimum requirement. The owner must choose ntfy or defer
notifications, and choose backups or explicitly defer them. For selected ntfy,
phone receipt must be confirmed before finishing. No key is required for ntfy:
the form fixes the service to https://ntfy.sh and generates a new random topic.
No custom server is offered. The topic is a secret subscription destination, not
an authenticated channel; anyone who learns it can read or publish messages.

The only outbound request the form makes is the owner's **Send test notification**
action, with a fixed, nonsensitive message. It follows no redirects and permits
one test per 30 seconds. **It arrived on my phone** records owner confirmation;
an HTTP success alone does not. No live notification is sent by automated tests.
ntfy supports configured app/backup alerts, not automatic reporting of every agent
event. External monitoring is needed to detect missed check-ins while the VPS is offline.

API fields show **Saved · untested**. There is no paid inference or claim of billing,
model access, domain readiness or delivery just because a credential was saved.
Apps still need an explicit secret grant and a chosen model. Desktop-agent login
is separate from the API credentials that hosted apps use.

## Start on a fresh or existing server

Use a reviewed, administrator-owned checkout. Never execute a deployment-user-owned
copy of this script as root. The agent prepares a dedicated unprivileged account
once (as administrator):

```sh
getent passwd labsetup >/dev/null || sudo useradd --system --user-group --home-dir /var/lib/lab-onboarding --shell /usr/sbin/nologin labsetup
```

The account must have no privileged groups, sudo permissions or other duties.
Do not use the shared `nobody` account. The root launcher reads static assets and
then permanently drops all groups and privileges to `labsetup` before binding any
socket or accepting input. The web process cannot run privileged configuration.
If launched by a non-root administrator, use a private state directory outside the
checkout that the account owns; the process retains that account's privileges,
so prefer the dedicated account on a real VPS.

In a terminal **on the owner's laptop**, open a tunnel (use the real SSH user,
address, key and port; a Tailscale address works):

```sh
ssh -L 8765:127.0.0.1:8765 ADMIN@SERVER
```

Then, **in that SSH terminal**, from the checkout on the server:

```sh
sudo /usr/bin/python3 -I tools/setup-wizard.py serve
```

Open **http://127.0.0.1:8765** in the laptop's browser and paste the temporary setup
code from the terminal. Do not put that code in agent chat. Keep the SSH terminal
open during setup. No tmux, public HTTP port or public deployment is required.
If the connection closes, restart the command to resume saved choices with a new
code. Unsaved fields are lost. Codes expire after one hour; restart to renew.
Use the same local and remote port; for another port, change both the tunnel and
`serve --port PORT`. The server intentionally accepts only loopback Host/Origin.

The process stores state outside Git in `/var/lib/lab-onboarding/setup.json`
(directory 0700, file 0600, owned by `labsetup`). On restart, already saved API
keys are not sent back to the browser. Blank inputs preserve them; a new value
replaces them. The authenticated owner can deliberately reveal the ntfy topic
through **Show subscription details**, since it is needed to subscribe.

## Agent handoff: stage, install, apply, verify

After **Finish & close setup**, all API access for that running session closes.
Stop the web process with Ctrl+C. Back in an administrator session, run:

```sh
sudo /usr/bin/python3 -I tools/setup-wizard.py stage
```

This validates the finished private bundle and creates root-owned 0600 files in
`/root/lab-credentials/`:

| File | Contents |
| --- | --- |
| `owner-settings.txt` | Non-secret form choices; merge into `.local/settings.txt` without erasing unrelated answers. Never source it. |
| `capabilities.json` | Non-secret selected services and pending verification. |
| `setup-bundle.json` | Credentials and full selected configuration. Never print, paste, commit or include it in an agent prompt. |

The agent should surface the non-secret choices for review, reuse these answers,
and follow SETUP.md. Confirm the actual machine, DNS and SSH/firewall settings.
The form's saved values are not proof of those conditions. Install the core only
on a confirmed fresh target. Do not rerun bootstrap on an existing installation.

Once core installation exists:

```sh
sudo /usr/bin/python3 -I tools/setup-wizard.py apply
```

This revalidates and stages the finished bundle, then uses the platform lifecycle
lock to merge selected AI keys into `/etc/lab/secrets.env`, configure hosted ntfy
in `/etc/lab/notify.env` and the legacy backup alert destination, and optionally
configure Resend and a separate Stripe **test-only** file. Existing unrelated
credentials are retained. Existing app grants and environment files are not
changed; grant required keys and restart selected apps through labctl as usual.
A non-secret `/etc/lab/setup-capabilities.json` describes only this setup's
selections, not every service already on the host. A saved key is not a verified
integration. Removing a key from the form or deferring a service does **not** revoke
or disable its already-installed counterpart; removal from a running host is a
separate administrator operation.

The commands are resumable configuration writes, not a multi-file transaction.
If interrupted, inspect the reported failure and re-run apply with the same
finished bundle. No package installs, service restarts, payments or schedules are
performed by apply. Secret files use the same literal KEY=value format as the
existing importer; never shell-source them. This form path is an alternative to
manual providers.env / ntfy.env entry, not an additional import to run afterward.

The agent must still configure selected backups and Healthchecks using
[server-backups.md](server-backups.md). Read the protected JSON programmatically,
extract only required fields into the documented protected destinations, and never
print their values. Review and validate endpoint, bucket, timezone and repository
choices before use; never interpolate them into shell commands. Preserve the
owner's backup password exactly. Initialize, back up and restore a test file,
confirm off-server recovery details, then enable one reviewed schedule. Those
operations are intentionally not triggered by saving a form. Resend domain
verification/test delivery, Stripe app integration and GitHub interactive login
likewise remain explicit agent steps.

After verified handoff, remove the form's `setup.json` and the root staging
`setup-bundle.json` using the administrator account, once all selected secrets
are in their final protected locations. Keep the non-secret settings and status
records. Stop the process before cleanup. Neither backup encryption passwords
nor configuration on existing services should be deleted as part of cleanup.

## Security and scope

Every API request requires the random in-memory setup code, strict loopback Host
checks and same-origin requests. No cookies, CORS, third-party scripts, analytics,
localStorage or sessionStorage are used. Headers disable caching, framing and
referrer transmission; request logging is disabled. Bodies are bounded; values
are validated before saving. Secrets and private topics are absent from status
responses. Unexpected network/file errors are redacted. A setup process can
write only its private staging area through fixed application operations; there
is no shell-command, arbitrary-path, package-install or remote-fetch endpoint.

This is a single-owner local administration tool, not an Internet-facing service
or a multi-user vault. The host administrator can read credentials. The form does
not automatically detect currently configured services or validate provider keys.
Do not expose its port through Caddy, a public firewall rule or Tailscale Serve.
Use the SSH tunnel even if SSH itself travels over Tailscale.

## Tests and browser QA

```sh
uv run --locked pytest
uv run --locked python tools/check-source.py
node --check tools/setup-ui/app.js
uv tool run --from playwright==1.64.1 playwright install chromium
uv run --locked --with playwright==1.64.1 python tools/check-setup-ui.py
```

The browser check starts an isolated loopback fixture, uses dummy credentials and
a mocked notification sender, checks desktop/mobile layouts, and stops its server.
Pass `--screenshots /absolute/output/directory` to save previews. No real account
keys are needed. Source/browser checks do not establish live VPS installation,
real phone delivery, API billing/access or Ubuntu 26.04 compatibility.
