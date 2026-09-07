#!/usr/bin/python3
"""Parse source without installing or executing any platform scripts."""
import ast
from pathlib import Path
import subprocess
import tomllib
ROOT = Path(__file__).resolve().parents[1]
count=0
for path in sorted(ROOT.rglob('*')):
    if any(part in ('.git','.venv','__pycache__','.pytest_cache') for part in path.parts) or not path.is_file():
        continue
    data=path.read_bytes()
    if path.suffix=='.py' or data.startswith(b'#!/usr/bin/python3'):
        ast.parse(data.decode(),filename=str(path));count+=1
    elif data.startswith(b'#!/usr/bin/env bash'):
        subprocess.run(['bash','-n',str(path)],check=True);count+=1
    elif path.suffix=='.toml':
        tomllib.loads(data.decode());count+=1
print(f'PASS: {count} Python, shell and TOML source parse checks')
