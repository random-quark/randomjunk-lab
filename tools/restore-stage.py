#!/usr/bin/python3
"""Stage a v3 restore into a NEW isolated directory; never write installed paths.

Run against an already-restored restic snapshot tree. No services or commands
are executed. See docs/recovery.md for the stopped-resource activation sequence.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bin/lib'))
from labcore import LabError, name

def copy_regular_tree(source, destination):
    if source.is_symlink() or not source.is_dir():
        raise LabError('source must be a real directory')
    destination.mkdir(mode=0o700)
    for path in source.iterdir():
        target = destination/path.name
        if path.is_symlink():
            raise LabError('restore refuses symlinks; inspect and recreate intentionally')
        if path.is_dir():
            if path.name not in ('.venv', '__pycache__'):
                copy_regular_tree(path, target)
        elif stat.S_ISREG(path.stat().st_mode):
            shutil.copyfile(path, target)
        else:
            raise LabError('restore refuses special filesystem objects')

def stage(snapshot, generation, app, destination):
    name(app)
    if destination.exists() or destination.is_symlink():
        raise LabError('destination must not exist')
    snapshot = snapshot.resolve()
    if not generation.resolve().is_relative_to(snapshot):
        raise LabError('backup generation must be inside the restored snapshot')
    manifest = json.loads((generation/'manifest.json').read_text())
    if manifest['version'] != 3:
        raise LabError('unsupported backup format')
    entries = [item for item in manifest['apps'] if item['name'] == app]
    if len(entries) != 1:
        raise LabError('expected exactly one matching app in manifest')
    item = entries[0]
    source = snapshot/'srv/lab'/app
    destination.mkdir(mode=0o700)
    try:
        copy_regular_tree(source/'app', destination/'app')
        copy_regular_tree(source/'data', destination/'data')
        for entry in item['sqlite']:
            relative = Path(entry['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise LabError('invalid SQLite restore path')
            stored = Path(entry['snapshot'])
            if stored.name != str(stored) or not stored.name.startswith('sqlite-'):
                raise LabError('invalid snapshot filename')
            src = generation/stored
            if src.is_symlink() or not src.is_file():
                raise LabError('snapshot must be a regular file')
            target = destination/'data'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
            # A restored consistent snapshot must not be combined with stale WAL.
            for suffix in ('-wal', '-shm', '-journal'):
                Path(str(target)+suffix).unlink(missing_ok=True)
        if 'postgres' in item:
            stored = Path(item['postgres'])
            if stored.name != str(stored) or stored.name != f'pg-{app}.dump':
                raise LabError('invalid Postgres dump filename')
            src = generation/stored
            if src.is_symlink() or not src.is_file():
                raise LabError('dump must be a regular file')
            shutil.copyfile(src, destination/'postgres.dump')
        record = snapshot/'var/lib/lab/records'/f'{app}.json'
        shutil.copyfile(record, destination/'record.json')
        (destination/'RESTORE-NOTES.txt').write_text('Staged only. Validate contents; follow docs/recovery.md before installing.\n')
    except Exception:
        # Keep diagnostic output in the explicitly chosen isolated directory.
        (destination/'INCOMPLETE').write_text('Staging failed; do not install these files.\n')
        raise

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot', type=Path)
    p.add_argument('generation', type=Path)
    p.add_argument('app', type=name)
    p.add_argument('destination', type=Path)
    args = p.parse_args()
    stage(args.snapshot, args.generation, args.app, args.destination)
