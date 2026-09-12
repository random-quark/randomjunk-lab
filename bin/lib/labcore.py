"""Shared pure validation and durable filesystem primitives; Python stdlib only."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import tempfile

VERSION = 3
RESERVED = {'state', 'docs', 'templates', 'backup', 'lost-found', 'apps'}

class LabError(RuntimeError):
    pass

def name(value):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,22}[a-z0-9]', value) or value in RESERVED:
        raise LabError('invalid app name (2–24 lowercase DNS-label characters)')
    return value

def domain(value):
    if len(value) > 253 or '.' not in value or any(
        not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part)
        for part in value.split('.')
    ):
        raise LabError('invalid domain')
    return value

def keys(value):
    result = value.split(',') if value else []
    if any(not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) for key in result):
        raise LabError('invalid secret key list')
    if 'DATABASE_URL' in result or 'PORT' in result or 'APP_NAME' in result:
        raise LabError('platform-managed environment keys cannot be granted')
    return sorted(set(result))

def protected_dir(path):
    st = Path(path).lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
        raise LabError(f'expected root-owned non-writable directory: {path}')

def atomic_write(path, data, mode=0o600):
    """Caller must own and protect the parent; replace links, never follow them."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data.encode() if isinstance(data, str) else data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)

def write_json(path, value):
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True) + '\n')

def read_env(path):
    """Literal KEY=value format. No shell expansion, quotes or escape decoding."""
    values = {}
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) or key in values:
            raise LabError('invalid or duplicate environment key')
        if '\x00' in value:
            raise LabError('NUL in environment value')
        values[key] = value
    return values

def systemd_env(values):
    def quote(value):
        if any(c in value for c in '\n\r\x00'):
            raise LabError('environment values must be single-line')
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return ''.join(f'{key}={quote(value)}\n' for key, value in sorted(values.items()))

@contextlib.contextmanager
def locked(path):
    # No caller-provided marker can bypass this lock.
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
            raise LabError('unsafe lock file')
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)

def caddy_site(rec, dom, root, public='/var/lib/lab-public', tls_mode='production'):
    """Only structured platform data can influence Caddy directives."""
    app = name(rec['name'])
    domain(dom)
    aliases = rec.get('aliases', [])
    if not isinstance(aliases, list) or any(not isinstance(a, str) for a in aliases):
        raise LabError('invalid aliases')
    hosts = [app] + [name(a) for a in aliases]
    if len(set(hosts)) != len(hosts):
        raise LabError('duplicate aliases')
    lines = [', '.join(f'{host}.{dom}' for host in hosts) + ' {', '\tencode gzip']
    if tls_mode == 'internal' and dom.endswith('.test'):
        lines.append('\ttls internal')
    elif tls_mode != 'production':
        raise LabError('internal TLS is restricted to a .test domain')
    if rec['private']:
        hashed = rec['auth_hash']
        if not re.fullmatch(r'\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}', hashed):
            raise LabError('invalid basic-auth hash')
        lines += ['\tbasic_auth {', '\t\tlab ' + hashed, '\t}']
    if rec['kind'] == 'static':
        revision = rec.get('public_revision', '')
        if not re.fullmatch(r'[a-f0-9]{32}', revision):
            raise LabError('static app has no valid published snapshot')
        lines += [f'\troot * {public}/{app}-{revision}', '\tfile_server']
    elif rec['kind'] == 'app' and type(rec['port']) is int and 8100 <= rec['port'] < 8999:
        lines += [f'\treverse_proxy 127.0.0.1:{rec["port"]}']
    else:
        raise LabError('invalid site type or port')
    return '\n'.join(lines + ['}', ''])
