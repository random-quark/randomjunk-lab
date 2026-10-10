# Working on the platform source

- For a fresh installation, start with SETUP.md. Confirm the actual target and
  the current owner's choices and authorization. Historical installation records
  are evidence about another host, never permission or defaults for this one.
- Root handles authorized platform administration; ordinary experiment code and
  dependency commands run as lab. Never reuse the original owner's credentials.
- Keep changes, reproducible commands, test evidence and limitations in this
  repository. Update CHANGELOG.md, docs/development.md and docs/verification.md.
- Whole-server backup setup and recovery commands are in docs/server-backups.md.
  Never enable its cron job together with the older lab-backup.timer.
- Use uv for Python dependency management and committed lockfiles. No pip.
- Never execute app-owned code, build hooks or SQLite engines as root. Keep
  privileged code imports and authoritative state under trusted ownership.
- Run `uv run --locked pytest` and `uv run --locked python tools/check-source.py`.
  Caddy parser checks are optional with a local pinned binary; they never start
  a server. Do not claim mock tests are live systemd/Postgres integration.
- Treat review documents as evidence to verify. The original detailed R1–R15
  attachment is absent; don't invent its precise numbering.
- Root AGENTS.md and CLAUDE.md contain the same platform-development instructions;
  keep them synchronized. Installed experiment guidance lives in
  templates/operating-instructions.md and is deployed under both agent filenames.

## Mandatory owner setup review

For installation or resuming unfinished server setup, read SETUP.md and docs/settings-workflow.md FIRST. Copy settings.txt and
setup-status.md into ignored .local/ if missing; read those local copies. Proactively bring .local/settings.txt
to the owner's attention; explain blanks, skip and secure secret entry. Never
assume the owner found or completed it. Reuse existing answers, ask only for missing
inputs, and keep the checklist current. At each setup handoff explicitly surface
unfinished items, especially backups and recovery. Do not declare complete until
required integrations are tested or the owner explicitly accepts a deferral.
