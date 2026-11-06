#!/usr/bin/python3 -I
"""Private onboarding: unprivileged loopback UI, separate root-only apply command."""
import argparse
import fcntl
import hmac
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import socket
import stat
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bin/lib'))
from labcore import LabError, atomic_write, domain, install_domain, read_env, protected_dir, locked

PROVIDERS = {
    'replicate': 'REPLICATE_API_TOKEN', 'openai': 'OPENAI_API_KEY',
    'gemini': 'GEMINI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY',
    'openrouter': 'OPENROUTER_API_KEY',
}
SECRET_NAMES = set(PROVIDERS.values()) | {
    'RESEND_API_KEY', 'STRIPE_SECRET_KEY', 'B2_KEY_ID', 'B2_APP_KEY',
    'RESTIC_PASSWORD', 'HEALTHCHECKS_PING_URL',
}
CHOICES = {
    'PROJECT_NAME': 'My Lab', 'DOMAIN': '', 'SERVER_IPV4': '', 'SSH_PORT': '22',
    'BACKUP_TIMEZONE': 'UTC', 'DEPLOYMENT_AGENT': 'claude-desktop',
    'NOTIFICATIONS': '', 'BACKUPS': '', 'B2_BUCKET': '', 'B2_ENDPOINT': '',
    'BACKUP_SERVER_NAME': '', 'EMAIL_PROVIDER': '', 'EMAIL_SENDING_DOMAIN': '',
    'EMAIL_DEFAULT_FROM': '', 'GITHUB_LOGIN': '', 'PAYMENTS_PROVIDER': '',
    'BACKUP_MONITORING': '', 'AI_TEST_BUDGET_USD': '', 'RECOVERY_DETAILS_SAVED': '',
}
LIMIT = 65536


def clean_text(value, limit=4096):
    if not isinstance(value, str) or len(value.encode('utf-8')) > limit or any(ord(c) < 32 or c in '\x7f\x85\u2028\u2029' for c in value):
        raise LabError('Use a single line of text within the field limit.')
    return value.strip()


def validate_choices(value):
    if not isinstance(value, dict) or set(value) - set(CHOICES):
        raise LabError('Unknown setup field.')
    result = {k: clean_text(v, 253) for k, v in value.items()}
    enums = {
        'NOTIFICATIONS': {'', 'ntfy', 'skip'}, 'BACKUPS': {'', 'b2', 'skip'},
        'DEPLOYMENT_AGENT': {'claude-desktop', 'codex-desktop'},
        'EMAIL_PROVIDER': {'', 'resend'}, 'PAYMENTS_PROVIDER': {'', 'stripe'},
        'BACKUP_MONITORING': {'', 'healthchecks', 'skip'},
        'RECOVERY_DETAILS_SAVED': {'', 'yes'},
    }
    for key, allowed in enums.items():
        if key in result and result[key] not in allowed:
            raise LabError('Invalid service selection.')
    for key in ('DOMAIN', 'EMAIL_SENDING_DOMAIN'):
        if result.get(key):
            domain(result[key])
    if result.get('SERVER_IPV4'):
        resolved = install_domain(result['SERVER_IPV4'])
        if not resolved.endswith('.sslip.io') or result['SERVER_IPV4'].count('.') != 3 or not all(p.isdigit() for p in result['SERVER_IPV4'].split('.')):
            raise LabError('Enter a public IPv4 address for automatic hosting.')
    if result.get('SSH_PORT') and (not result['SSH_PORT'].isdigit() or not 1 <= int(result['SSH_PORT']) <= 65535):
        raise LabError('SSH port must be between 1 and 65535.')
    if result.get('AI_TEST_BUDGET_USD') and not re.fullmatch(r'\d{1,6}(?:\.\d{1,2})?', result['AI_TEST_BUDGET_USD']):
        raise LabError('Test budget must be a nonnegative amount in USD.')
    return result


def validate_secrets(value):
    if not isinstance(value, dict) or set(value) - SECRET_NAMES:
        raise LabError('Unknown credential field.')
    result = {k: clean_text(v) for k, v in value.items()}
    if 'RESTIC_PASSWORD' in value:
        result['RESTIC_PASSWORD'] = value['RESTIC_PASSWORD']  # Preserve exact recovery password.
    if any(not v for v in result.values()):
        raise LabError('Enter a key or leave the field unchanged.')
    stripe = result.get('STRIPE_SECRET_KEY', '')
    if stripe and not stripe.startswith(('sk_test_', 'rk_test_')):
        raise LabError('Use a Stripe test key here. Live payments are a separate setup.')
    return result


