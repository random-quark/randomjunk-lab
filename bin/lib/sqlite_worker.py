#!/usr/bin/python3 -I
"""Unprivileged SQLite enumeration/snapshot worker. Output contains database data."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from urllib.parse import quote

def snapshot(source, destination):
    # URI metacharacters are encoded; no filenames are inserted into SQL.
    uri = 'file:' + quote(str(Path(source).absolute()), safe='/') + '?mode=ro'
    with sqlite3.connect(uri) as src, sqlite3.connect(str(destination)) as dst:
        src.backup(dst)

def main():
    if os.geteuid() == 0:
        raise SystemExit('SQLite worker must run as an app runtime identity')
    operation, directory, *args = sys.argv[1:]
    root = Path(directory)
    if operation == 'list':
        found = []
        def failed(error):
            raise error
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=failed):
            for filename in files:
                path = Path(directory)/filename
                if path.suffix in ('.db', '.sqlite', '.sqlite3'):
                    if path.is_symlink() or not path.is_file():
                        raise ValueError('unsafe SQLite entry')
                    found.append(str(path.relative_to(root)))
        print(json.dumps(sorted(found)))
    elif operation == 'snapshot' and len(args) == 1:
        relative = Path(args[0])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('invalid SQLite path')
        source = root/relative
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError('SQLite path escapes data directory')
        with tempfile.TemporaryDirectory(prefix='lab-sqlite-') as temporary:
            destination = Path(temporary)/'snapshot.db'
            snapshot(source, destination)
            with destination.open('rb') as stream:
                shutil.copyfileobj(stream, sys.stdout.buffer)
    else:
        raise ValueError('unsupported SQLite worker operation')

if __name__ == '__main__':
    main()
