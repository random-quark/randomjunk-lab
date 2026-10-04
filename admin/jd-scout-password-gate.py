#!/usr/bin/python3 -I
"""Owner-requested, scoped migration from Caddy Basic auth to app password gate.

Deploy and test the app password/session gate first. This changes no other lab.
No password or credential is read, copied, or printed by this migration.
"""
import sys
import urllib.error
import urllib.request
sys.path.insert(0, '/usr/local/lib/lab')
from controller import Controller
from labcore import locked


def main():
    ctl = Controller()
    with locked(ctl.state / 'lock'):
        rec = ctl.record('jd-scout')
        base = f'http://127.0.0.1:{rec["port"]}'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(base + '/', timeout=10) as response:
            assert response.status == 200 and b'No username needed.' in response.read()
        for path in ('/api/access', '/novnc/vnc.html'):
            try:
                opener.open(base + path, timeout=10)
            except urllib.error.HTTPError as exc:
                assert exc.code == 401 and 'WWW-Authenticate' not in exc.headers
            else:
                raise RuntimeError('Refusing migration: app route is not protected')
        previous = dict(rec)
        rec['private'] = False  # Caddy gate only; the application remains private.
        rec.pop('auth_hash', None)
        ctl.save(rec)
        try:
            ctl.caddy_publish(ctl.published())
        except Exception:
            ctl.save(previous)
            raise
    print('JD Scout now uses its app password screen. Other records unchanged.')

if __name__ == '__main__':
    main()