def validate_bundle(data):
    if not isinstance(data, dict) or set(data) != {'version', 'choices', 'secrets', 'topic', 'notification', 'finished'} or data['version'] != 1:
        raise LabError('Invalid setup bundle.')
    choices = validate_choices(data['choices'])
    choices.setdefault('SERVER_IPV4', '')  # Older saved forms had no IP-only option.
    if set(choices) != set(CHOICES):
        raise LabError('Incomplete setup bundle.')
    data['choices'] = choices
    data['secrets'] = validate_secrets(data['secrets'])
    if not isinstance(data['topic'], str) or (data['topic'] and not re.fullmatch(r'lab-[a-f0-9]{32}', data['topic'])):
        raise LabError('Invalid notification topic.')
    if data['notification'] not in {'untested', 'sent', 'confirmed', 'failed'} or type(data['finished']) is not bool:
        raise LabError('Invalid setup status.')
    return data


def read_bundle(directory):
    """No symlink traversal; bounded, regular private file under a private directory."""
    directory = Path(directory)
    if directory.resolve() != directory.absolute():
        raise LabError('Use a real setup directory, not a symlink.')
    dst = directory.lstat()
    if not stat.S_ISDIR(dst.st_mode) or dst.st_mode & 0o077:
        raise LabError('Setup directory must have mode 0700.')
    fd = os.open(directory / 'setup.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != dst.st_uid or stat.S_IMODE(st.st_mode) != 0o600 or st.st_size > LIMIT:
            raise LabError('Setup bundle must be a private regular file owned by its directory owner.')
        try:
            return validate_bundle(json.loads(stream.read(LIMIT + 1)))
        except (ValueError, TypeError, KeyError) as exc:
            raise LabError('Invalid setup bundle.') from exc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send_notification(topic):
    # Only this fixed service and a generated path; never a user-supplied URL.
    request = urllib.request.Request(
        'https://ntfy.sh/' + topic,
        data=b'Your lab setup can reach this phone. Confirm receipt in the setup page.',
        headers={'Title': 'Lab setup test', 'Content-Type': 'text/plain'}, method='POST')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=10) as response:
        if response.status != 200:
            raise LabError('Notification delivery failed. Try again later.')


class Wizard:
    def __init__(self, directory, sender=send_notification):
        self.directory = Path(directory)
        self.sender = sender
        self.token = secrets.token_urlsafe(32)
        self.expires = time.monotonic() + 3600
        self.last_send = 0
        path = self.directory / 'setup.json'
        if path.exists() or path.is_symlink():
            self.data = read_bundle(self.directory)
            # Opening a new local process is the explicit way to reopen setup.
            self.data['finished'] = False
        else:
            self.data = {'version': 1, 'choices': dict(CHOICES), 'secrets': {},
                         'topic': '', 'notification': 'untested', 'finished': False}
        self.save()

    def save(self):
        atomic_write(self.directory / 'setup.json', json.dumps(self.data, ensure_ascii=False))

    def status(self):
        return {'choices': self.data['choices'], 'saved_keys': sorted(self.data['secrets']),
                'has_topic': bool(self.data['topic']), 'notification': self.data['notification'],
                'finished': self.data['finished']}

    def action(self, action, body):
        if self.data['finished']:
            raise LabError('Setup is closed. Restart the setup command to edit again.')
        if action == 'save':
            if set(body) != {'choices', 'secrets', 'remove'}:
                raise LabError('Invalid save request.')
            choices = validate_choices(body['choices'])
            updates = validate_secrets(body['secrets'])
            remove = body['remove']
            if not isinstance(remove, list) or any(not isinstance(k, str) or k not in SECRET_NAMES for k in remove):
                raise LabError('Unknown credential to remove.')
            # All validation precedes changes. Empty password fields never erase keys.
            self.data['choices'].update(choices)
            for key in remove:
                self.data['secrets'].pop(key, None)
            self.data['secrets'].update(updates)
        elif action == 'topic':
            if self.data['topic']:
                raise LabError('A topic already exists. Use subscription details to subscribe.')
            self.data['topic'] = 'lab-' + secrets.token_hex(16)
            self.data['choices']['NOTIFICATIONS'] = 'ntfy'
            self.save()
            return {'topic': self.data['topic']}
        elif action == 'subscription':
            # Intentional disclosure of subscription destination to authenticated owner.
            if not self.data['topic']:
                raise LabError('Create a topic first.')
            return {'topic': self.data['topic']}
        elif action == 'test-ntfy':
            if self.data['choices']['NOTIFICATIONS'] != 'ntfy' or not self.data['topic']:
                raise LabError('Choose ntfy and create your subscription first.')
            if time.monotonic() - self.last_send < 30:
                raise LabError('Wait 30 seconds before sending another test.')
            self.last_send = time.monotonic()
            try:
                self.sender(self.data['topic'])
                self.data['notification'] = 'sent'
            except Exception:
                self.data['notification'] = 'failed'
                self.save()
                raise LabError('Could not send the notification. Check connectivity and try again.') from None
        elif action == 'confirm-ntfy':
            if self.data['notification'] not in {'sent', 'confirmed'}:
                raise LabError('Send a test before confirming phone receipt.')
            self.data['notification'] = 'confirmed'
        elif action == 'finish':
            finish_checks(self.data)
            self.data['finished'] = True
        else:
            raise LabError('Unknown setup action.')
        self.save()
        return self.status()


