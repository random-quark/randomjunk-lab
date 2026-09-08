#!/usr/bin/python3 -I
"""Compare installed code with this checkout; print paths/results, never secrets."""
from pathlib import Path
import hashlib
import sys
ROOT=Path(__file__).resolve().parents[1]
pairs=[(ROOT/'sbin/labctl',Path('/usr/local/sbin/labctl')),
       (ROOT/'etc/lab-app@.service',Path('/etc/systemd/system/lab-app@.service')),
       (ROOT/'backup/lab-backup.sh',Path('/usr/local/bin/lab-backup')),
       (ROOT/'backup/lab-notify-root',Path('/usr/local/bin/lab-notify-root'))]
for name in ('newlab','labrm','labs','labdoctor','notify','labdev','labshot'):
    pairs.append((ROOT/'bin'/name,Path('/usr/local/bin')/name))
for source in (ROOT/'bin/lib').glob('*.py'):
    pairs.append((source,Path('/usr/local/lib/lab')/source.name))
for source in (ROOT/'templates').rglob('*'):
    if source.is_file() and not any(part in ('__pycache__','.venv') for part in source.parts):
        pairs.append((source,Path('/usr/local/share/lab/templates')/source.relative_to(ROOT/'templates')))
failed=[]
for source,installed in pairs:
    if not installed.is_file() or hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(installed.read_bytes()).digest():
        failed.append(str(installed))
if failed:
    print('MISMATCHES:\n'+'\n'.join(failed));raise SystemExit(1)
print(f'PASS: {len(pairs)} installed code/template files match source')
