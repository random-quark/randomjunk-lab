# Whole-server Restic backups

This is an optional administrator setup. Configure it only when the owner asks
for remote whole-server backups and supplies a private bucket plus restricted
credentials. Secrets never belong in this repository, agent chat, commands,
process arguments or logs.

The installed job backs up `/` and excludes replaceable operating-system files,
caches, logs and selected transient files. Application data is included unless
explicitly excluded. This is not a bootable disk image. Starting from `/` makes future application data
under locations such as `/opt` or `/var/www` opt-out rather than easy to miss.
Review the exclusion file whenever the storage layout changes. A new mounted
filesystem or unusual database engine still needs explicit review.

## Fresh-machine prerequisites

Install Restic (at least 0.16), cron and logrotate through the OS package manager;
check `restic version`. The core bootstrap installs Restic, but does not configure
this whole-server job. Review database clients, storage mounts and the exclusion
list for this specific host. The Parcel exclusion is only an example for that
app's expiring uploads; it does not imply Parcel is installed.

## Protected configuration

Create `/root/.restic-env` as root:root 0600 with shell-quoted values:

```sh
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export RESTIC_REPOSITORY=s3:https://S3-ENDPOINT/BUCKET/SERVER
export RESTIC_PASSWORD_FILE=/root/.restic-pass
```

Create `/root/.restic-pass` as root:root 0600 with a unique random password and
store an independent copy in the owner's password manager. Both files are
deliberately excluded from their own repository. Losing the password makes the
backup unusable. Never print the B2 application key during validation.

Install the reviewed files:

```sh
install -o root -g root -m 0700 admin/backup/restic-backup /usr/local/bin/restic-backup
install -o root -g root -m 0600 admin/backup/restic-backup-excludes /etc/restic-backup-excludes
install -o root -g root -m 0644 admin/backup/restic-backup.logrotate /etc/logrotate.d/restic-backup
```

The script creates a compressed `pg_dumpall` and consistent compressed snapshots
of SQLite files under `/srv`, `/home`, `/root`, `/opt` and `/var/www`, then backs
up the filesystem. PostgreSQL databases added to the current cluster and SQLite
files with `.db`, `.sqlite` or `.sqlite3` names are discovered automatically.
When introducing another database engine or a separate data mount, update and
test this job at the same time. Raw database files may be present in the general
filesystem snapshot, but only the logical/SQLite snapshots are recovery evidence.

Before the first backup, confirm this is a new, unique repository path and save
the password independently. As root, with the protected configuration already
created, initialize it (or inspect snapshots if deliberately connecting to an
existing repository; never delete an existing repository to make init succeed):

```sh
source /root/.restic-env
restic init
/usr/local/bin/restic-backup
restic snapshots
```

These root Restic files deliberately use trusted shell syntax. They are different
from `/etc/lab/secrets.env` and the literal provider staging files, which must not
be sourced. Do not use shell tracing or print credentials.

Complete the staged restore/compare below before adding the cron entry. Check
`timedatectl` and agree its timezone with the owner. Preserve other root cron jobs
and avoid duplicating an existing restic entry. Verify the cron service is enabled.

The schedule is a single root crontab entry, in the server's local timezone:

```cron
30 3 * * * /usr/local/bin/restic-backup >/dev/null 2>&1
```

Do not also enable `lab-backup.timer`; it is a separate older app-oriented job
and would duplicate uploads, checks and retention operations. The whole-server
script keeps 7 daily, 4 weekly and 6 monthly snapshots, prunes unneeded data and
checks 1% of repository data after every successful upload. Logs are at
`/var/log/restic-backup.log` and rotate weekly for twelve rotations.

## Verification and recovery

Run a manual backup before adding the schedule. Then verify:

```sh
source /root/.restic-env
restic snapshots --tag server1
restic stats --mode raw-data
```

Always restore into a new staging directory first. For one file:

```sh
source /root/.restic-env
restic restore latest --tag server1 --target /root/restore-staging --include /etc/hostname
```

For a full snapshot staged away from live paths:

```sh
source /root/.restic-env
restic restore SNAPSHOT_ID --target /root/restore-staging
```

Do not restore directly over `/`. Review ownership, secrets, database dumps and
service state before activating restored content. PostgreSQL's compressed dump is
`/var/backups/db/postgresql/all.sql.gz`; SQLite snapshot mappings are in
`/var/backups/db/sqlite/manifest.tsv`.

On the current server, the owner confirmed an independent password copy. A B2
backup, 1% repository check and byte-identical `/etc/hostname` staged restore
passed on 2026-09-17. This proves access to this repository at that time; it does
not prove a future scheduled run or a full rebuild on a different machine.

## Optional external monitoring (Healthchecks.io)

During setup, explicitly review BACKUP_MONITORING in settings.txt with the owner.
Create a check with a one-day period and one-hour grace, and select a verified
notification integration. Store HEALTHCHECKS_PING_URL with the UUID ping URL in
/root/.restic-healthchecks.env (root:root, mode 0600), using shell quoting.
Never commit the URL. This file is excluded from backups; recreate it on recovery.

The script sends /start after acquiring its lock, success only after upload,
retention and integrity verification finish, and /fail on unsuccessful exit.
No file contents or logs are sent. The URL goes to curl on stdin, not in arguments.
Delivery is bounded and best-effort: network failure does not interrupt a backup;
the external missing-ping alert covers lost contact. Overlapping runs send nothing.

The period is measured from pings, not the 03:30 cron schedule. Manual runs shift
that deadline until the next scheduled completion. A start without completion
exceeds grace after one hour. Increase grace if legitimate backups take longer.
A cron-based check in the selected server timezone is an alternative for fixed-clock deadlines.

Verify with a real backup and confirm the check becomes Up. Test failure routing
with a mocked curl, not an intentionally broken production backup. Owner must
confirm email receipt separately; HTTP acceptance alone does not prove delivery.
Official protocol: https://healthchecks.io/docs/bash/

## Parcel temporary storage

Parcel uploads and generated ZIPs live under /srv/lab/parcel/data/transient/ and
are excluded from Restic. Its SQLite metadata and application source remain
backed up. After restoration, missing transfer content is marked unavailable;
restoring the server does not resurrect expired downloads. Apply the equivalent
exclusion before enabling uploads on another host.
