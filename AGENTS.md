# Working on the platform source

- Current scope is source development and isolated tests. Do not install the
  platform, change host services/users/firewall, configure real credentials,
  or send notifications without explicit authorization for that phase.
- Keep changes, reproducible commands, test evidence and limitations in this
  repository. Update CHANGELOG.md, docs/development.md and docs/verification.md.
- Use uv for Python dependency management and committed lockfiles. No pip.
- Never execute app-owned code, build hooks or SQLite engines as root. Keep
  privileged code imports and authoritative state under trusted ownership.
- Run `uv run --locked pytest` and `uv run --locked python tools/check-source.py`.
  Caddy parser checks are optional with a local pinned binary; they never start
  a server. Do not claim mock tests are live systemd/Postgres integration.
- Treat review documents as evidence to verify. The original detailed R1–R15
  attachment is absent; don't invent its precise numbering.
- CLAUDE.md describes future installed-platform use as lab; it does not forbid
  authorized source review in this repository from a root-owned workspace.
