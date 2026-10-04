# Installation run — randomjunk.dev — 2026-09-07

Owner authorization: install/manage the platform, ask for prerequisites when needed,
use randomjunk.dev, use staged OpenAI/Gemini/Replicate keys and hosted ntfy.
No VPS snapshot requested; owner accepts rebuilding this disposable machine.
GitHub publishing and remote-backup credentials remain a later configuration step.

## Preflight

- Ubuntu 24.04 with systemd as PID 1; SSH listens on 22, Tailscale already active.
- Public IPv4: 84.247.128.147. Existing lab/Caddy/Postgres platform paths absent.
- UFW installed but inactive before platform installation.
- providers.env is root-owned 0600; required key names OPENAI_API_KEY,
  GEMINI_API_KEY and REPLICATE_API_TOKEN are nonempty. Values not printed.
- ntfy.env was root-owned 0600 containing only the generated random topic.
  Normalized it to NTFY_URL/NTFY_TOPIC assignments without displaying the topic.
- Requested Name.com wildcard and root A records pointing to 84.247.128.147;
  initial DNS still points to registrar parking. IPv6 records deferred initially.

## Commands and evidence

Installer command from the repository:

```sh
bash bootstrap.sh --install-fresh randomjunk.dev
```

Full package/bootstrap output is retained locally in
`/root/workspaces/labserver-review/installation-logs/bootstrap.log`.
No secrets are included in that command or installation output.
This is an ongoing run; completion and live test results are recorded below.

## Core installation completed

Bootstrap completed successfully. Installed Caddy 2.11.4, PostgreSQL 16.15 with
pgvector package, uv 0.8.22. caddy/postgresql/ssh/tailscaled/fail2ban and
unattended-upgrades are active. UFW allows OpenSSH/80/443; existing SSH and
Tailscale remain active. Backup timer is disabled.

Ran `python3 -I tools/import-credentials.py`: imported the three configured
provider keys, configured hosted ntfy for lab and root backup alerts, and retained
0600/0640 ownership boundaries. No values printed. Direct unprivileged helper
execution refuses as intended; the supported invocation is `sudo labctl ...`.
Sent one ntfy setup test clearly stating validation is still in progress. Phone
receipt requires the owner's confirmation; no readiness claim was sent yet.

## Confirmed prerequisites and first live matrix

- Owner confirmed Android receipt of the ntfy setup test. iPhone remains untested.
- Both the apex and wildcard DNS now resolve to 84.247.128.147.
- Added a root-configured `internal` TLS test mode restricted to .test domains,
  and skip_install_trust to Caddy. Tests trust only Caddy's local CA within their
  HTTP client; no machine-wide CA installation or production ACME requests.
- First live matrix passed: public/private static, no-DB backend, SQLite backend,
  private Postgres backend, pgvector operations, two successive dummy secret
  grants, actual Caddy/lab/runtime file permissions, no root fallback on an
  unprovisioned systemd instance, reconciliation, removal and repeated removal.
- All first-matrix app records/users/DBs were removed and production configuration
  and /etc/hosts restored. Expanded failure/recovery checks follow.

Reproduce the authorized live matrix on an otherwise empty installed platform:

```sh
python3 -I tools/live-integration.py
```

It creates only dummy .test apps, uses a protected local log, removes fixtures,
and restores provider configuration without printing values. It is an integration
tool, not part of the isolated pytest suite. Do not run it casually on a used
platform. GitHub access and remote backup storage remain unconfigured.

The first expanded stop-failure fixture used a failing ExecStop hook. systemd
can still stop the process successfully in that case, so the fixture's assertion
was wrong; all dummy resources were cleaned up. Corrected the fixture to
RefuseManualStop=yes to test an actual rejected stop with the process retained.
Prior integration logs are archived locally rather than overwritten.

## Final installed state and evidence

Expanded live integration passed, including concurrent creates, actual stop
refusal preserving the app, real Caddy rollback, static symlink refusal,
PostgreSQL/vector restore, runtime-user SQLite snapshots and encrypted LOCAL
restic restore/staging. Local restic tests used dummy data and an ephemeral
password; no real provider credentials were backed up by that test. The earlier
source-only deferrals are superseded only for these tested cases.

