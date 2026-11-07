import base64
import os
from pathlib import Path
import subprocess
import sys

import pytest
from labcore import LabError
from sshkeys import public_key, WRITER

KEY = 'ssh-ed25519 ' + base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + bytes(range(32))).decode()


def test_key_validation_strips_comments_and_rejects_private_options_and_truncation():
    assert public_key(KEY + ' laptop $(evil)') == KEY
    for key in ['-----BEGIN OPENSSH PRIVATE KEY-----', 'command="evil" ' + KEY,
                KEY + '\n' + KEY, 'ssh-ed25519 YWJj', KEY.replace('ssh-ed25519 ', 'ssh-rsa ', 1)]:
        with pytest.raises(LabError):
            public_key(key)


def run_writer(home, key=KEY):
    return subprocess.run([sys.executable, '-I', '-c', WRITER], input=key, text=True,
                          env={**os.environ, 'HOME': str(home)}, capture_output=True)


def test_writer_preserves_existing_and_is_idempotent(tmp_path):
    directory = tmp_path / '.ssh'
    directory.mkdir()
    target = directory / 'authorized_keys'
    target.write_text('# existing comment without newline')
    assert run_writer(tmp_path).returncode == 0
    first = target.read_text()
    assert first == '# existing comment without newline\n' + KEY + '\n'
    assert run_writer(tmp_path).returncode == 0
    assert target.read_text() == first
    assert target.stat().st_mode & 0o777 == 0o600
    assert directory.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize('kind', ['directory-symlink', 'file-symlink', 'hardlink'])
def test_writer_refuses_redirected_targets(tmp_path, kind):
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'authorized_keys'
    sentinel.write_text('unchanged')
    ssh = tmp_path / '.ssh'
    if kind == 'directory-symlink':
        ssh.symlink_to(outside)
    else:
        ssh.mkdir()
        if kind == 'file-symlink':
            (ssh / 'authorized_keys').symlink_to(sentinel)
        else:
            os.link(sentinel, ssh / 'authorized_keys')
    assert run_writer(tmp_path).returncode != 0
    assert sentinel.read_text() == 'unchanged'
