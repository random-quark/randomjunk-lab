#!/usr/bin/python3 -I
"""Import staged credentials without printing values; run after core installation."""
import os
from pathlib import Path
import pwd
import stat
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bin/lib'))
from labcore import LabError, atomic_write, read_env

def secure_input(path):
    st=path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
        raise LabError('staged credentials must be root-owned regular files with mode 0600')
    return read_env(path)

def main():
    if os.geteuid()!=0:
        raise LabError('credential import requires root')
    source=Path('/root/lab-credentials'); target=Path('/etc/lab')
    providers=secure_input(source/'providers.env')
    required={'OPENAI_API_KEY','GEMINI_API_KEY','REPLICATE_API_TOKEN'}
    if not all(providers.get(k) for k in required):
        raise LabError('required provider keys missing')
    if set(providers)-required-{'ANTHROPIC_API_KEY','OPENROUTER_API_KEY'}:
        raise LabError('unrecognized provider key names')
    notification=secure_input(source/'ntfy.env')
    if notification.get('NTFY_URL')!='https://ntfy.sh' or not notification.get('NTFY_TOPIC'):
        raise LabError('hosted ntfy configuration missing')
    current=read_env(target/'secrets.env')
    current.update(providers)
    atomic_write(target/'secrets.env',''.join(k+'='+v+'\n' for k,v in sorted(current.items())))
    atomic_write(target/'notify.env',''.join(k+'='+notification[k]+'\n' for k in ('NTFY_URL','NTFY_TOPIC')))
    os.chown(target/'notify.env',0,pwd.getpwnam('lab').pw_gid)
    (target/'notify.env').chmod(0o640)
    backup=read_env(target/'backup.env')
    backup.update({k:notification[k] for k in ('NTFY_URL','NTFY_TOPIC')})
    atomic_write(target/'backup.env',''.join(k+'='+v+'\n' for k,v in sorted(backup.items())))
    print('Imported provider key names: '+', '.join(sorted(providers)))
    print('Hosted ntfy configured for lab and backup alerts; values hidden.')

if __name__=='__main__':
    main()