The final production configuration is randomjunk.dev with default public TLS.
https://welcome.randomjunk.dev returns HTTP/2 200 with certificate validation.
The intentionally retained welcome app is static; all check-* accounts, records,
databases and unit drop-ins were removed. Original /etc/hosts and provider keys
were restored. Inactive .test leaf-certificate cache entries were removed; the
Caddy local CA remains for future internal tests, outside system trust.

Installed/source comparison: 30 code/template files identical. labdoctor: 0
problems. caddy/postgresql/ssh/tailscaled/fail2ban/unattended-upgrades active.
secrets.env and backup.env are root-owned 0600; notify.env is root:lab 0640.
The operating guides are installed under /srv/lab and /home/lab, with reference
docs under /usr/local/share/lab/docs. Enter the deployment shell with:

```sh
sudo -iu lab
cd /srv/lab
```

A readiness notification was sent with the welcome URL after server checks passed.
The owner confirmed the earlier Android setup notification and supplied an
Android browser screenshot showing welcome.randomjunk.dev rendering the expected
Randomjunk Lab scaffold without a displayed certificate warning. Android page
loading is confirmed; iPhone and PWA installation were not tested. The external web
fetch tool refused the new URL under its own URL-safety check; that is not an
HTTP failure from the server, and no external-fetch success is claimed.

## Existing host findings

`cloud-init.service` failed at 06:06:53 CEST and
`systemd-networkd-wait-online.service` failed at 06:10:51 CEST on 2026-09-07,
during boot and before this installation. Current networking/SSH/Tailscale work.
These were documented, not hidden with reset-failed or repaired by changing a
working network configuration. A future reboot/network review can address them.

## Follow-up configuration

- Hosted ntfy configured; no self-hosted notification service installed.
- Provider key presence/configuration checked; no paid calls or model-access tests.
- Remote backup storage/credentials not provided; lab-backup.timer remains disabled.
  The successful LOCAL restore drill is not a B2 recovery test.
- GitHub credentials not provided. Selected-repository publishing is a follow-up;
  do not grant its deployer credentials to arbitrary app runtimes.
- No reboot, old-version migration or iPhone/PWA installation test performed.
- The root domain has DNS configured; app sites use their own subdomains. The
  welcome URL is the initial live endpoint, not an apex-domain website.

## Owner phone confirmation

The supplied Android screenshot confirms that the expected welcome scaffold
renders on the phone. This completes the pending phone page-load check, not a
Tetris implementation or PWA-installation test. The screenshot was not copied
into the repository or source ZIP.

## WebKit testing profile — 2026-09-16

Installed reviewed Ubuntu graphics/media/text dependencies for Playwright WebKit.
Browser installation and testing run as lab, OS packages through trusted apt.
See docs/browser-testing.md (browser-testing.md from this docs directory) for exact
reproduction and engine/device coverage limits. No bootstrap rerun or app changes.

## Whole-server B2 backup — 2026-09-17

Configured the owner-provided private B2 repository with root-only credential and
password files outside Git. Installed the reviewed whole-server script, exclusion
list, root cron at 03:30 Europe/Berlin and weekly log rotation. The older
`lab-backup.timer` remains disabled to avoid duplicate jobs.

The first run processed 1.579 GiB and stored 645.672 MiB. A corrected second run
removed transient SQLite destination sidecars, added 2.337 MiB of stored data,
passed the 1% repository check and restored `/etc/hostname` byte-identically from
B2. See docs/server-backups.md for scope, retention and recovery commands.

## JD Scout remote-browser proof of concept — 2026-10-04

Owner requested a private JD/MCP experiment. Installed Ubuntu packages using
`apt-get install -y --no-install-recommends x11vnc novnc` (Xvfb and browser OS
libraries already present). These are optional tools, not default lab requirements.
No public VNC listener or machine-wide desktop service was enabled.

Only `lab-app@jd-scout.service` has a new browser.conf drop-in: MemoryMax=1536M,
TasksMax=256, CPUQuota=150%. Its source/reproduction lives in the experiment's
`/srv/lab/jd-scout/app/ops/browser.conf` and install.md. Runtime Chromium downloads
live in `/srv/lab/jd-scout/browsers`; login profiles use private data/.cache and
are excluded by the existing backup rules. The site credential remains root-only;
its SHA-256 verifier is injected into the app environment. Do not copy secrets
into this repository. JD account login and authenticated extraction need owner
interaction and are not asserted by platform liveness checks.
