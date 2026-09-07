"""Serialized root authority. App code and dependency tooling run only as lab.

See docs/security.md and docs/development.md before changing this boundary.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import base64
from labcore import (LabError, VERSION, atomic_write, caddy_site, domain, keys,
                     locked, name, protected_dir, read_env, systemd_env, write_json)

SAFE_ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
            'LANG': 'C.UTF-8', 'HOME': '/root', 'SYSTEMD_PAGER': 'cat',
            'SYSTEMD_COLORS': '0', 'PAGER': 'cat'}

class Controller:
    def __init__(self):
        self.root = Path('/srv/lab')
        self.state = Path('/var/lib/lab')
        self.public = Path('/var/lib/lab-public')
        self.etc = Path('/etc/lab')
        self.units = Path('/etc/systemd/system')
        self.caddy = Path('/etc/caddy')
        self.templates = Path('/usr/local/share/lab/templates')
        self.lib = Path('/usr/local/lib/lab')

    def run(self, args, *, user=None, data=None, check=True, quiet=False, cwd=None):
        args = [str(arg) for arg in args]
        if user:
            args = ['/usr/sbin/runuser', '-u', user, '--', *args]
        result = subprocess.run(args, input=data, text=True, capture_output=True,
                                env=SAFE_ENV, cwd=cwd, timeout=600)
        if check and result.returncode:
            # SQL/env/dependency errors may contain credentials: don't echo output.
            raise LabError(f'{Path(args[0]).name} failed (exit {result.returncode}); inspect locally with care')
        return result

    def config(self):
        config = json.loads((self.etc/'platform.json').read_text())
        if config.get('version') != VERSION:
            raise LabError('unsupported platform version; follow migration documentation')
        domain(config['domain'])
        mode = config.get('tls_mode', 'production')
        if mode not in ('production', 'internal') or (mode == 'internal' and not config['domain'].endswith('.test')):
            raise LabError('invalid TLS mode: internal TLS requires a .test domain')
        return config

    def path(self, app):
        return self.state/'records'/f'{name(app)}.json'

    def save(self, rec):
        write_json(self.path(rec['name']), rec)

    def record(self, app):
        try:
            rec = json.loads(self.path(app).read_text())
            if rec['version'] != VERSION or rec['name'] != app or rec['kind'] not in ('app', 'static') or rec['db'] not in ('none', 'sqlite', 'postgres'):
                raise ValueError()
            if not isinstance(rec['resources'], dict) or not isinstance(rec['grants'], list):
                raise ValueError()
            keys(','.join(rec['grants']))
            return rec
        except (ValueError, KeyError, TypeError) as exc:
            raise LabError(f'invalid record for {app}; restore metadata before mutation') from exc

    def unit(self, app):
        return f'lab-app@{name(app)}.service'

    def username(self, app):
        return f'labapp-{name(app)}'

    def dropin(self, app):
        return self.units/(self.unit(app)+'.d')

    def environment_values(self, rec):
        values = {'APP_NAME': rec['name'], 'PORT': str(rec['port'] or '')}
        if rec['db'] == 'sqlite':
            values['DATABASE_URL'] = f'sqlite:///{self.root}/{rec["name"]}/data/{rec["name"]}.db'
        if rec['db'] == 'postgres':
            cred = json.loads((self.state/'credentials'/f'{rec["name"]}.json').read_text())
            values['DATABASE_URL'] = cred['DATABASE_URL']
        master = read_env(self.etc/'secrets.env') if rec['grants'] else {}
        for key in rec['grants']:
            if key not in master or not master[key]:
                raise LabError(f'missing or empty master key: {key}')
            values[key] = master[key]
        return systemd_env(values)

    def environment(self, rec):
        atomic_write(self.etc/'apps'/f'{rec["name"]}.env', self.environment_values(rec))

    def service_identity(self, rec):
        app = rec['name']
        user = self.username(app)
        expected = f'[Service]\nUser={user}\nGroup={user}\n'
        directory = self.dropin(app)
        directory.mkdir(mode=0o755, exist_ok=True)
        protected_dir(directory)
        atomic_write(directory/'identity.conf', expected, 0o644)
        self.run(['systemctl', 'daemon-reload'])

    def check_identity(self, rec):
        app = rec['name']
        if rec['kind'] != 'app' or not rec['resources'].get('identity'):
            raise LabError('app service has not been provisioned')
        user = self.username(app)
        try:
            account = pwd.getpwnam(user)
        except KeyError as exc:
            raise LabError('runtime user missing') from exc
        if account.pw_uid == 0 or account.pw_gid == 0:
            raise LabError('unsafe runtime identity')
        protected_dir(self.dropin(app))
        identity = self.dropin(app)/'identity.conf'
        if identity.is_symlink() or not identity.is_file() or identity.stat().st_uid != 0 or identity.stat().st_mode & 0o022 or identity.read_text() != f'[Service]\nUser={user}\nGroup={user}\n':
            raise LabError('missing or invalid identity drop-in')
        actual = self.run(['systemctl', 'show', self.unit(app), '-p', 'User', '-p', 'Group', '--value']).stdout.splitlines()
        if len(actual) != 2 or any(value != user for value in actual):
            raise LabError('effective systemd identity does not match provisioned runtime')
        env = self.etc/'apps'/f'{app}.env'
        st = env.lstat()
        import stat
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
            raise LabError('unsafe runtime environment file')

    def service(self, action, app):
        rec = self.record(app)
        if action in ('start', 'restart', 'enable'):
            self.check_identity(rec)
        if action == 'enable':
            self.run(['systemctl', 'enable', self.unit(app)])
            self.run(['systemctl', 'start', self.unit(app)])
        elif action == 'disable':
            self.stop(rec)
            self.run(['systemctl', 'disable', self.unit(app)])
        else:
            result = self.run(['systemctl', action, self.unit(app)], check=False)
            if action in ('status', 'is-active'):
                print(result.stdout, end='')
            return result.returncode
        return 0

    def stop(self, rec):
        if rec['kind'] != 'app':
            return
        self.run(['systemctl', 'stop', self.unit(rec['name'])])
        result = self.run(['systemctl', 'show', self.unit(rec['name']), '-p', 'ActiveState', '--value'])
        if result.stdout.strip() not in ('inactive', 'failed'):
            raise LabError('service not stopped; refusing destructive cleanup')

    def sql(self, statement, db='postgres'):
        return self.run(['psql', '-X', '--no-password', '-v', 'ON_ERROR_STOP=1', '-tA', '-d', db],
                        user='postgres', data=statement)

    def db_create(self, rec):
        app = rec['name']
        db = 'lab_' + app.replace('-', '_')
        # A creating record owns these names only after confirming they were absent.
        if self.sql(f"SELECT 1 FROM pg_roles WHERE rolname='{db}';").stdout.strip() or self.sql(f"SELECT 1 FROM pg_database WHERE datname='{db}';").stdout.strip():
            raise LabError('database/role already exists; refuse to adopt or rotate it')
        rec['resources']['postgres_intent'] = True
        self.save(rec)
        password = secrets.token_hex(24)
        write_json(self.state/'credentials'/f'{app}.json', {
            'DATABASE_URL': f'postgresql+psycopg://{db}:{password}@127.0.0.1:5432/{db}'})
        self.sql(f'CREATE ROLE "{db}" LOGIN PASSWORD \'{password}\';')
        self.sql(f'CREATE DATABASE "{db}" OWNER "{db}";')
        # --db postgres promises pgvector, so fail visibly when unavailable.
        self.sql('CREATE EXTENSION IF NOT EXISTS vector;', db)
        rec['resources']['postgres'] = True
        self.save(rec)

    def caddy_publish(self, records):
        """Validate an isolated complete candidate, then atomically switch it.

        One generated file is the complete imported site set. No arbitrary
        caller-supplied paths, Caddy text, or lab-writable staged files.
        """
        canonical = '{\n\tadmin unix//run/caddy/admin.sock\n\tskip_install_trust\n}\nimport /etc/caddy/lab-sites.caddy\n'
        if (self.caddy/'Caddyfile').read_text() != canonical:
            raise LabError('top-level Caddyfile differs from managed configuration; inspect before publication')
        dom = self.config()['domain']
        sites = ''.join(caddy_site(rec, dom, self.root, self.public, self.config().get('tls_mode', 'production')) for rec in sorted(records, key=lambda item: item['name']))
        header = '{\n\tadmin unix//run/caddy/admin.sock\n\tskip_install_trust\n}\n'
        candidate = self.state/'caddy-candidate'
        atomic_write(candidate, header + sites, 0o600)
        self.run(['caddy', 'validate', '--config', candidate, '--adapter', 'caddyfile'])
        live = self.caddy/'lab-sites.caddy'
        previous = live.read_bytes()
        atomic_write(live, sites, 0o644)
        reload_command = ['caddy', 'reload', '--config', self.caddy/'Caddyfile', '--adapter', 'caddyfile', '--address', 'unix//run/caddy/admin.sock']
        try:
            failed = self.run(reload_command, check=False).returncode != 0
        except (subprocess.TimeoutExpired, OSError):
            failed = True
        if failed:
            atomic_write(live, previous, 0o644)
            try:
                rollback_failed = self.run(reload_command, check=False).returncode != 0
            except (subprocess.TimeoutExpired, OSError):
                rollback_failed = True
            raise LabError('Caddy reload failed; old file restored' + ('; rollback reload ALSO failed: operator action required' if rollback_failed else ' and reloaded'))
        candidate.unlink(missing_ok=True)

    def published(self, exclude=None):
        result = []
        for path in sorted((self.state/'records').glob('*.json')):
            rec = self.record(path.stem)
            if rec['name'] != exclude and rec['resources'].get('caddy'):
                result.append(rec)
        return result

    def allocate_port(self):
        used = {self.record(p.stem)['port'] for p in (self.state/'records').glob('*.json')}
        for port in range(8100, 8999):
            if port in used:
                continue
            with socket.socket() as sock:
                try:
                    sock.bind(('127.0.0.1', port))
                except OSError:
                    continue
            return port
        raise LabError('no available application port')

    def create(self, args):
        app = name(args.name)
        config = self.config()
        if args.db != 'none' and args.kind != 'app' or args.secrets and args.kind != 'app':
            raise LabError('database and secret options require --app')
        grants = keys(args.secrets)
        if len(args.title or app) > 160 or any(ord(c) < 32 for c in (args.title or app)):
            raise LabError('title must be a single line, at most 160 characters')
        container = self.root/app
        if self.path(app).exists() or os.path.lexists(container):
            raise LabError('app or record exists; inspect with labdoctor')
        if self.dropin(app).exists() or (self.etc/'apps'/f'{app}.env').exists():
            raise LabError('orphan service metadata exists; reconcile before creation')
        try:
            pwd.getpwnam(self.username(app))
        except KeyError:
            pass
        else:
            raise LabError('runtime user already exists; refusing to adopt it')
        rec = {'version': VERSION, 'name': app, 'kind': args.kind, 'db': args.db,
               'private': args.private, 'title': args.title or app, 'grants': grants,
               'port': self.allocate_port() if args.kind == 'app' else None,
               'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'status': 'creating', 'resources': {}}
        self.save(rec)
        try:
            rec['resources']['identity_intent'] = True
            self.save(rec)
            self.run(['useradd', '--system', '--user-group', '--no-create-home', '--shell', '/usr/sbin/nologin', self.username(app)])
            runtime = pwd.getpwnam(self.username(app))
            deployer = pwd.getpwnam('lab')
            container.mkdir(mode=0o755)
            container.chmod(0o755)
            (container/'app').mkdir(mode=0o755)
            (container/'app').chmod(0o755)
            os.chown(container/'app', deployer.pw_uid, deployer.pw_gid)
            (container/'data').mkdir(mode=0o700)
            os.chown(container/'data', runtime.pw_uid, runtime.pw_gid)
            rec['resources']['identity'] = True
            self.save(rec)
            # Only this fixed trusted worker is invoked. Its entire process,
            # including uv/build hooks and all app-owned paths, runs as lab.
            self.run(['/usr/bin/python3', '-I', self.lib/'scaffold.py', str(self.templates/args.kind),
                      str(container/'app'), app, rec['title'], f'https://{app}.{config["domain"]}', config['domain'], args.db], user='lab')
            rec['resources']['code'] = True
            self.save(rec)
            if args.db == 'postgres':
                self.db_create(rec)
            if args.kind == 'app':
                self.environment(rec)
                self.service_identity(rec)
            if args.private:
                password = secrets.token_urlsafe(24)
                # Feed password on stdin, not process argv.
                hashed = self.run(['caddy', 'hash-password'], data=password+'\n').stdout.strip()
                rec['auth_hash'] = hashed
                atomic_write(self.state/'credentials'/f'{app}.basic', password)
            rec['status'] = 'prepared'
            self.save(rec)
            if args.prepare_only:
                print(f'{app}: prepared without startup or Caddy publication; follow docs/recovery.md')
            else:
                self.publish(app)
        except Exception:
            # Never blindly destroy data on failed creation. Each acquisition
            # has an intent record, including crash windows.
            rec = self.record(app)
            rec['status'] = 'create-failed'
            self.save(rec)
            raise

    def snapshots(self, app):
        # Exact suffix prevents app "aa" from matching "aa-other" snapshots.
        return [path for path in self.public.iterdir()
                if re.fullmatch(re.escape(name(app)) + r'-[a-f0-9]{32}', path.name)]

    def snapshot_public(self, rec):
        # Root never opens the deployment tree. The fixed worker reads as lab
        # and only regular-file bytes enter the root-owned snapshot directory.
        result = self.run(['/usr/bin/python3', '-I', self.lib/'export_public.py',
                           self.root/rec['name']/'app/public'], user='lab')
        entries = json.loads(result.stdout)
        if not isinstance(entries, list) or len(entries) > 10000:
            raise LabError('invalid static export')
        revision = secrets.token_hex(16)
        target = self.public/(rec['name']+'-'+revision)
        target.mkdir(mode=0o755)
        target.chmod(0o755)
        total = 0
        try:
            for entry in entries:
                relative = Path(entry['path'])
                if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                    raise LabError('invalid static export path')
                data = base64.b64decode(entry['data'], validate=True)
                total += len(data)
                if total > 64 * 1024 * 1024:
                    raise LabError('static export exceeds 64 MiB')
                destination = target/relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                for parent in destination.parents:
                    if parent == self.public:
                        break
                    parent.chmod(0o755)
                atomic_write(destination, data, 0o644)
            if not (target/'index.html').is_file():
                raise LabError('static publication requires index.html')
        except Exception:
            shutil.rmtree(target)
            raise
        return revision

    def publish(self, app):
        rec = self.record(app)
        if rec['status'] in ('removing', 'removal-failed') or not rec['resources'].get('code'):
            raise LabError('app is not prepared for publication')
        new_snapshot = None
        if rec['kind'] == 'static':
            new_snapshot = self.snapshot_public(rec)
            rec['public_revision'] = new_snapshot
        if rec['kind'] == 'app':
            self.environment(rec)
            self.service('enable', app)
            rec['resources']['service'] = True
            self.save(rec)
            if not self.wait_http(f'http://127.0.0.1:{rec["port"]}/api/health', timeout=45, expected_app=app):
                raise LabError('backend liveness failed; resources retained for diagnosis')
        intent = self.record(app)
        intent['resources']['caddy_intent'] = True
        self.save(intent)
        try:
            self.caddy_publish(self.published(exclude=app) + [rec])
        except Exception:
            if new_snapshot:
                shutil.rmtree(self.public/(app+'-'+new_snapshot))
            raise
        rec['resources']['caddy_intent'] = True
        rec['resources']['caddy'] = True
        rec['status'] = 'created'
        self.save(rec)
        if new_snapshot:
            for old in self.snapshots(app):
                if old.name != app+'-'+new_snapshot:
                    protected_dir(old)
                    shutil.rmtree(old)
        if not self.verify(app):
            raise LabError('published but HTTPS verification failed; inspect and run labctl verify')
        print(f'HTTP-verified: https://{app}.{self.config()["domain"]}')
        print(f'Code: {self.root}/{app}/app. Application behavior still needs testing.')
        if rec['private']:
            print(f'Basic-auth password: root-only {self.state}/credentials/{app}.basic')

    def wait_http(self, url, *, timeout=30, password=None, expected_app=None):
        headers = {}
        if password:
            headers['Authorization'] = 'Basic ' + base64.b64encode(('lab:'+password).encode()).decode()
        # Don't send private readiness credentials to redirects or env proxies.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        context = ssl.create_default_context()
        if self.config().get('tls_mode') == 'internal':
            context.load_verify_locations('/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPSHandler(context=context))
        deadline = time.monotonic() + timeout
        while True:
            try:
                with opener.open(urllib.request.Request(url, headers=headers), timeout=min(5, timeout)) as response:
                    if response.status == 200:
                        if expected_app:
                            body = json.loads(response.read(65536))
                            return isinstance(body, dict) and body.get('ok') is True and body.get('app') == expected_app
                        return True
            except (OSError, urllib.error.URLError, ValueError):
                pass
            if time.monotonic() >= deadline:
                return False
            time.sleep(1)

    def verify(self, app):
        rec = self.record(app)
        if not rec['resources'].get('caddy'):
            raise LabError('app is not published; cannot mark HTTP-verified')
        password = (self.state/'credentials'/f'{app}.basic').read_text() if rec['private'] else None
        ok = self.wait_http(f'https://{app}.{self.config()["domain"]}', password=password)
        if rec['kind'] == 'app':
            self.check_identity(rec)
            ok = ok and self.run(['systemctl', 'is-active', self.unit(app)], check=False).returncode == 0
            ok = ok and self.wait_http(f'http://127.0.0.1:{rec["port"]}/api/health', expected_app=app)
        rec['https'] = 'ok' if ok else 'pending'
        rec['status'] = 'http-verified' if ok else 'verification-pending'
        self.save(rec)
        return ok

    def grant(self, app, requested):
        rec = self.record(app)
        if rec['kind'] != 'app':
            raise LabError('secret grants require a backend')
        rec['grants'] = sorted(set(rec['grants']) | set(keys(requested)))
        rendered = self.environment_values(rec)  # validate before changing anything
        previous_status = rec['status']
        rec['status'] = 'environment-pending'
        self.save(rec)  # authoritative desired grants survive interrupted env writes
        atomic_write(self.etc/'apps'/f'{app}.env', rendered)
        rec['status'] = previous_status if previous_status != 'environment-pending' else 'verification-pending'
        self.save(rec)
        print('Grants merged; restart the app to apply them.')

    def remove(self, app):
        if not self.path(app).exists():
            # Repeated removal is safe only when namespace resources are absent.
            if os.path.lexists(self.root/app) or self.dropin(app).exists() or (self.etc/'apps'/f'{app}.env').exists():
                raise LabError('orphan resources without metadata; restore record before removal')
            if self.snapshots(app):
                raise LabError('orphan static snapshot; restore metadata before removal')
            try:
                pwd.getpwnam(self.username(app))
            except KeyError:
                pass
            else:
                raise LabError('orphan runtime identity; restore metadata before removal')
            print(f'{app}: no record or filesystem resources; labdoctor audits database orphans')
            return
        rec = self.record(app)
        rec['status'] = 'removing'
        self.save(rec)
        try:
            self.stop(rec)  # Failure blocks ALL destructive dependent operations.
            if rec['kind'] == 'app':
                self.run(['systemctl', 'disable', self.unit(app)])
            if rec['resources'].get('caddy') or rec['resources'].get('caddy_intent'):
                self.caddy_publish(self.published(exclude=app))
                rec['resources']['caddy'] = False
                rec['resources']['caddy_intent'] = False
                self.save(rec)
            if rec['resources'].get('postgres_intent'):
                db = 'lab_' + app.replace('-', '_')
                self.sql(f'DROP DATABASE IF EXISTS "{db}" WITH (FORCE);')
                self.sql(f'DROP ROLE IF EXISTS "{db}";')
                rec['resources']['postgres_intent'] = False
                rec['resources']['postgres'] = False
                self.save(rec)
            # /srv/lab and container are root-owned; rmtree uses fd-based
            # traversal and must never fall back to a symlink-unsafe platform.
            if not shutil.rmtree.avoids_symlink_attacks:
                raise LabError('platform lacks safe recursive deletion')
            container = self.root/app
            if os.path.lexists(container):
                protected_dir(container)
                shutil.rmtree(container)
            if self.dropin(app).exists():
                protected_dir(self.dropin(app))
                shutil.rmtree(self.dropin(app))
            (self.etc/'apps'/f'{app}.env').unlink(missing_ok=True)
            self.run(['systemctl', 'daemon-reload'])
            if rec['resources'].get('identity_intent'):
                try:
                    pwd.getpwnam(self.username(app))
                except KeyError:
                    pass
                else:
                    self.run(['userdel', self.username(app)])
            for snapshot in self.snapshots(app):
                protected_dir(snapshot)
                shutil.rmtree(snapshot)
            for suffix in ('.json', '.basic'):
                (self.state/'credentials'/f'{app}{suffix}').unlink(missing_ok=True)
            self.path(app).unlink()  # last; failed cleanup keeps retry metadata
            print(f'{app}: removed; retained backups are unaffected')
        except Exception:
            rec['status'] = 'removal-failed'
            self.save(rec)
            raise

    def doctor(self):
        problems = []
        records = {}
        for path in (self.state/'records').glob('*.json'):
            try:
                rec = self.record(path.stem)
                records[path.stem] = rec
                if rec['status'] != 'http-verified':
                    problems.append(f'{path.stem}: {rec["status"]}')
                for directory in (self.root/path.stem, self.root/path.stem/'app', self.root/path.stem/'data'):
                    if not directory.is_dir():
                        problems.append(f'{path.stem}: missing {directory.name}')
                if rec['kind'] == 'app':
                    self.check_identity(rec)
                    if self.run(['systemctl', 'is-active', self.unit(path.stem)], check=False).returncode:
                        problems.append(f'{path.stem}: service not active')
                if (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(rec['created'])).days > 90:
                    problems.append(f'{path.stem}: older than 90 days')
            except (LabError, OSError, ValueError, KeyError, TypeError) as exc:
                problems.append(f'{path.name}: {exc}')
        known = set(records)
        for directory in self.root.iterdir():
            if directory.name in ('AGENTS.md', 'CLAUDE.md'):
                continue
            if directory.name not in known:
                problems.append(f'orphan app entry: {directory.name}')
        for path in self.units.glob('lab-app@*.service.d'):
            if path.name[len('lab-app@'):-len('.service.d')] not in known:
                problems.append(f'orphan unit: {path.name}')
        for path in (self.etc/'apps').glob('*.env'):
            if path.stem not in known:
                problems.append(f'orphan env: {path.name}')
        expected_snapshots = {app+'-'+r['public_revision'] for app, r in records.items() if r.get('public_revision')}
        for path in self.public.iterdir():
            if path.name not in expected_snapshots:
                problems.append(f'orphan static snapshot: {path.name}')
        for snapshot in expected_snapshots:
            if not (self.public/snapshot).is_dir():
                problems.append(f'missing static snapshot: {snapshot}')
        for path in (self.state/'credentials').iterdir():
            if path.stem not in known:
                problems.append(f'orphan credential file: {path.name}')
        for account in pwd.getpwall():
            if account.pw_name.startswith('labapp-') and account.pw_name[7:] not in known:
                problems.append(f'orphan identity: {account.pw_name}')
        for kind, query in [('database', "SELECT datname FROM pg_database WHERE datname LIKE 'lab\\_%' ESCAPE '\\';"), ('role', "SELECT rolname FROM pg_roles WHERE rolname LIKE 'lab\\_%' ESCAPE '\\';")]:
            expected = {'lab_'+app.replace('-', '_') for app, rec in records.items() if rec['db'] == 'postgres'}
            try:
                actual = set(self.sql(query).stdout.splitlines())
                problems += [f'orphan {kind}: {item}' for item in sorted(actual - expected)]
                problems += [f'missing {kind}: {item}' for item in sorted(expected - actual)]
            except LabError:
                problems.append(f'cannot enumerate Postgres {kind}s')
        try:
            expected_sites = ''.join(caddy_site(rec, self.config()['domain'], self.root, self.public, self.config().get('tls_mode', 'production')) for rec in self.published())
            if (self.caddy/'lab-sites.caddy').read_text() != expected_sites:
                problems.append('Caddy file differs from published records; use labctl reconcile-caddy')
        except (LabError, OSError, ValueError):
            problems.append('cannot reconcile Caddy because metadata/config is invalid')
        for item in problems:
            print(item)
        print(f'{len(problems)} problem(s); read-only inspection, not a readiness certification')
        return bool(problems)


def parser():
    p = argparse.ArgumentParser(description='Trusted lab platform operations (v3)')
    sub = p.add_subparsers(dest='op', required=True)
    create = sub.add_parser('create')
    create.add_argument('name', type=name)
    kinds = create.add_mutually_exclusive_group()
    kinds.add_argument('--app', dest='kind', action='store_const', const='app')
    kinds.add_argument('--static', dest='kind', action='store_const', const='static')
    create.set_defaults(kind='static')
    create.add_argument('--db', choices=['none', 'sqlite', 'postgres'], default='none')
    create.add_argument('--private', action='store_true')
    create.add_argument('--prepare-only', action='store_true', help='provision stopped resources for restore')
    create.add_argument('--title')
    create.add_argument('--secrets', default='')
    for op in ('remove', 'verify', 'logs', 'publish'):
        sub.add_parser(op).add_argument('name', type=name)
    service = sub.add_parser('service')
    service.add_argument('action', choices=['start', 'stop', 'restart', 'enable', 'disable', 'status', 'is-active'])
    service.add_argument('name', type=name)
    grant = sub.add_parser('secrets-grant')
    grant.add_argument('keys')
    grant.add_argument('name', type=name)
    for op in ('list', 'doctor', 'secrets-list', 'reconcile-caddy'):
        sub.add_parser(op)
    return p


def main(argv=None):
    os.umask(0o077)
    try:
        args = parser().parse_args(argv)
        if os.geteuid() != 0:
            raise LabError('run through sudo /usr/local/sbin/labctl')
        ctl = Controller()
        for directory in (ctl.root, ctl.public, ctl.state, ctl.state/'records', ctl.state/'credentials', ctl.etc, ctl.etc/'apps', ctl.caddy, ctl.units):
            protected_dir(directory)
        ctl.config()
        with locked(ctl.state/'lock'):
            if args.op == 'create': ctl.create(args)
            elif args.op == 'remove': ctl.remove(args.name)
            elif args.op == 'publish': ctl.publish(args.name)
            elif args.op == 'service': return ctl.service(args.action, args.name)
            elif args.op == 'verify': return 0 if ctl.verify(args.name) else 1
            elif args.op == 'secrets-grant': ctl.grant(args.name, args.keys)
            elif args.op == 'secrets-list': print('\n'.join(sorted(read_env(ctl.etc/'secrets.env'))))
            elif args.op == 'doctor': return int(ctl.doctor())
            elif args.op == 'reconcile-caddy': ctl.caddy_publish(ctl.published())
            elif args.op == 'list':
                for path in sorted((ctl.state/'records').glob('*.json')):
                    try:
                        rec = ctl.record(path.stem)
                        print(rec['name'], rec['kind'], rec['status'], rec['port'] or '-', sep='\t')
                    except LabError:
                        print(path.stem, 'INVALID RECORD', sep='\t')
            elif args.op == 'logs':
                ctl.record(args.name)
                print(ctl.run(['journalctl', '--no-pager', '-u', ctl.unit(args.name), '-n', '60']).stdout, end='')
        return 0
    except (LabError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        # Never print arbitrary subprocess output or JSON/env values.
        print(f'labctl: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
