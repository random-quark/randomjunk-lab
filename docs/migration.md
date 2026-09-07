# Migration from either draft

Revision 3 changes the privileged boundary and directory layout. It is **not**
an in-place upgrade script. Bootstrap refuses existing platform paths/accounts
and Caddy configuration before package installation. That refusal addresses the
unsafe draft-rerun behavior; automated old-version migration is not implemented.

During a separately authorized migration, inventory and checkpoint:

- `/srv/lab`, its old `.state`, ports.tsv, .domain, shared env files, per-app
  source/data/lockfiles and any custom install.md notes;
- `/usr/local/bin` lab tools, `/usr/local/lib/lab`, privileged helper, templates;
- unit template, all per-instance drop-ins, enablement, runtime identities;
- all Caddy config/drop-ins, actual admin address/socket permissions, certificates;
- Postgres databases, roles, memberships and grants (including any old lab role
  with CREATEDB/CREATEROLE or inherited powers), SQLite snapshots;
- root/lab/shared secret file permissions and key names without displaying values;
- timers, restic credentials/retention and external resources.

Prefer a new target machine and staged restoration. Map old source from
`/srv/lab/NAME/` into the new `/srv/lab/NAME/app/`, keep data separate, and rebuild
venvs as lab with locked dependencies. Migrate old metadata explicitly; the v3
stager accepts v3 manifests only. Old 25–31 character names need a reviewed rename
because v3 limits app names to 24 for portable runtime usernames.

On an eventual in-place migration, stop and verify affected services first and
preserve rollback copies. Remove/revoke old broad sudoers, provisioning-role
privileges and obsolete Caddy overrides only after mapping dependencies. Do not
leave shared secret files reachable by old identities. Reconcile UID/GID
ownership, service identity, granted keys, DB passwords and Caddy data before
publication. Never rotate real credentials or delete old resources as an
incidental bootstrap side effect. Record every migration command and test result.