def finish_checks(data):
    c = data['choices']
    if not (c['DOMAIN'] or c['SERVER_IPV4']) or not c['SSH_PORT']:
        raise LabError('Enter a public server IP or your own domain, and the SSH port.')
    install_domain(c['DOMAIN'] or c['SERVER_IPV4'])
    if not c['NOTIFICATIONS'] or not c['BACKUPS']:
        raise LabError('Choose notifications and backups, or explicitly defer them.')
    if c['NOTIFICATIONS'] == 'ntfy' and data['notification'] != 'confirmed':
        raise LabError('Confirm the test arrived on your phone, or defer notifications.')
    required = []
    if c['EMAIL_PROVIDER']:
        required += ['RESEND_API_KEY']
        if not c['EMAIL_SENDING_DOMAIN']:
            raise LabError('Enter your email sending domain.')
    if c['PAYMENTS_PROVIDER']:
        required += ['STRIPE_SECRET_KEY']
    if c['BACKUP_MONITORING'] == 'healthchecks':
        required += ['HEALTHCHECKS_PING_URL']
    if c['BACKUPS'] == 'b2':
        required += ['B2_KEY_ID', 'B2_APP_KEY', 'RESTIC_PASSWORD']
        if not all(c[k] for k in ('B2_BUCKET', 'B2_ENDPOINT', 'BACKUP_SERVER_NAME')):
            raise LabError('Complete the backup bucket, endpoint and unique server name.')
        if c['RECOVERY_DETAILS_SAVED'] != 'yes':
            raise LabError('Save your backup recovery details outside this VPS first.')
    if any(k not in data['secrets'] for k in required):
        raise LabError('A selected service still needs credentials. Complete it or deselect it.')


def make_server(wizard, assets, port):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'LabSetup'
        sys_version = ''

        def log_message(self, *args):
            pass  # Never log request paths, bodies, headers or credentials.

        def setup(self):
            super().setup()
            self.connection.settimeout(8)

        def respond(self, status, value, mime='application/json'):
            body = json.dumps(value).encode() if mime == 'application/json' else value
            self.send_response(status)
            for key, val in {
                'Content-Type': mime, 'Content-Length': str(len(body)),
                'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
                'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
                'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
            }.items():
                self.send_header(key, val)
            self.end_headers()
            self.wfile.write(body)

        def allowed(self, api=False):
            origins = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
            if 'http://' + self.headers.get('Host', '') not in origins:
                self.respond(403, {'error': 'Use the local SSH tunnel address.'})
                return False
            origin = self.headers.get('Origin')
            if origin is not None and origin not in origins:
                self.respond(403, {'error': 'Cross-origin requests are blocked.'})
                return False
            if api and (time.monotonic() > wizard.expires or wizard.data['finished'] or
                        not hmac.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + wizard.token).encode())):
                self.respond(401, {'error': 'Setup code is missing, expired or closed. Restart setup if needed.'})
                return False
            return True

        def do_GET(self):
            if not self.allowed(self.path.startswith('/api/')):
                return
            if self.path == '/api/status':
                self.respond(200, wizard.status())
            elif self.path in assets:
                mime, data = assets[self.path]
                self.respond(200, data, mime)
            else:
                self.respond(404, {'error': 'Not found.'})

        def do_POST(self):
            if not self.allowed(True):
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= LIMIT or self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != 'application/json':
                    raise LabError('Send a JSON request under 64 KiB.')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict) or not self.path.startswith('/api/'):
                    raise LabError('Invalid request.')
                result = wizard.action(self.path.removeprefix('/api/'), body)
                self.respond(200, result)
            except (LabError, ValueError, TypeError) as exc:
                message = str(exc) if isinstance(exc, LabError) else 'Invalid request.'
                self.respond(400, {'error': message})
            except (OSError, socket.timeout):
                self.respond(500, {'error': 'Could not save setup. Check disk space and private directory permissions.'})
    return HTTPServer(('127.0.0.1', port), Handler)


