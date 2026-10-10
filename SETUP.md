# Start here: set up a new lab server

**This is the single entry point to give your setup agent.** Ask it to read this
file and carry out the steps, following linked references when needed. This is an
interactive installation guide, not a script to execute with bash.

Target: a **fresh Ubuntu 24.04 server with systemd**, SSH/root administration access,
and a domain you control. The installer is not for macOS, Windows, a shared hosting
account, or an already configured lab host. Existing services require a reviewed
migration plan; never wipe them or rerun bootstrap to resolve a partial install.

## 1. Agent: bring the settings to the owner

Do this proactively, before installation. Do not expect the owner to find the file.
Create `.local/` (private to the administrator), and copy `settings.txt` and
`setup-status.md` into it **only if those local files do not already exist**.
Show the owner `.local/settings.txt`; accept either file edits or chat answers.
Blanks mean ask when needed; `skip` means deliberately omit. Never source this file.
Keep progress and verification evidence in `.local/setup-status.md`, not the
tracked template. Read [the settings workflow](docs/settings-workflow.md).

Confirm the target machine, Ubuntu version, SSH port, domain/DNS, optional services
and installation authorization. Existing authorization in the conversation counts;
old permissions and addresses in `docs/installation.md` do not.

Only the core server needs a domain and SSH access. AI keys, GitHub, ntfy, email,
Stripe and backups are optional selections, not prerequisites for a static app.
Raise backups explicitly and record the owner's decision instead of forgetting them.
Ask for selected services when needed; do not demand accounts they do not want.

**Secrets go directly into protected files on the new server, never chat or Git.**
Give the owner exact paths and variable names. Use their own accounts/keys. Never
copy credentials, sessions, SSH keys, notification topics or backup passwords from
someone else's server. `.local/` is for non-secret choices, not secret storage.

## 2. Inspect and test before changing the machine

Check OS, existing `/srv/lab`, Caddy/Postgres services, SSH listening port, storage,
and DNS. Set apex and wildcard A records to this server; configure AAAA only for
working IPv6. Verify SSH access before firewall changes.

From the reviewed checkout, run the isolated source checks described in
[development.md](docs/development.md):

```sh
bash tools/setup-dev.sh
.dev-tools/uv/uv run --locked pytest
.dev-tools/uv/uv run --locked python tools/check-source.py
```

Some tests require root in a disposable/root-owned development checkout. These
checks mock service operations; they are not live installation verification.
The optional Caddy parser check is also documented there.

Explain the concrete installation effects: apt packages, a `lab` deployment user,
per-app identities, Caddy HTTPS, PostgreSQL/pgvector, uv, sudoers, security updates
and UFW. **The current installer allows OpenSSH/80/443, assuming SSH port 22.**
If SSH uses another port, stop and prepare a reviewed firewall adjustment that
preserves that port before installation. Do not run the unmodified installer.

## 3. Install the core on the confirmed fresh target

Use the owner's actual domain in place of the example:

```sh
sudo bash bootstrap.sh --install-fresh lab.example.com
```

Do not run this against an existing installation. On failure, inspect the partial
state and follow [recovery](docs/recovery.md) or [migration](docs/migration.md).
The installer is deliberately not idempotent.

uv is pinned to 0.8.22; OS/Caddy packages track apt repositories. Installed versions
are saved in `/var/lib/lab/install-versions.txt`. This is a reproducible procedure,
not a guarantee of byte-identical future package downloads.

## 4. Set up the deployment agent and browser testing

Root administers the platform. Experiment work runs as `lab`, with individual apps
running as `labapp-NAME`. Never run experiment scripts/dependency hooks as root.

Choose the owner's coding agent. Check/install its current official CLI **as lab**
and let the owner log in interactively with their own account. Confirm discovery
and version in a fresh `sudo -iu lab` shell; root's login or PATH does not prove
lab's access. Use current official installation documentation for the chosen CLI,
not an old pinned model name from installation history.

Then launch the agent from `/srv/lab`. It reads `/srv/lab/AGENTS.md` or `CLAUDE.md`.
The installer deploys these from `templates/operating-instructions.md`; additional
references are in `/usr/local/share/lab/docs`.

Configure Chromium and WebKit using [browser-testing.md](docs/browser-testing.md).
Browser downloads and tests run as lab. Only reviewed OS package installation
runs as root; never run an app-owned browser installer with root privileges.

