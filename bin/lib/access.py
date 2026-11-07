"""Invitation-scoped SSH enrollment. Runs as lab, with no root HTTP process."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlsplit
import urllib.request
import urllib.error
from labcore import LabError
from sshkeys import public_key, WRITER

STATE = Path('/var/lib/lab-access')
CONFIG = Path('/etc/lab/access.json')


class Invitations:
    def __init__(self, path, writer, sender=None):
        self.path = path
        self.writer = writer
        self.sender = sender or send_notification
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS invitations (digest TEXT PRIMARY KEY, expires REAL NOT NULL, binding TEXT, used INTEGER NOT NULL DEFAULT 0, revoked INTEGER NOT NULL DEFAULT 0)')

            db.execute('CREATE TABLE IF NOT EXISTS notifications (recipient TEXT PRIMARY KEY, topic TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0, tested INTEGER NOT NULL DEFAULT 0, last_test REAL NOT NULL DEFAULT 0, skipped INTEGER NOT NULL DEFAULT 0)')

    def notification(self, token, action):
        if action not in ('status', 'start', 'test', 'confirm', 'skip'):
            raise LabError('Unknown notification action.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            _, invite = self.check(db, token)
            if not invite[2]:
                raise LabError('Enable SSH access first. Notifications are optional.')
            recipient = invite[1]
            if action == 'start':
                db.execute('INSERT OR IGNORE INTO notifications(recipient,topic) VALUES (?,?)',
                           (recipient, 'infinity-' + secrets.token_hex(20)))
                db.execute('UPDATE notifications SET skipped=0 WHERE recipient=?', (recipient,))
            row = db.execute('SELECT topic,confirmed,tested,last_test,skipped FROM notifications WHERE recipient=?', (recipient,)).fetchone()
            if action == 'skip':
                db.execute('INSERT OR IGNORE INTO notifications(recipient,topic) VALUES (?,?)',
                           (recipient, 'infinity-' + secrets.token_hex(20)))
                db.execute('UPDATE notifications SET skipped=1,confirmed=0 WHERE recipient=?', (recipient,))
                return {'state': 'skipped', 'recipient': recipient}
            if not row:
                if action != 'status':
                    raise LabError('Choose Set up notifications first.')
                return {'state': 'unconfigured', 'recipient': recipient}
            if action == 'test':
                if row[4]:
                    raise LabError('Choose Set up notifications first.')
                if time.time() - row[3] < 30:
                    raise LabError('Wait 30 seconds before sending another test.')
                db.execute('UPDATE notifications SET last_test=?,tested=0 WHERE recipient=?', (time.time(), recipient))
            if action == 'confirm':
                if not row[2] or row[4]:
                    raise LabError('Send a test and confirm it arrived on your phone first.')
                db.execute('UPDATE notifications SET confirmed=1 WHERE recipient=?', (recipient,))
        if action == 'test':
            self.sender(row[0], 'The Infinity Machine', 'Your test notification arrived. Confirm receipt on the setup page.')
            with self.connect() as db:
                db.execute('UPDATE notifications SET tested=1 WHERE recipient=?', (recipient,))
        with self.connect() as db:
            row = db.execute('SELECT topic,confirmed,tested,last_test,skipped FROM notifications WHERE recipient=?', (recipient,)).fetchone()
        return {'state': 'skipped' if row[4] else ('ready' if row[1] else 'pending'),
                'recipient': recipient, 'topic': row[0] if not row[4] else '', 'tested': bool(row[2])}

    def notify(self, recipient, title, url):
        if not recipient or not re.fullmatch(r'[a-f0-9]{64}', recipient):
            raise LabError('Supply the recipient ID from the invitation page; never guess a destination.')
        parsed = urlsplit(url or '')
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or any(c.isspace() for c in url):
            raise LabError('Supply an HTTPS app URL without credentials.')
        if not title or len(title) > 180 or len(url) > 2048:
            raise LabError('Supply a short title and app URL.')
        with self.connect() as db:
            row = db.execute('SELECT topic,confirmed,skipped FROM notifications WHERE recipient=?', (recipient,)).fetchone()
        if not row or not row[1] or row[2]:
            raise LabError('Notifications are not confirmed for this recipient. Share the link in chat.')
        self.sender(row[0], title, url)

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def create(self, hours=24):
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as db:
            db.execute('DELETE FROM invitations WHERE expires < ?', (time.time() - 7 * 86400,))
            db.execute('INSERT INTO invitations(digest,expires) VALUES (?,?)', (digest, time.time() + hours * 3600))
        return token, digest

    def check(self, db, token):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            raise LabError('This invitation is invalid, expired or revoked. Ask the server owner for a new link.')
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = db.execute('SELECT expires,binding,used,revoked FROM invitations WHERE digest=?', (digest,)).fetchone()
        if row is None or row[0] < time.time() or row[3]:
            raise LabError('This invitation is invalid, expired or revoked. Ask the server owner for a new link.')
        return digest, row

    def status(self, token):
        with self.connect() as db:
            _, row = self.check(db, token)
            return {'used': bool(row[2]), 'expires': row[0]}

    def enroll(self, token, value):
        with self.connect() as db:
            self.check(db, token)
        key = public_key(value)
        binding = hashlib.sha256(key.encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            digest, row = self.check(db, token)
            if row[1] and row[1] != binding:
                raise LabError('This invitation is already assigned to another key. Ask for a new invitation.')
            # Commit key binding BEFORE writing SSH access. A crash/retry cannot
            # redeem one invitation for a different key after a partial success.
            db.execute('UPDATE invitations SET binding=? WHERE digest=?', (binding, digest))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.check(db, token)
            self.writer(key)
            db.execute('UPDATE invitations SET used=1 WHERE digest=?', (digest,))
        return {'enabled': True, 'user': 'lab'}

    def revoke(self, digest):
        with self.connect() as db:
            changed = db.execute('UPDATE invitations SET revoked=1 WHERE digest=?', (digest,)).rowcount
        if not changed:
            raise LabError('Invitation ID not found.')


def send_notification(topic, title, message):
    # Fixed destination; never accept a user-supplied endpoint or follow redirects.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    payload = {'topic': topic, 'title': title, 'message': message}
    if message.startswith('https://'):
        payload['actions'] = [
            {'action': 'copy', 'label': 'Copy link', 'value': message},
            {'action': 'view', 'label': 'Open in browser', 'url': message},
        ]
    body = json.dumps(payload).encode()
    request = urllib.request.Request('https://ntfy.sh', data=body,
                                     headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=8) as response:
            if response.status != 200:
                raise LabError('ntfy could not accept the message. Retry later or skip for now.')
    except (OSError, urllib.error.URLError):
        raise LabError('ntfy could not accept the message. Retry later or skip for now.') from None


def write_key(key):
    if os.geteuid() != pwd.getpwnam('lab').pw_uid:
        raise LabError('Access service must run as lab.')
    result = subprocess.run(['/usr/bin/python3', '-I', '-c', WRITER], input=key,
                            text=True, capture_output=True, timeout=10)
    if result.returncode:
        raise LabError('Could not save access. Ask the server owner to check SSH directory permissions, then retry the same key.')


def server(store, origin, port=9876):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *args):
            pass  # Never log credentials, keys, headers or request bodies.

        def reply(self, code, data):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def do_POST(self):
            try:
                if self.path not in ('/_lab/access/status', '/_lab/access/enroll', '/_lab/access/notifications'):
                    self.reply(404, {'error': 'Not found.'}); return
                if self.headers.get('Origin') != origin or self.headers.get('Transfer-Encoding'):
                    self.reply(403, {'error': 'Open the original invitation page.'}); return
                now = time.monotonic()
                if now - self.server.window > 60:
                    self.server.window, self.server.count = now, 0
                self.server.count += 1
                if self.server.count > 60:
                    self.reply(429, {'error': 'Too many requests. Wait a minute and retry.'}); return
                if self.headers.get_content_type() != 'application/json':
                    self.reply(415, {'error': 'JSON required.'}); return
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 18000:
                    self.reply(413, {'error': 'Paste one public key only.'}); return
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError()
                token = self.headers.get('Authorization', '').removeprefix('Bearer ')
                if self.path.endswith('/status'):
                    result = store.status(token)
                elif self.path.endswith('/notifications'):
                    if set(data) != {'action'}:
                        raise ValueError()
                    result = store.notification(token, data['action'])
                else:
                    if set(data) != {'public_key'}:
                        raise ValueError()
                    result = store.enroll(token, data['public_key'])
                self.reply(200, result)
            except LabError as exc:
                self.reply(400, {'error': str(exc)})
            except (ValueError, UnicodeError):
                self.reply(400, {'error': 'Invalid request.'})
            except (OSError, sqlite3.Error, subprocess.SubprocessError):
                self.reply(503, {'error': 'Access setup is unavailable. Retry the same key or contact the server owner.'})

        def do_GET(self):
            self.reply(405, {'error': 'Use the invitation form.'})

    http = HTTPServer(('127.0.0.1', port), Handler)
    http.window, http.count = time.monotonic(), 0
    return http


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['invite', 'serve', 'revoke', 'notify'])
    parser.add_argument('--hours', type=int, default=24)
    parser.add_argument('--id')
    parser.add_argument('--recipient')
    parser.add_argument('--title')
    parser.add_argument('--url')
    args = parser.parse_args()
    if not 1 <= args.hours <= 168:
        parser.error('Invitation lifetime must be 1–168 hours.')
    account = pwd.getpwnam('lab')
    if os.geteuid() == 0:
        os.setgroups([]); os.setgid(account.pw_gid); os.setuid(account.pw_uid)
    if os.geteuid() != account.pw_uid:
        raise LabError('Run this command as lab or the server administrator.')
    os.environ['HOME'] = account.pw_dir
    os.umask(0o077)
    config = json.loads(CONFIG.read_text())
    url = config['welcome_url']
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username:
        raise LabError('Configure an HTTPS welcome origin first.')
    origin = url.rstrip('/')
    store = Invitations(STATE / 'invitations.sqlite', write_key)
    if args.command == 'invite':
        token, digest = store.create(args.hours)
        print(f'Private invitation (expires in {args.hours} hours; one public key):')
        print(origin + '/#invite=' + token)
        print('Invitation ID: ' + digest)
    elif args.command == 'notify':
        store.notify(args.recipient, args.title, args.url)
        print('Notification sent.')
    elif args.command == 'revoke':
        if not args.id:
            parser.error('--id is required for revoke')
        store.revoke(args.id)
        print('Invitation revoked. Already authorized SSH keys are not removed.')
    else:
        server(store, origin).serve_forever()


if __name__ == '__main__':
    try:
        main()
    except (LabError, OSError, KeyError, ValueError) as exc:
        print(str(exc) if isinstance(exc, LabError) else 'Check access-service installation and configuration.', file=sys.stderr)
        sys.exit(1)
