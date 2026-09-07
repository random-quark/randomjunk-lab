# Recovery

## Rebuild the platform

1. Fresh Ubuntu 24.04, wildcard DNS pointing at the new IP.
2. `./bootstrap.sh <domain>`
3. Restore `/etc/lab/*` from backup — or recreate the three config files by hand.
4. Restore `/var/lib/caddy` **before** starting Caddy, so existing certificates
   and the ACME account are reused rather than re-issued.

## Restore one experiment

    restic snapshots
    restic restore latest --target / --include /srv/lab/<name>
    restic restore latest --target / --include /srv/lab/.state/<name>.json

Then, depending on what the record says:

**Static** — deploy the Caddy site. The simplest reliable route is to recreate
the scaffolding and copy the files back:

    newlab <name> --static
    restic restore latest --target / --include /srv/lab/<name>/public

**SQLite app**

    newlab <name> --app --db sqlite
    # restore the snapshot taken by VACUUM INTO
    restic restore latest --target /tmp/r --include /var/backups/lab/sqlite-<name>-data-<name>.db
    cp /tmp/r/var/backups/lab/sqlite-*.db /srv/lab/<name>/data/<name>.db

**Postgres app**

    newlab <name> --app --db postgres
    restic restore latest --target /tmp/r --include /var/backups/lab/pg-lab_<name>.sql.gz
    zcat /tmp/r/var/backups/lab/pg-lab_<name>.sql.gz | sudo -u postgres psql -d lab_<name>

`newlab` creates a fresh role and password, so the app's `DATABASE_URL` is
correct after restore. If you instead restore roles from `globals.sql.gz`, the
passwords come with them and the env file must match.

Dependencies rebuild from `uv.lock` — `.venv` is excluded from backups on purpose.

## What backups do not cover

- **Retained snapshots outlive deletion.** `labrm` removes an experiment from the
  machine; restic keeps 7 daily, 4 weekly and 6 monthly snapshots. Data lives on
  in B2 until those expire.
- **Installed PWA state on a phone** is client-side and survives server deletion.
- **`RESTIC_PASSWORD`.** Lose it and every snapshot is unreadable. It is not in
  the backup, by definition.
