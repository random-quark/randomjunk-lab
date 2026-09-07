#!/usr/bin/env bash
# Fresh installation only. Never run this for review/testing or an upgrade.
set -euo pipefail
[[ ${1:-} == --install-fresh && $# -eq 2 ]] || {
  echo 'usage: sudo ./bootstrap.sh --install-fresh DOMAIN' >&2; exit 2;
}
[[ $EUID -eq 0 ]] || { echo 'root required' >&2; exit 1; }
DOMAIN=$2
REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 - "$DOMAIN" "$REPO_DIR/bin/lib" <<'PY'
import sys
sys.path.insert(0, sys.argv[2])
from labcore import domain
domain(sys.argv[1])
PY
# Guard BEFORE packages/configuration are touched. No implicit draft migration.
for path in /srv/lab /var/lib/lab /var/lib/lab-public /etc/lab /etc/sudoers.d/lab /etc/systemd/system/lab-app@.service; do
  [[ ! -e $path && ! -L $path ]] || { echo "Existing platform path: $path; see docs/migration.md" >&2; exit 1; }
done
if id lab >/dev/null 2>&1; then echo 'Existing lab account: migration required' >&2; exit 1; fi
if compgen -G '/etc/systemd/system/caddy.service.d/*' >/dev/null; then
  echo 'Existing Caddy overrides: inspect/migrate first' >&2; exit 1
fi
if [[ -e /etc/caddy/Caddyfile ]]; then
  echo 'Existing Caddy configuration: use a fresh machine or a reviewed installation plan' >&2; exit 1
fi
INSTALL_TMP=$(mktemp -d)
trap 'rm -rf -- "$INSTALL_TMP"' EXIT
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg debian-keyring debian-archive-keyring apt-transport-https \
  git python3 python3-venv librsvg2-bin postgresql postgresql-contrib restic ufw fail2ban unattended-upgrades
# Pin uv; do not execute a remote pipe. Archive checksums in the install log.
curl -fLsS https://astral.sh/uv/0.8.22/install.sh -o "$INSTALL_TMP/uv-install.sh"
UV_UNMANAGED_INSTALL=/usr/local/bin sh "$INSTALL_TMP/uv-install.sh"
curl -fLsS https://dl.cloudsmith.io/public/caddy/stable/gpg.key -o "$INSTALL_TMP/caddy-key"
# Caddy packages and OS security updates follow their apt repositories. Capture
# exact installed versions below; no claim that repository state is immutable.
gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg "$INSTALL_TMP/caddy-key"
curl -fLsS https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt -o /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy
PG_VERSION=$(ls /etc/postgresql | sort -V | tail -1)
apt-get install -y "postgresql-${PG_VERSION}-pgvector"
useradd --create-home --user-group --shell /bin/bash lab
install -d -o root -g root -m 755 /srv/lab /var/lib/lab-public /etc/lab
install -d -o root -g root -m 700 /var/lib/lab /var/lib/lab/records /var/lib/lab/credentials /etc/lab/apps /var/backups/lab
python3 - "$DOMAIN" <<'PY'
import json, os, sys
with open('/etc/lab/platform.json', 'w') as stream:
    json.dump({'version': 3, 'domain': sys.argv[1]}, stream)
os.chmod('/etc/lab/platform.json', 0o600)
PY
install -o root -g root -m 600 /dev/null /etc/lab/secrets.env
cat > /etc/lab/backup.env <<'EOF'
B2_ENDPOINT=
B2_BUCKET=
B2_KEY_ID=
B2_APP_KEY=
RESTIC_PASSWORD=
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=
EOF
chmod 600 /etc/lab/backup.env
cat > /etc/lab/notify.env <<'EOF'
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=
EOF
chown root:lab /etc/lab/notify.env
chmod 640 /etc/lab/notify.env
install -d -o root -g root -m 755 /usr/local/lib/lab /usr/local/share/lab
install -o root -g root -m 644 "$REPO_DIR/bin/lib/"*.py /usr/local/lib/lab/
python3 - "$REPO_DIR/templates" <<'PY_COPY'
import shutil, sys
shutil.copytree(sys.argv[1], '/usr/local/share/lab/templates', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.venv'))
PY_COPY
chown -R root:root /usr/local/share/lab
chmod -R a+rX /usr/local/share/lab
install -d -m 755 /usr/local/share/lab/docs
install -m 644 "$REPO_DIR/docs/"*.md /usr/local/share/lab/docs/
install -m 644 "$REPO_DIR/templates/operating-instructions.md" /srv/lab/AGENTS.md
install -m 644 "$REPO_DIR/templates/operating-instructions.md" /srv/lab/CLAUDE.md
install -o lab -g lab -m 644 "$REPO_DIR/templates/operating-instructions.md" /home/lab/AGENTS.md
install -m 755 "$REPO_DIR/sbin/labctl" /usr/local/sbin/labctl
for script in newlab labrm labs labdoctor notify; do
  install -m 755 "$REPO_DIR/bin/$script" "/usr/local/bin/$script"
done
install -m 755 "$REPO_DIR/backup/lab-backup.sh" /usr/local/bin/lab-backup
install -m 755 "$REPO_DIR/backup/lab-notify-root" /usr/local/bin/lab-notify-root
install -m 644 "$REPO_DIR/etc/lab-app@.service" /etc/systemd/system/lab-app@.service
cat > /etc/sudoers.d/lab <<'EOF'
Defaults:lab !requiretty
lab ALL=(root) NOPASSWD: /usr/local/sbin/labctl
EOF
chmod 440 /etc/sudoers.d/lab
visudo -cf /etc/sudoers.d/lab
cat > /etc/caddy/Caddyfile <<'EOF'
{
	admin unix//run/caddy/admin.sock
	skip_install_trust
}
import /etc/caddy/lab-sites.caddy
EOF
install -m 644 /dev/null /etc/caddy/lab-sites.caddy
install -d -m 755 /etc/systemd/system/caddy.service.d
cat > /etc/systemd/system/caddy.service.d/lab.conf <<'EOF'
[Service]
RuntimeDirectory=caddy
RuntimeDirectoryMode=0700
EOF
cat > /etc/systemd/system/lab-backup.service <<'EOF'
[Unit]
Description=lab backup (explicitly enable timer after configuration)
OnFailure=lab-backup-failure.service
[Service]
Environment=LAB_BACKUP_ONFAILURE=1
Type=oneshot
ExecStart=/usr/local/bin/lab-backup
UMask=0077
TimeoutStartSec=6h
EOF
cat > /etc/systemd/system/lab-backup-failure.service <<'EOF'
[Unit]
Description=Notify about failed lab backup
[Service]
Type=oneshot
ExecStart=/usr/local/bin/lab-notify-root "Lab backup FAILED" "Inspect lab-backup.service"
TimeoutStartSec=30
EOF
cat > /etc/systemd/system/lab-backup.timer <<'EOF'
[Unit]
Description=lab daily backup
[Timer]
OnCalendar=*-*-* 03:30:00
RandomizedDelaySec=900
Persistent=true
[Install]
WantedBy=timers.target
EOF
# No shared provisioning Postgres role: only root's fixed helper provisions.
systemctl enable --now postgresql
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "ALTER SYSTEM SET listen_addresses = 'localhost';"
systemctl restart postgresql
systemctl daemon-reload
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl enable --now caddy
systemctl restart caddy
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
systemctl enable --now unattended-upgrades
{
  date -u --iso-8601=seconds
  uname -a
  uv --version
  caddy version
  dpkg-query -W
  git -C "$REPO_DIR" rev-parse HEAD 2>/dev/null || true
} > /var/lib/lab/install-versions.txt
chmod 600 /var/lib/lab/install-versions.txt
printf '%s\n' 'Installed. Follow SETUP.md for DNS, keys, isolated integration and backup initialization.' \
  'Backup timer is deliberately NOT enabled until credentials and a restore drill pass.'
