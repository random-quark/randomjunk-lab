#!/usr/bin/python3 -I
"""Apply the reviewed 2026-09-09 helper/template/docs update, not bootstrap.

Run only from the trusted root-owned reviewed platform checkout. Backs up replaced
installed files under /root/workspaces/labserver-review/deployments. Does not touch
app source/data, credentials, Caddy sites or systemd services.
"""
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'bin/lib'))
from labcore import atomic_write, locked

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if os.geteuid()!=0 or not args.apply:
        parser.error('administrator must explicitly use --apply')
    pairs=[]
    for source in (ROOT/'bin/lib').glob('*.py'):
        pairs.append((source,Path('/usr/local/lib/lab')/source.name,0o644))
    for name in ('labdev','labshot','labbuild','labpreflight'):
        pairs.append((ROOT/'bin'/name,Path('/usr/local/bin')/name,0o755))
    for source in (ROOT/'templates').rglob('*'):
        if source.is_file() and not any(p in ('.venv','__pycache__') for p in source.parts):
            pairs.append((source,Path('/usr/local/share/lab/templates')/source.relative_to(ROOT/'templates'),0o644))
    for source in (ROOT/'docs').glob('*.md'):
        pairs.append((source,Path('/usr/local/share/lab/docs')/source.name,0o644))
    for target in ('/srv/lab/AGENTS.md','/srv/lab/CLAUDE.md','/home/lab/AGENTS.md'):
        pairs.append((ROOT/'templates/operating-instructions.md',Path(target),0o644))
    obsolete=[Path('/usr/local/share/lab/templates')/kind/'public/sw.js' for kind in ('app','static')]
    parent=ROOT.parent/'deployments';parent.mkdir(exist_ok=True)
    backup=Path(tempfile.mkdtemp(prefix='feedback-',dir=parent))
    manifest=[]
    with locked(Path('/var/lib/lab/lock')):
        # Backups retain ownership/mode information for administrator-led rollback.
        for target in [p[1] for p in pairs]+obsolete:
            row={'path':str(target),'existed':target.exists()}
            if target.exists():
                info=target.stat();row.update(uid=info.st_uid,gid=info.st_gid,mode=info.st_mode&0o777)
                dest=backup/target.relative_to('/');dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(target,dest)
            manifest.append(row)
        (backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
        for source,target,mode in pairs:
            target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
            atomic_write(target,source.read_bytes(),mode)
            if str(target)=='/home/lab/AGENTS.md':
                account=pwd.getpwnam('lab');os.chown(target,account.pw_uid,account.pw_gid)
        for target in obsolete:
            target.unlink(missing_ok=True)
    print('Applied reviewed helpers/templates/docs; prior files:',backup)

if __name__=='__main__':
    main()