def settings_text(data):
    c = dict(data['choices'])
    c['DOMAIN'] = install_domain(c['DOMAIN'] or c['SERVER_IPV4'])
    c['AI_PROVIDERS'] = ','.join(k for k, v in PROVIDERS.items() if v in data['secrets']) or 'skip'
    c.update(NTFY_URL='https://ntfy.sh', BACKUP_METHOD='whole-server', PAYMENTS_MODE='test' if c['PAYMENTS_PROVIDER'] else '')
    return '# Non-secret owner choices. Never source this file.\n' + ''.join(k + '=' + v + '\n' for k, v in c.items())


def stage_bundle(data, destination):
    """Root-owned staging for the administrator; never execute input as commands."""
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    protected_dir(destination)
    if destination.stat().st_mode & 0o077:
        raise LabError('Credential staging directory must be private (0700).')
    atomic_write(destination / 'owner-settings.txt', settings_text(data))
    atomic_write(destination / 'setup-bundle.json', json.dumps(data))
    atomic_write(destination / 'capabilities.json', json.dumps({
        'scope': 'selected in this setup; existing services may also be configured',
        'providers': [k for k, v in PROVIDERS.items() if v in data['secrets']],
        'provider_verification': 'untested', 'notifications': data['notification'] if data['choices']['NOTIFICATIONS'] == 'ntfy' else 'deferred',
        'backups': 'pending' if data['choices']['BACKUPS'] == 'b2' else 'deferred',
        'email': 'pending' if data['choices']['EMAIL_PROVIDER'] else 'not selected',
        'payments': 'test key only' if data['choices']['PAYMENTS_PROVIDER'] else 'not selected',
    }, indent=2))


