#!/usr/bin/env bash
# Workspace-only tooling. Does not install the platform or edit shell profiles.
set -euo pipefail
REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
DEV_TOOLS="$REPO_DIR/.dev-tools"
mkdir -p "$DEV_TOOLS"
curl -fLsS https://astral.sh/uv/0.8.22/install.sh -o "$DEV_TOOLS/uv-install.sh"
UV_UNMANAGED_INSTALL="$DEV_TOOLS/uv" sh "$DEV_TOOLS/uv-install.sh"
case $(uname -m) in
  x86_64) CADDY_ARCH=amd64 ;;
  aarch64) CADDY_ARCH=arm64 ;;
  *) echo 'Caddy helper supports Linux x86_64/aarch64 only' >&2; exit 1 ;;
esac
CADDY_ARCHIVE="caddy_2.10.2_linux_${CADDY_ARCH}.tar.gz"
curl -fLsS "https://github.com/caddyserver/caddy/releases/download/v2.10.2/$CADDY_ARCHIVE" -o "$DEV_TOOLS/$CADDY_ARCHIVE"
curl -fLsS https://github.com/caddyserver/caddy/releases/download/v2.10.2/caddy_2.10.2_checksums.txt -o "$DEV_TOOLS/caddy-checksums.txt"
python3 - "$DEV_TOOLS" "$CADDY_ARCHIVE" <<'PY'
import hashlib, pathlib, sys, tarfile
root=pathlib.Path(sys.argv[1]); archive=root/sys.argv[2]
expected=next(line.split()[0] for line in (root/'caddy-checksums.txt').read_text().splitlines() if line.split()[-1]==archive.name)
if len(expected)!=128 or hashlib.sha512(archive.read_bytes()).hexdigest()!=expected:
    raise SystemExit('Caddy checksum mismatch; refusing extraction')
with tarfile.open(archive) as stream:
    binary=stream.extractfile('caddy').read()
(root/'caddy').write_bytes(binary);(root/'caddy').chmod(0o755)
PY
cd "$REPO_DIR"
"$DEV_TOOLS/uv/uv" sync --locked
printf '%s\n' 'Workspace tooling ready. See docs/development.md for test commands.'
