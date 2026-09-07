# Shared helpers for newlab / labrm / labs / labdoctor. Sourced, not executed.
# Unprivileged: everything here runs as the 'lab' user.

LAB_ROOT=${LAB_ROOT:-/srv/lab}
STATE_DIR="$LAB_ROOT/.state"
PORTS_FILE="$LAB_ROOT/ports.tsv"
LOCK_FILE="$STATE_DIR/lock"
LABCTL="sudo /usr/local/sbin/labctl"
PORT_BASE=8100
RESERVED_NAMES='state|docs|lost+found|templates|backup'

die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }
info() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarn:\033[0m %s\n' "$*" >&2; }

valid_name() {
  local n=$1
  [[ ${#n} -ge 2 && ${#n} -le 31 ]] || return 1
  [[ $n =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] || return 1
  [[ ! $n =~ ^($RESERVED_NAMES)$ ]] || return 1
}

domain() { cat "$LAB_ROOT/.domain"; }

# --- locking ------------------------------------------------------------------
# Serialises creation, removal and port allocation. flock releases on process
# death, so a killed agent cannot wedge the lock.
with_lock() {
  # A child process (newlab calling labrm to roll back) inherits the parent's
  # lock through this marker rather than deadlocking against it.
  [[ ${LAB_LOCK_HELD:-0} == 1 ]] && return 0
  mkdir -p "$STATE_DIR"
  exec {LOCK_FD}>>"$LOCK_FILE"
  flock -w 60 "$LOCK_FD" || die "timed out waiting for the lab lock"
  export LAB_LOCK_HELD=1
}

# --- resource records ---------------------------------------------------------
# Written BEFORE anything is created and updated as each resource is acquired,
# so an interrupted run can still be cleaned up. This is the record labrm and
# labdoctor work from.
record_path() { printf '%s/%s.json' "$STATE_DIR" "$1"; }

record_init() {
  local name=$1 kind=$2 db=$3 private=$4
  python3 - "$(record_path "$name")" "$name" "$kind" "$db" "$private" <<'PY'
import json, sys, datetime
path, name, kind, db, private = sys.argv[1:6]
json.dump({
    "name": name, "kind": kind, "db": db, "private": private == "1",
    "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "state": "creating",
    "resources": {},
}, open(path, "w"), indent=2)
PY
  chmod 600 "$(record_path "$name")"
}

record_set() {   # record_set <name> <key> <value>
  python3 - "$(record_path "$1")" "$2" "$3" <<'PY'
import json, sys
path, key, val = sys.argv[1:4]
d = json.load(open(path))
if val in ("true", "false"):
    val = val == "true"
d["resources"][key] = val
json.dump(d, open(path, "w"), indent=2)
PY
}

record_state() {
  python3 - "$(record_path "$1")" "$2" <<'PY'
import json, sys
path, state = sys.argv[1:3]
d = json.load(open(path)); d["state"] = state
json.dump(d, open(path, "w"), indent=2)
PY
}

record_get() {   # record_get <name> <dotted.key>
  python3 - "$(record_path "$1")" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
cur = d
for part in sys.argv[2].split("."):
    cur = cur.get(part) if isinstance(cur, dict) else None
    if cur is None: break
print("" if cur is None else (str(cur).lower() if isinstance(cur, bool) else cur))
PY
}

# --- ports --------------------------------------------------------------------
# Call under the lock. Checks both the registry and what is actually listening.
alloc_port() {
  local used port
  used=$(awk 'NR>1 {print $2}' "$PORTS_FILE" 2>/dev/null | sort -n)
  port=$PORT_BASE
  while grep -qx "$port" <<<"$used" || ss -ltnH "sport = :$port" | grep -q .; do
    port=$((port + 1))
    [[ $port -lt 8999 ]] || die "no free port below 8999"
  done
  printf '%s\t%s\n' "$1" "$port" >> "$PORTS_FILE"
  printf '%s' "$port"
}

release_port() {
  [[ -f $PORTS_FILE ]] || return 0
  local tmp; tmp=$(mktemp)
  awk -v n="$1" '$1 != n' "$PORTS_FILE" > "$tmp" && mv "$tmp" "$PORTS_FILE"
}

# --- readiness ----------------------------------------------------------------
# Nothing is announced as working until this passes.
wait_http() {   # wait_http <url> [timeout-seconds]
  local url=$1 timeout=${2:-90} start
  start=$(date +%s)
  while true; do
    if curl -fsS --max-time 10 -o /dev/null "$url"; then return 0; fi
    (( $(date +%s) - start > timeout )) && return 1
    sleep 2
  done
}
