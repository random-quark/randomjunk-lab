#!/usr/bin/python3 -I
"""Unprivileged convenience commands for installed experiments."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit

COMMON = Path('/usr/local/share/lab/templates/common/tools')

def main():
    command = sys.argv[1]
    parser = argparse.ArgumentParser(prog=command)
    parser.add_argument('name')
    if command == 'labbuild':
        parser.add_argument('--check', action='store_true')
    if command == 'labpreflight':
        parser.add_argument('--engines', nargs='+', choices=['chromium','webkit','firefox'], default=['chromium'])
    if command == 'labshot':
        parser.add_argument('--out')
        parser.add_argument('--viewport', default='390x844')
        parser.add_argument('--url', default='/', help='same-site path (default /)')
    args = parser.parse_args(sys.argv[2:])
    if os.geteuid() == 0:
        parser.error('run as lab, never root')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,22}[a-z0-9])', args.name):
        parser.error('invalid experiment name')
    root = Path('/srv/lab') / args.name / 'app'
    if not root.is_dir():
        parser.error('experiment app directory not found')
    if command == 'labbuild':
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from pwa_build import build
        try:
            changed = build(root/'public', check=args.check)
        except ValueError as error:
            parser.error(str(error))
        print('custom worker: freshness unmanaged' if not (root/'public/sw.template.js').exists() else ('built shell' if changed else 'shell is current'))
        return
    if command == 'labpreflight':
        python = root/'.venv/bin/python'
        if not python.exists():
            parser.error('missing environment: run uv sync --locked as lab in app/')
        os.execv(str(python), [str(python), str(COMMON/'preflight.py'), '--app-dir', str(root), '--engines', *args.engines])
    if command == 'labdev':
        os.execv('/usr/bin/python3', ['/usr/bin/python3', str(COMMON/'labdev.py'), '--app-dir', str(root)])
    metadata = root / 'lab.json'
    if metadata.exists():
        url = json.loads(metadata.read_text())['url']
    else:
        # Older experiments predate metadata; use only their documented HTTPS URL.
        match = re.search(r'https://[a-zA-Z0-9.-]+', (root/'install.md').read_text())
        if not match:
            parser.error('no URL in lab.json or install.md')
        url = match.group()
    parsed = urlsplit(args.url)
    if parsed.scheme or parsed.netloc or not args.url.startswith('/'):
        parser.error('--url must be a path on the experiment site')
    base = urlsplit(url)
    url = urlunsplit((base.scheme, base.netloc, parsed.path, parsed.query, ''))
    python = root / '.venv/bin/python'
    if not python.exists():
        parser.error('browser tooling missing: use a dev-enabled uv environment as documented')
    out = args.out or str(root/'artifacts/labshot')
    os.execv(str(python), [str(python), str(COMMON/'labshot.py'), url, '--out', out, '--viewport', args.viewport])

if __name__ == '__main__':
    main()
