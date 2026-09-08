"""Isolated local development server; no production environment or database."""
import argparse
from contextlib import contextmanager
import functools
import http.server
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

class PublicHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        target = Path(self.translate_path(self.path))
        root = Path(self.directory).resolve()
        try:
            target.resolve().relative_to(root)
            if any(p.is_symlink() for p in [target, *target.parents] if p != root):
                raise ValueError()
        except ValueError:
            self.send_error(404)
            return None
        return super().send_head()
    def list_directory(self, path):
        self.send_error(404)
        return None
    def log_message(self, *args):
        pass

@contextmanager
def server(app_dir, *, kind=None, db=None):
    if os.geteuid() == 0:
        raise RuntimeError('run development servers as lab, never root')
    root = Path(app_dir).resolve()
    metadata = json.loads((root / 'lab.json').read_text()) if (root / 'lab.json').exists() else {}
    kind = kind or metadata.get('kind') or ('app' if (root / 'main.py').exists() else 'static')
    db = db or metadata.get('db', 'sqlite')
    if db == 'postgres':
        raise RuntimeError('labdev requires a separate test Postgres database; automatic Postgres provisioning is not supported')
    with tempfile.TemporaryDirectory(prefix='labdev-') as directory:
        temp = Path(directory)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); sock.listen(128)
            port = sock.getsockname()[1]
            env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(Path.home()),
                   'LANG': 'C.UTF-8', 'APP_NAME': metadata.get('name', root.parent.name),
                   'PORT': str(port), 'DATABASE_URL': 'sqlite:///' + str(temp / 'test.db'),
                   'LAB_DEV': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
            python = root / '.venv/bin/python'
            if kind == 'app':
                if not python.exists():
                    raise RuntimeError('run uv sync --locked --python /usr/bin/python3 as lab first')
                command = [str(python), '-m', 'uvicorn', 'main:app', '--fd', str(sock.fileno())]
                health = '/api/health'
            else:
                command = [sys.executable, str(Path(__file__).resolve()), '--static-child',
                           str(sock.fileno()), '--app-dir', str(root)]
                health = '/'
            with (temp / 'server.log').open('w+') as log:
                process = subprocess.Popen(command, cwd=root, env=env, pass_fds=(sock.fileno(),),
                                           start_new_session=True, stdout=log, stderr=log)
                url = f'http://127.0.0.1:{port}'
                try:
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    deadline = time.monotonic() + 20
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError('development server exited before readiness; inspect the app startup locally')
                        try:
                            with opener.open(url + health, timeout=.5) as response:
                                if response.status == 200:
                                    break
                        except OSError:
                            pass
                        if time.monotonic() >= deadline:
                            raise RuntimeError('development server readiness timed out')
                        time.sleep(.05)
                    yield {'url': url, 'pid': process.pid, 'database': str(temp / 'test.db')}
                finally:
                    # Own process group only: no command-line pattern matching.
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.wait()
                    # Close any children still alive after the parent exited.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', default='.')
    parser.add_argument('--static-child', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('run as lab, never root')
    if args.static_child is not None:
        handler = functools.partial(PublicHandler, directory=str(Path(args.app_dir) / 'public'))
        httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler, bind_and_activate=False)
        httpd.socket.close()
        httpd.socket = socket.socket(fileno=args.static_child)
        httpd.server_address = httpd.socket.getsockname()
        httpd.serve_forever()
        return
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    try:
        with server(args.app_dir) as info:
            print(json.dumps(info), flush=True)
            print('Loopback only; Ctrl-C stops the server and removes its temporary database.', flush=True)
            while True:
                signal.pause()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
