#!/usr/bin/python3 -I
"""Install reviewed hostname helpers only; preserve a root-owned rollback copy."""
import json, os, shutil, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin/lib'))
from labcore import atomic_write, locked, protected_dir
if os.geteuid()!=0:raise SystemExit('Administrator execution required')
protected_dir(ROOT);protected_dir(ROOT/'bin/lib');protected_dir(Path('/usr/local/lib/lab'))
backup=Path(tempfile.mkdtemp(prefix='hostnames-',dir=ROOT.parent/'deployments'))
with locked(Path('/var/lib/lab/lock')):
    for name in ('labcore.py','controller.py'):
        target=Path('/usr/local/lib/lab')/name
        shutil.copy2(target,backup/name)
        atomic_write(target,(ROOT/'bin/lib'/name).read_bytes(),0o644)
print('Installed hostname helpers; rollback copies:',backup)
