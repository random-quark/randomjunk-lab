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

def import_staged(source, target, lab_gid):
    """Validate selected files before writing; optional integrations are independent."""
    provider_path = source/'providers.env'
    notify_path = source/'ntfy.env'
    providers = notification = None
    if provider_path.exists() or provider_path.is_symlink():
        providers = secure_input(provider_path)
        allowed = {'OPENAI_API_KEY', 'GEMINI_API_KEY', 'REPLICATE_API_TOKEN',
                   'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY'}
        if not providers or set(providers)-allowed or not all(providers.values()):
            raise LabError('provider file must contain nonempty selected provider keys only')
    if notify_path.exists() or notify_path.is_symlink():
        notification = secure_input(notify_path)
        if (set(notification) != {'NTFY_URL', 'NTFY_TOPIC'} or
                notification.get('NTFY_URL') != 'https://ntfy.sh' or
                not notification.get('NTFY_TOPIC')):
            raise LabError('hosted ntfy configuration missing or unrecognized')
    if providers is None and notification is None:
        raise LabError('no staged integrations found; skip import if none were selected')
    # Read all affected destination files before any writes.
    current = read_env(target/'secrets.env') if providers is not None else None
    backup = read_env(target/'backup.env') if notification is not None else None
    if providers is not None:
        current.update(providers)
        atomic_write(target/'secrets.env', ''.join(k+'='+v+'\n' for k,v in sorted(current.items())))
        print('Imported provider key names: '+', '.join(sorted(providers)))
    if notification is not None:
        atomic_write(target/'notify.env', ''.join(k+'='+notification[k]+'\n' for k in ('NTFY_URL','NTFY_TOPIC')))
        os.chown(target/'notify.env', 0, lab_gid)
        (target/'notify.env').chmod(0o640)
        backup.update(notification)
        atomic_write(target/'backup.env', ''.join(k+'='+v+'\n' for k,v in sorted(backup.items())))
        print('Hosted ntfy configured for lab and legacy backup alerts; values hidden.')

def main():
    if os.geteuid() != 0:
        raise LabError('credential import requires root')
    import_staged(Path('/root/lab-credentials'), Path('/etc/lab'), pwd.getpwnam('lab').pw_gid)

if __name__ == '__main__':
    main()
