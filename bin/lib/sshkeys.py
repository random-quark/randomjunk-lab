"""Bounded public-key validation and unprivileged authorized_keys updates."""
import base64
import os
from pathlib import Path
import pwd
import subprocess
import tempfile

from labcore import LabError


def public_key(value):
    if not isinstance(value, str) or len(value) > 16384 or any(ord(c) < 32 for c in value.strip()):
        raise LabError('Paste one SSH public key, not a private key or multiple lines.')
    parts = value.strip().split()
    if len(parts) < 2 or parts[0] not in {'ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521'}:
        raise LabError('Use an OpenSSH public key beginning ssh-ed25519, ssh-rsa or ecdsa-sha2-. No key options.')
    try:
        blob = base64.b64decode(parts[1], validate=True)
        size = int.from_bytes(blob[:4], 'big')
        if blob[4:4 + size].decode('ascii') != parts[0]:
            raise ValueError()
    except (ValueError, UnicodeError):
        raise LabError('Invalid SSH public key.') from None
    key = ' '.join(parts[:2])  # Comments never become shell or authorized_keys options.
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'key.pub'
        path.write_text(key + '\n')
        result = subprocess.run(['/usr/bin/ssh-keygen', '-l', '-f', str(path)], capture_output=True)
    if result.returncode:
        raise LabError('Invalid SSH public key.')
    return key


# This code runs as lab, never root: even a replaced/symlinked home cannot redirect
# privileged writes. Refuse symlinks, unexpected ownership and oversized files.
WRITER = r'''
import fcntl, os, pathlib, stat, sys
key = sys.stdin.read().strip()
home = pathlib.Path.home()
os.chdir(home)
try: os.mkdir('.ssh', 0o700)
except FileExistsError: pass
d = os.open('.ssh', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
assert os.fstat(d).st_uid == os.getuid(), 'SSH directory must belong to lab'
os.fchmod(d, 0o700)
f = os.open('authorized_keys', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=d)
with os.fdopen(f, 'r+') as stream:
    fcntl.flock(stream, fcntl.LOCK_EX)
    info = os.fstat(stream.fileno())
    assert stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1 and info.st_size < 1048576, 'Unsafe authorized_keys file'
    lines = stream.read()
    if not any(line.split()[:2] == key.split() for line in lines.splitlines()):
        stream.seek(0, 2)
        stream.write(('\n' if lines and not lines.endswith('\n') else '') + key + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.fchmod(stream.fileno(), 0o600)
os.close(d)
'''


def authorize_lab_key(value):
    if os.geteuid() != 0:
        raise LabError('Only an administrator can authorize a laptop key.')
    key = public_key(value)
    try:
        user = pwd.getpwnam('lab')
    except KeyError:
        raise LabError('Install the core first to create lab.') from None
    result = subprocess.run(['/usr/sbin/runuser', '-u', 'lab', '--', '/usr/bin/python3', '-I', '-c', WRITER],
                            input=key, text=True, capture_output=True,
                            env={'PATH': '/usr/bin:/bin', 'HOME': user.pw_dir})
    if result.returncode:
        raise LabError('Could not authorize the key. Inspect lab SSH directory ownership and permissions.')
