#!/usr/bin/env bash
#
# lab-server bootstrap — run once, as root, on a fresh Ubuntu 24.04 box.
# Idempotent: safe to re-run after editing.
#
#   ./bootstrap.sh sand.box
#
set -euo pipefail

DOMAIN="${1:-}"
[[ -n $DOMAIN ]] || { echo "usage: $0 <domain>   e.g. $0 sand.box" >&2; exit 1; }
[[ $DOMAIN =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}$ ]] || { echo "invalid domain: $DOMAIN" >&2; exit 1; }
[[ $EUID -eq 0 ]] || { echo "must run as root" >&2; exit 1; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT=/srv/lab
LAB_USER=lab

say() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------- packages ----
say "Installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  ca-certificates curl gnupg lsb-release apt-transport-https \
  debian-keyring debian-archive-keyring \
  git jq sqlite3 unzip python3 python3-venv \
  librsvg2-bin \
  postgresql postgresql-contrib \
  restic ufw fail2ban unattended-upgrades

if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi

if ! command -v caddy >/dev/null 2>&1; then
  say "Installing Caddy"
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  apt-get update -qq && apt-get install -y -qq caddy
fi
say "Caddy version: $(caddy version | head -1)  — record this; --watch and admin
    socket behaviour are version-specific."

# -------------------------------------------------------------- lab user -----
say "Creating '$LAB_USER' and $LAB_ROOT"
id -u "$LAB_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$LAB_USER"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 755 "$LAB_ROOT"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 700 "$LAB_ROOT/.state"
printf '%s\n' "$DOMAIN" > "$LAB_ROOT/.domain"
chown "$LAB_USER:$LAB_USER" "$LAB_ROOT/.domain"
[[ -f $LAB_ROOT/ports.tsv ]] || printf '# name\tport\n' > "$LAB_ROOT/ports.tsv"
chown "$LAB_USER:$LAB_USER" "$LAB_ROOT/ports.tsv"

# ------------------------------------------------------------- secrets -------
# Root-owned and root-only. The lab user cannot read this file; agents ask for
# individual keys by name via `labctl secrets-grant`, which copies only those
# keys into a per-app env file owned by root and readable by that app alone.
say "Creating /etc/lab"
install -d -o root -g root -m 755 /etc/lab
install -d -o root -g root -m 710 /etc/lab/apps
if [[ ! -f /etc/lab/secrets.env ]]; then
  cat > /etc/lab/secrets.env <<'SECEOF'
# Master secrets. root:root 0600 — the lab user and experiments CANNOT read this.
# Grant individual keys to an app with:  labctl secrets-grant KEY,KEY <app>
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
REPLICATE_API_TOKEN=
OPENROUTER_API_KEY=
RESEND_API_KEY=
TAVILY_API_KEY=
ELEVENLABS_API_KEY=
GITHUB_TOKEN=
B2_ENDPOINT=
B2_BUCKET=
B2_KEY_ID=
B2_APP_KEY=
SECEOF
fi
chown root:root /etc/lab/secrets.env; chmod 600 /etc/lab/secrets.env

# Notification config. Two files on purpose: the lab user needs to send
# notifications, but the root backup job must not depend on anything the lab
# user could influence.
if [[ ! -f /etc/lab/notify.env ]]; then
  printf 'NTFY_URL=https://ntfy.sh\nNTFY_TOPIC=CHANGE-ME-long-and-random\n' > /etc/lab/notify.env
fi
chown root:root /etc/lab/notify.env; chmod 644 /etc/lab/notify.env

if [[ ! -f /etc/lab/backup.env ]]; then
  cat > /etc/lab/backup.env <<'BKEOF'
# Backup credentials. root:root 0600 — deliberately NOT readable by lab or by
# any experiment: these can delete the backup repository.
B2_ENDPOINT=
B2_BUCKET=
B2_KEY_ID=
B2_APP_KEY=
RESTIC_PASSWORD=
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=CHANGE-ME-long-and-random
BKEOF
fi
chown root:root /etc/lab/backup.env; chmod 600 /etc/lab/backup.env

# ------------------------------------------------------------- postgres ------
say "Configuring Postgres"
PG_VERSION="$(ls /etc/postgresql | sort -V | tail -1)"
apt-get install -y -qq "postgresql-${PG_VERSION}-pgvector" \
  || echo "!! pgvector unavailable for PG ${PG_VERSION} — see SETUP.md"
systemctl enable --now postgresql
# The lab role exists so the agent can run read-only psql. It deliberately has
# NO CREATEDB or CREATEROLE: all provisioning happens through labctl as the
# postgres superuser, which is what PG16's role rules require anyway.
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$LAB_USER'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE ROLE $LAB_USER LOGIN;"
sed -i "s/^#\?listen_addresses.*/listen_addresses = 'localhost'/" \
  "/etc/postgresql/${PG_VERSION}/main/postgresql.conf"

# ---------------------------------------------------------------- caddy ------
say "Configuring Caddy"
install -d -o root -g root -m 755 /etc/caddy/sites
[[ -f /etc/caddy/Caddyfile.orig ]] || cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.orig 2>/dev/null || true

cat > /etc/caddy/Caddyfile <<CADDYEOF
# Managed by lab-server bootstrap.sh — do not hand-edit.
# Site config lives in /etc/caddy/sites/*.caddy, deployed only via labctl.

{
	email admin@${DOMAIN}

	# Administration API on a root-only Unix socket rather than localhost:2019.
	# On the default TCP endpoint any local process — including an experiment —
	# could reconfigure the proxy. Restricting systemctl is not enough.
	admin unix//run/caddy/admin.sock

	# on_demand_tls is deliberately NOT enabled: with wildcard DNS it would let
	# anyone trigger unlimited certificate issuance. See SETUP.md.
}

import /etc/caddy/sites/*.caddy
CADDYEOF

# The admin socket must be root-only, and --watch is NOT used: deployment is an
# explicit validate-then-reload through labctl, which can roll back.
mkdir -p /etc/systemd/system/caddy.service.d
cat > /etc/systemd/system/caddy.service.d/lab.conf <<'CSVC'
[Service]
RuntimeDirectory=caddy
RuntimeDirectoryMode=0700
CSVC

# --------------------------------------------------------------- systemd -----
say "Installing unit template and lab tooling"
install -m 644 "$REPO_DIR/etc/lab-app@.service" /etc/systemd/system/lab-app@.service

install -o root -g root -m 755 "$REPO_DIR/sbin/labctl" /usr/local/sbin/labctl
install -d -o root -g root -m 755 /usr/local/lib/lab
install -o root -g root -m 644 "$REPO_DIR/bin/lib/labcommon.sh" /usr/local/lib/lab/labcommon.sh
install -o root -g root -m 755 "$REPO_DIR/bin/lib/render.py"    /usr/local/lib/lab/render.py
for s in newlab labrm labs labdoctor notify; do
  install -o root -g root -m 755 "$REPO_DIR/bin/$s" "/usr/local/bin/$s"
done
install -o root -g root -m 755 "$REPO_DIR/backup/lab-backup.sh"   /usr/local/bin/lab-backup
install -o root -g root -m 755 "$REPO_DIR/backup/lab-notify-root" /usr/local/bin/lab-notify-root

install -d -o root -g root -m 755 /usr/local/share/lab
rm -rf /usr/local/share/lab/templates
cp -r "$REPO_DIR/templates" /usr/local/share/lab/templates
chown -R root:root /usr/local/share/lab

install -o "$LAB_USER" -g "$LAB_USER" -m 644 "$REPO_DIR/CLAUDE.md" "$LAB_ROOT/CLAUDE.md"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 755 "$LAB_ROOT/docs"
install -o "$LAB_USER" -g "$LAB_USER" -m 644 "$REPO_DIR/docs/"* "$LAB_ROOT/docs/"

# ------------------------------------------------------------ sudo rights ----
# One rule, one binary, no argument globs. labctl validates its own arguments;
# a wildcard like "systemctl stop lab-app@*" would also match a trailing
# unrelated unit name, which is exactly the trap this avoids.
say "Installing sudoers rule"
cat > /etc/sudoers.d/lab <<'SUDOEOF'
Defaults:lab !requiretty
lab ALL=(root) NOPASSWD: /usr/local/sbin/labctl
SUDOEOF
chmod 440 /etc/sudoers.d/lab
visudo -cf /etc/sudoers.d/lab

# ----------------------------------------------------------------- backup ----
cat > /etc/systemd/system/lab-backup.service <<'BKSVC'
[Unit]
Description=lab-server nightly backup

[Service]
Type=oneshot
ExecStart=/usr/local/bin/lab-backup
BKSVC
cat > /etc/systemd/system/lab-backup.timer <<'BKTIM'
[Unit]
Description=Run lab-server backup nightly

[Timer]
OnCalendar=*-*-* 03:30:00
RandomizedDelaySec=900
Persistent=true

[Install]
WantedBy=timers.target
BKTIM

# --------------------------------------------------------------- firewall ----
say "Firewall"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp  >/dev/null   # HTTP-01 challenge + redirect
ufw allow 443/tcp >/dev/null   # HTTPS + TLS-ALPN-01 challenge
ufw --force enable >/dev/null

# ------------------------------------------------------------------ start ----
systemctl daemon-reload
systemctl restart postgresql
systemctl enable --now caddy && systemctl restart caddy
systemctl enable --now lab-backup.timer
systemctl enable --now unattended-upgrades

say "Done."
cat <<DONEEOF

  Domain:     ${DOMAIN}
  Postgres:   ${PG_VERSION}, localhost only; provisioning only via labctl
  Caddy:      admin on a root-only unix socket; deploys validated by labctl
  Sudo:       lab may run /usr/local/sbin/labctl and nothing else

  STILL TO DO BY HAND — see SETUP.md:
    1. DNS:  A  *  -> this server's IP
    2. /etc/lab/secrets.env    (API keys; set spend caps at each provider)
    3. /etc/lab/notify.env     (ntfy topic — long and random)
    4. /etc/lab/backup.env     (B2 credentials + restic password), then restic init
    5. Smoke test:  sudo -u lab -i newlab hello --static
    6. Run the integration matrix in SETUP.md before trusting this unattended.

DONEEOF
