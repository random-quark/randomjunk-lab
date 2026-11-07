#!/usr/bin/python3 -I
"""Enable invitation enrollment on an existing public static welcome app."""
import argparse
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bin/lib'))
from labcore import LabError, atomic_write, locked, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', default='welcome')
    args = parser.parse_args()
    app = name(args.app)
    if os.geteuid() != 0:
        raise LabError('The server administrator enables this once during setup.')
    account = pwd.getpwnam('lab')
    if account.pw_dir != '/home/lab':
        raise LabError('Review service paths for a nonstandard lab home.')
    record = json.loads((Path('/var/lib/lab/records') / (app + '.json')).read_text())
    if record['kind'] != 'static' or record['private'] or not record.get('public_revision'):
        raise LabError('Choose an existing published public static guide app.')
    for source, dest, mode in [
        (ROOT/'bin/lib/labcore.py', '/usr/local/lib/lab/labcore.py', '644'),
        (ROOT/'bin/lib/controller.py', '/usr/local/lib/lab/controller.py', '644'),
        (ROOT/'bin/lib/access.py', '/usr/local/lib/lab/access.py', '644'),
        (ROOT/'bin/lib/sshkeys.py', '/usr/local/lib/lab/sshkeys.py', '644'),
        (ROOT/'bin/lab-access', '/usr/local/bin/lab-access', '755'),
        (ROOT/'etc/lab-access.service', '/etc/systemd/system/lab-access.service', '644')]:
        subprocess.run(['install', '-o', 'root', '-g', 'root', '-m', mode, str(source), dest], check=True)
    subprocess.run(['runuser', '-u', 'lab', '--', '/usr/bin/python3', '-I', '-c',
                    "from pathlib import Path; p=Path.home()/'.ssh'; p.mkdir(mode=0o700,exist_ok=True); assert not p.is_symlink()"],
                   check=True, env={'PATH': '/usr/bin:/bin', 'HOME': account.pw_dir})
    with locked(Path('/var/lib/lab/lock')):
        path = Path('/etc/lab/platform.json')
        config = json.loads(path.read_text())
        config['access_app'] = app
        atomic_write(Path('/etc/lab/access.json'), json.dumps({'welcome_url': f'https://{app}.{config["domain"]}'}), 0o644)
        atomic_write(path, json.dumps(config), 0o600)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'lab-access.service'], check=True)
    subprocess.run(['systemctl', 'restart', 'lab-access.service'], check=True)
    # Normal publication validates and reloads the managed Caddy candidate.
    subprocess.run(['runuser', '-u', 'lab', '--', 'sudo', '/usr/local/sbin/labctl', 'publish', app], check=True)
    print('Invitation enrollment enabled. As lab, run: lab-access invite')


if __name__ == '__main__':
    try:
        main()
    except LabError as exc:
        print(str(exc), file=sys.stderr); sys.exit(1)
