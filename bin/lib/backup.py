"""Root backup orchestrator. SQLite engines run only as runtime users."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from controller import Controller, SAFE_ENV
from labcore import LabError, locked, protected_dir, read_env, write_json

REQUIRED = ('B2_ENDPOINT', 'B2_BUCKET', 'B2_KEY_ID', 'B2_APP_KEY', 'RESTIC_PASSWORD')

def backup_environment(config):
    if any(not config.get(key) for key in REQUIRED):
        raise LabError('backup configuration is incomplete')
    return dict(SAFE_ENV, RESTIC_REPOSITORY=f's3:{config["B2_ENDPOINT"]}/{config["B2_BUCKET"]}/lab',
                AWS_ACCESS_KEY_ID=config['B2_KEY_ID'], AWS_SECRET_ACCESS_KEY=config['B2_APP_KEY'],
                RESTIC_PASSWORD=config['RESTIC_PASSWORD'])

def checked(args, *, env, output=None):
    result = subprocess.run([str(a) for a in args], env=env, stdout=output or subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=7200)
    if result.returncode:
        raise LabError(f'{Path(args[0]).name} backup step failed (exit {result.returncode})')

def perform(ctl, destination):
    config = read_env(ctl.etc/'backup.env')
    env = backup_environment(config)
    protected_dir(destination)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    generation = destination/stamp
    generation.mkdir(mode=0o700)
    manifest = {'version': 3, 'created': stamp, 'apps': []}
    # Incomplete generations are deliberately retained for diagnosis, never
    # referenced by a successful manifest or reused on the next run.
    with (generation/'globals.sql').open('wb') as output:
        checked(['/usr/sbin/runuser', '-u', 'postgres', '--', 'pg_dumpall', '--globals-only'], env=env, output=output)
    for path in sorted((ctl.state/'records').glob('*.json')):
        rec = ctl.record(path.stem)
        if rec['status'] not in ('http-verified', 'created', 'verification-pending'):
            raise LabError(f'{rec["name"]}: incomplete lifecycle; backup needs operator attention')
        app = rec['name']
        item = {'name': app, 'db': rec['db'], 'sqlite': []}
        worker = ['/usr/sbin/runuser', '-u', ctl.username(app), '--', '/usr/bin/python3', '-I', ctl.lib/'sqlite_worker.py']
        # Enumerate inside the runtime privilege boundary. Failure is checked.
        listed = subprocess.run([str(a) for a in worker + ['list', ctl.root/app/'data']], env=SAFE_ENV, capture_output=True, text=True, timeout=60)
        if listed.returncode:
            raise LabError(f'{app}: SQLite enumeration failed')
        for relative in json.loads(listed.stdout):
            digest = hashlib.sha256((app+'\0'+relative).encode()).hexdigest()
            filename = f'sqlite-{digest}.db'
            with (generation/filename).open('wb') as output:
                checked(worker + ['snapshot', ctl.root/app/'data', relative], env=SAFE_ENV, output=output)
            item['sqlite'].append({'path': relative, 'snapshot': filename})
        if rec['db'] == 'postgres':
            filename = f'pg-{app}.dump'
            with (generation/filename).open('wb') as output:
                checked(['/usr/sbin/runuser', '-u', 'postgres', '--', 'pg_dump', '--format=custom', '--no-owner', '--no-acl', '--dbname', 'lab_'+app.replace('-', '_')], env=env, output=output)
            item['postgres'] = filename
        manifest['apps'].append(item)
    write_json(generation/'manifest.json', manifest)
    checked(['restic', 'backup', '--tag', 'lab-v3', '--exclude', '**/.venv', '--exclude', '**/__pycache__', '--exclude', '**/node_modules',
             ctl.root, ctl.public, generation, ctl.etc, ctl.state, '/etc/caddy', '/var/lib/caddy', ctl.units/'lab-app@.service',
             *sorted(ctl.units.glob('lab-app@*.service.d'))], env=env)
    checked(['restic', 'forget', '--tag', 'lab-v3', '--group-by', 'host,tags', '--keep-daily', '7', '--keep-weekly', '4', '--keep-monthly', '6', '--prune'], env=env)
    checked(['restic', 'check', '--read-data-subset=1%'], env=env)
    write_json(destination/'last-success.json', {'generation': stamp})
    # Only after a successful remote backup/check remove old local generations.
    for old in destination.iterdir():
        if old.is_dir() and not old.is_symlink() and old != generation:
            shutil.rmtree(old)

def main():
    os.umask(0o077)
    try:
        if os.geteuid() != 0:
            raise LabError('backup orchestrator requires root')
        ctl = Controller()
        for directory in (ctl.state, ctl.state/'records', ctl.etc):
            protected_dir(directory)
        with locked(ctl.state/'lock'):
            perform(ctl, Path('/var/backups/lab'))
        return 0
    except Exception:
        # Don't include exception details that could contain credentials or DB
        # contents. Explicit catch covers missing config and worker failures.
        print('lab-backup: FAILED; inspect configuration, metadata and backup service locally', file=sys.stderr)
        if os.environ.get('LAB_BACKUP_ONFAILURE') == '1':
            return 1  # systemd OnFailure also covers timeout, signal and OOM exits
        try:
            subprocess.run(['/usr/local/bin/lab-notify-root', 'Lab backup FAILED', 'Backup did not complete; inspect lab-backup.service'], env=SAFE_ENV, timeout=20, check=False)
        except Exception:
            print('lab-backup: failure notification also failed', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
