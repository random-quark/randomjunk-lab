#!/usr/bin/env bash
#
# Nightly backup. Runs as root from lab-backup.timer.
#
# SECURITY: this script reads ONLY /etc/lab/backup.env, which is root-owned and
# in a root-owned directory. It is parsed line by line and never sourced, so
# nothing the lab user or an experiment can write is executed as root.
#
# What is captured:
#   * every Postgres database, plus cluster globals (roles, memberships)
#   * every SQLite database, snapshotted consistently rather than copied live
#   * /srv/lab (excluding .venv, which is rebuilt from uv.lock)
#   * /etc/caddy AND Caddy's data directory, which holds certificates and the
#     ACME account key — without it a restore re-issues every certificate
#   * /etc/lab and /etc/systemd/system/lab-app@*.d
#
set -euo pipefail

CONF=/etc/lab/backup.env
DUMP_DIR=/var/backups/lab
LAB_ROOT=/srv/lab
CADDY_DATA=/var/lib/caddy

fail() {
  local msg="$1"
  /usr/local/bin/lab-notify-root "Backup FAILED on $(hostname)" "$msg" || true
  echo "lab-backup: $msg" >&2
  exit 1
}
# Any unhandled failure anywhere in the job alerts — not only the final check.
trap 'fail "unexpected failure at line $LINENO"' ERR

[[ -r $CONF ]] || fail "cannot read $CONF"
# Strict parse: assignments only, no sourcing.
while IFS='=' read -r k v; do
  case "$k" in
    B2_ENDPOINT|B2_BUCKET|B2_KEY_ID|B2_APP_KEY|RESTIC_PASSWORD) printf -v "$k" '%s' "$v" ;;
  esac
done < <(grep -E '^[A-Z0-9_]+=' "$CONF")

: "${B2_BUCKET:?B2_BUCKET missing}"; : "${B2_ENDPOINT:?B2_ENDPOINT missing}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD missing}"

export RESTIC_REPOSITORY="s3:${B2_ENDPOINT}/${B2_BUCKET}/lab"
export AWS_ACCESS_KEY_ID="$B2_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$B2_APP_KEY"
export RESTIC_PASSWORD

install -d -m 700 "$DUMP_DIR"
find "$DUMP_DIR" -type f -mtime +2 -delete

# --- Postgres ------------------------------------------------------------------
# Globals first: per-database dumps do not contain roles or memberships, so a
# restore without these leaves databases owned by roles that do not exist.
sudo -u postgres pg_dumpall --globals-only | gzip -9 > "$DUMP_DIR/globals.sql.gz" \
  || fail "pg_dumpall --globals-only failed"

# Enumerate explicitly: a failed query inside a for-loop substitution would
# otherwise silently produce an empty list and a backup with no databases.
DBLIST=$(sudo -u postgres psql -tAc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres'") \
  || fail "could not enumerate Postgres databases"

while read -r db; do
  [[ -n $db ]] || continue
  sudo -u postgres pg_dump --clean --if-exists "$db" | gzip -9 > "$DUMP_DIR/pg-$db.sql.gz" \
    || fail "pg_dump of $db failed"
done <<<"$DBLIST"

# --- SQLite --------------------------------------------------------------------
# Copying a live SQLite file (plus its -wal) can capture a torn state.
# VACUUM INTO takes a consistent snapshot through SQLite's own machinery.
while IFS= read -r -d '' dbfile; do
  out="$DUMP_DIR/sqlite-$(echo "${dbfile#$LAB_ROOT/}" | tr '/' '-')"
  rm -f "$out"
  sqlite3 "file:${dbfile}?mode=ro" "VACUUM INTO '${out}';" \
    || fail "SQLite snapshot of $dbfile failed"
done < <(find "$LAB_ROOT" -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print0)

# --- restic --------------------------------------------------------------------
restic backup --tag lab \
  --exclude '**/.venv' --exclude '**/__pycache__' --exclude '**/node_modules' \
  "$LAB_ROOT" "$DUMP_DIR" /etc/caddy "$CADDY_DATA" /etc/lab \
  /etc/systemd/system/lab-app@.service /etc/systemd/system/lab-app@*.service.d \
  || fail "restic backup failed"

restic forget --tag lab --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune \
  || fail "restic forget/prune failed"

restic check --read-data-subset=1% >/dev/null || fail "restic check failed"

trap - ERR
exit 0
