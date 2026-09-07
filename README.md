# lab-server

## What this is for

A single throwaway VPS where I can say to a coding agent *"build me a Tetris game
that does X"* and, a few minutes later, get a message on my phone with a working
URL — `tetris.example.com` — running as an installable PWA over HTTPS.

The goal is **zero repeated architecture decisions**. Every experiment needs the
same plumbing: a subdomain, a certificate, a port, maybe a database, a service
that survives reboot, and clean removal later. Deciding that once and encoding it
here means an agent spends its effort on the actual app and cannot get the boring
parts subtly wrong.

Design constraints that shaped everything:

- **Many small, mostly disposable experiments.** Removal must be as reliable as
  creation — hence resource records, `labrm`, and `labdoctor`.
- **Agents work largely unattended.** Conventions are enforced by tools where
  possible and written down where not. Failure paths matter more than happy paths.
- **The box is expendable; credentials are not.** API balances, GitHub tokens,
  backup-deletion keys and domain reputation all outlive the machine, so they are
  kept out of reach of the experiments themselves.
- **No DNS work per experiment.** One wildcard record does it forever.

## The pieces

| File | What it is |
|---|---|
| `bootstrap.sh` | Run once as root on a fresh box. Idempotent. |
| `SETUP.md` | Rationale, manual steps, and the integration matrix to run before trusting this. |
| `CLAUDE.md` | Installed at `/srv/lab/CLAUDE.md`. The rules agents read. |
| `sbin/labctl` | Root-owned. The single privileged entry point; the only sudo target. |
| `bin/newlab` | Creates an experiment, records resources, rolls back on failure. |
| `bin/labrm` | The one teardown implementation; also used for rollback. |
| `bin/labdoctor` | Reconciles records against reality; finds orphans and stale experiments. |
| `bin/labs`, `bin/notify` | List experiments; push a notification. |
| `templates/` | Static PWA shell, and FastAPI + PWA for `--app`. |
| `backup/` | Nightly restic backup with its own root-owned credentials. |

## Order of operations

1. Buy the domain. Add one DNS record: `A  *  <server-ip>`
2. Clone to `/opt/lab-server`, then `sudo ./bootstrap.sh yourdomain.tld`
3. Fill in `/etc/lab/secrets.env`, `/etc/lab/notify.env`, `/etc/lab/backup.env`
4. `restic init`, then test a restore
5. Smoke test: `sudo -u lab -i newlab hello --static`, then `labrm hello`
6. Work through the integration matrix in `SETUP.md`
7. From then on: `sudo -u lab -i`, then `claude` from `/srv/lab` — **not as root**

## Status

**Untested against a real machine.** Revision 2, after an external review that
found privilege-escalation, partial-failure and teardown problems in the first
draft. See `CHANGELOG.md`. Nothing here has been run on Ubuntu with real systemd
and Postgres — treat `SETUP.md`'s integration matrix as required, not optional.