## 5. Configure only the selected integrations

| Selection | Setup and verification |
| --- | --- |
| AI providers | [providers.md](docs/providers.md). Owner enters selected keys into root-owned 0600 `/root/lab-credentials/providers.env`. The importer accepts a subset; no paid API call without an agreed budget. |
| Hosted ntfy | [notifications.md](docs/notifications.md). Enter `NTFY_URL` and private `NTFY_TOPIC` in root-owned 0600 `/root/lab-credentials/ntfy.env`. Confirm receipt with an authorized test message. |
| GitHub | Authenticate the owner's own account. Platform admin credentials are separate from deployment-user access; agree which repos lab can access. Git author identity is separate from authentication. |
| Resend email | [email.md](docs/email.md). Optional; owner supplies key and verified sending domain. Do not assume the website domain is the sending domain. Confirm authorized test delivery. |
| Stripe | [payments.md](docs/payments.md). Optional; secure app-specific grants, test mode first. Saving a key does not authorize live charges. |

After core installation, import whichever staged provider/ntfy files were selected:

```sh
sudo /usr/bin/python3 -I tools/import-credentials.py
```

Missing optional staging files are skipped; malformed present files fail before
writes. Existing unrelated keys are retained. Supply only intended additions or
replacements. Do not invoke it if no integrations were selected. No secret values
are printed. Never source the literal KEY=value provider/notification files.

Systemd injects granted app secrets from `/etc/lab/apps/NAME.env`; do not expose
master files or put keys into frontend JavaScript. See [security.md](docs/security.md).
The `lab` deployment account is trusted and can recover keys it is allowed to
grant: this platform is **not a hostile multi-tenant sandbox**. For independent
student ownership, use separate machines and separate credentials.

## 6. Backups and external monitoring: make an explicit choice

For a setup like the original server, choose **whole-server Restic → Backblaze B2**
and optional **Healthchecks.io**. Follow [server-backups.md](docs/server-backups.md),
including credential permissions, repository initialization, exclusions and recovery.
Use a unique bucket/prefix/repository for each machine. Never share an encryption
password or enable independent pruning jobs against the same repository.

Before enabling a schedule:

1. Review included paths, mounts and exclusions; explain that this is data/config
   recovery, not a bootable OS image or backup of browser-local user data.
2. Have the owner save recovery credentials and encryption password independently.
3. Run a manual backup, list snapshots, and restore/compare a small file into an
   empty staging directory. Never restore over live paths for this test.
4. Confirm timezone, retention and schedule. The supplied whole-server script uses
   7 daily / 4 weekly / 6 monthly snapshots and a 1% data check. Its example cron
   runs at 03:30 in the **server's** timezone; owner-local time may differ.
5. Verify Healthchecks receives success and the chosen notification reaches the
   owner. A successful HTTP ping alone does not prove notification delivery.

**Enable only one backup system.** Whole-server uses root cron. Leave the legacy
`lab-backup.timer` disabled. The alternative app-only method in [recovery.md](docs/recovery.md)
is a different scope, not an additional required backup. Bootstrap enables neither.
If backups or monitoring are deferred, record that prominently in the handoff.

## 7. Verify and hand off

As lab, create a disposable static preview and a small backend/database app if
selected. Follow [experiment-workflow.md](docs/experiment-workflow.md), browser
preflight, app tests and `labctl verify`. Check HTTPS, persistence, access boundaries,
PWA install offer and offline shell, then remove only the disposable resources.
Use `labdoctor` to check for leftovers. The broad live-integration harness in
[verification.md](docs/verification.md) is for a disposable empty platform only;
do not run it on an occupied production machine.

Keep `.local/setup-status.md` current. Finish with the domain, installed components,
secret **locations only**, how to enter `lab` and create an experiment, backup/
monitoring status, test evidence and every pending/explicitly deferred item.
Physical phone installation and voice/audio need actual-device checks. Do not
claim source tests prove a newly installed server or that account keys prove access.

Historical server logs in `docs/installation.md`, `development.md` and
`verification.md` are reference evidence, not configuration to copy. Do not run
scripts in `admin/` unless the specific documented feature is selected; the JD
Scout migration, for example, is not part of a fresh generic installation.