def apply_integrations(data, target, stage, lab_gid):
    """Apply only bounded configuration; no apt, shell, schedules or paid calls."""
    protected_dir(target)
    # Preflight every affected destination before any write.
    current = read_env(target / 'secrets.env')
    backup = read_env(target / 'backup.env')
    selected = {k: v for k, v in data['secrets'].items() if k in PROVIDERS.values()}
    current.update(selected)
    c = data['choices']
    if c['EMAIL_PROVIDER'] == 'resend':
        current['RESEND_API_KEY'] = data['secrets']['RESEND_API_KEY']
    atomic_write(target / 'secrets.env', ''.join(k + '=' + v + '\n' for k, v in sorted(current.items())))
    if c['NOTIFICATIONS'] == 'ntfy':
        notify = {'NTFY_URL': 'https://ntfy.sh', 'NTFY_TOPIC': data['topic']}
        atomic_write(target / 'notify.env', ''.join(k + '=' + v + '\n' for k, v in notify.items()))
        os.chown(target / 'notify.env', 0, lab_gid)
        (target / 'notify.env').chmod(0o640)
        backup.update(notify)
        atomic_write(target / 'backup.env', ''.join(k + '=' + v + '\n' for k, v in sorted(backup.items())))
    if c['EMAIL_PROVIDER'] == 'resend':
        atomic_write(target / 'email.json', json.dumps({'provider': 'resend', 'sending_domain': c['EMAIL_SENDING_DOMAIN'], 'default_from': c['EMAIL_DEFAULT_FROM'] or None}))
        os.chown(target / 'email.json', 0, lab_gid)
        (target / 'email.json').chmod(0o640)
    if c['PAYMENTS_PROVIDER'] == 'stripe':
        atomic_write(target / 'stripe.env', 'STRIPE_SECRET_KEY=' + data['secrets']['STRIPE_SECRET_KEY'] + '\n')
    # This inventory is a safe discovery hint, not a grant or a claim of verification.
    atomic_write(target / 'setup-capabilities.json', (stage / 'capabilities.json').read_bytes(), 0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['serve', 'stage', 'apply'])
    parser.add_argument('--state-dir', type=Path, default=Path('/var/lib/lab-onboarding'))
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.command != 'serve':
        if os.geteuid() != 0:
            raise LabError('Staging and activation require an administrator.')
        data = read_bundle(args.state_dir)
        if not data['finished']:
            raise LabError('Finish and close the form before staging or applying.')
        finish_checks(data)
        destination = Path('/root/lab-credentials')
        stage_bundle(data, destination)
        if args.command == 'apply':
            with locked(Path('/var/lib/lab/lock')):
                apply_integrations(data, Path('/etc/lab'), destination, pwd.getpwnam('lab').pw_gid)
            print('Selected AI/notification/email/test-payment credentials applied; provider access remains untested.')
        else:
            print('Choices and secrets staged. Continue SETUP.md; core installation is still required.')
        print('Non-secret choices: /root/lab-credentials/owner-settings.txt')
        print('Backup and monitoring secrets: protected setup-bundle.json. Configure and verify those separately.')
        print('Existing app grants were not changed. Stop the wizard and remove its private staging directory after handoff.')
        return
    assets = {'/': ('text/html; charset=utf-8', (ROOT / 'tools/setup-ui/index.html').read_bytes()),
              '/app.js': ('text/javascript; charset=utf-8', (ROOT / 'tools/setup-ui/app.js').read_bytes()),
              '/style.css': ('text/css; charset=utf-8', (ROOT / 'tools/setup-ui/style.css').read_bytes())}
    args.state_dir = args.state_dir.absolute()
    if args.state_dir.resolve() != args.state_dir:
        raise LabError('Use a real private directory outside the repository.')
    if args.state_dir == ROOT or ROOT in args.state_dir.parents:
        raise LabError('Secret staging must be outside the repository.')
    setup_user = None
    if os.geteuid() == 0:
        try:
            setup_user = pwd.getpwnam('labsetup')
        except KeyError as exc:
            raise LabError('Create the dedicated labsetup system user first; see docs/setup-wizard.md.') from exc
        if setup_user.pw_uid == 0:
            raise LabError('The setup account must not be root.')
    args.state_dir.mkdir(mode=0o700, parents=False, exist_ok=True)
    uid = setup_user.pw_uid if setup_user else os.geteuid()
    st = args.state_dir.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_mode & 0o077 or st.st_uid not in {os.geteuid(), uid}:
        raise LabError('Use a private directory owned by the setup process.')
    if os.geteuid() == 0:
        setup_user = pwd.getpwnam('labsetup')
        os.chown(args.state_dir, setup_user.pw_uid, setup_user.pw_gid)
        os.chdir('/')
        os.setgroups([])
        os.setgid(setup_user.pw_gid)
        os.setuid(setup_user.pw_uid)
    session_fd = os.open(args.state_dir / 'session.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    session_stat = os.fstat(session_fd)
    if not stat.S_ISREG(session_stat.st_mode) or session_stat.st_uid != os.geteuid() or stat.S_IMODE(session_stat.st_mode) != 0o600:
        raise LabError('Invalid setup session lock.')
    try:
        fcntl.flock(session_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise LabError('Another setup process already owns this directory. Stop it before restarting.') from exc
    wizard = Wizard(args.state_dir)
    server = make_server(wizard, assets, args.port)
    print(f'Open http://127.0.0.1:{server.server_port} through an SSH tunnel using the same local port.', flush=True)
    print('One-hour setup code (do not paste into agent chat): ' + wizard.token, flush=True)
    print('No root privileges in the web process. Ctrl+C stops the form; saved choices can be resumed.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        os.close(session_fd)


if __name__ == '__main__':
    try:
        main()
    except LabError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except (OSError, KeyError):
        print('Setup could not continue. Check private directory ownership, selected inputs and core installation.', file=sys.stderr)
        sys.exit(1)
