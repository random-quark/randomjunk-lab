import base64
import json
import threading
import time
import urllib.error
import urllib.request

import pytest
from access import Invitations, server
from labcore import LabError, caddy_site


def key(seed):
    return 'ssh-ed25519 ' + base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + bytes([seed]) * 32).decode()


@pytest.fixture
def store(tmp_path):
    writes = []
    return Invitations(tmp_path / 'invites.sqlite', writes.append), writes


def test_one_key_retry_and_no_plaintext_token(store):
    invites, writes = store
    token, digest = invites.create()
    assert token.encode() not in invites.path.read_bytes()
    assert not invites.status(token)['used']
    assert invites.enroll(token, key(1))['enabled']
    assert invites.status(token)['used']
    assert invites.enroll(token, key(1) + ' changed-comment')['enabled']
    with pytest.raises(LabError, match='another key'):
        invites.enroll(token, key(2))
    assert writes == [key(1), key(1)]


def test_bad_key_does_not_consume_invite(store):
    invites, writes = store
    token, _ = invites.create()
    with pytest.raises(LabError):
        invites.enroll(token, 'PRIVATE KEY')
    assert not writes
    assert invites.enroll(token, key(2))['enabled']


def test_partial_write_still_binds_one_key(store):
    invites, writes = store
    token, _ = invites.create()
    def fail(value):
        writes.append(value)
        raise LabError('simulated interrupted write')
    invites.writer = fail
    with pytest.raises(LabError):
        invites.enroll(token, key(1))
    invites.writer = writes.append
    with pytest.raises(LabError, match='another key'):
        invites.enroll(token, key(2))
    assert invites.enroll(token, key(1))['enabled']


@pytest.mark.parametrize('kind', ['missing', 'wrong', 'expired', 'revoked'])
def test_denied_invites_never_write(store, kind):
    invites, writes = store
    token, digest = invites.create()
    if kind == 'missing': token = ''
    if kind == 'wrong': token = 'x' * 43
    if kind == 'expired':
        with invites.connect() as db:
            db.execute('UPDATE invitations SET expires=?', (time.time() - 1,))
    if kind == 'revoked': invites.revoke(digest)
    with pytest.raises(LabError):
        invites.enroll(token, key(1))
    assert writes == []


def test_http_origin_auth_and_body_limits(store):
    invites, writes = store
    token, _ = invites.create()
    http = server(invites, 'https://welcome.example.com', 0)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{http.server_port}/_lab/access/enroll'
    def request(origin='https://welcome.example.com', auth=token, body=None):
        data = json.dumps(body or {'public_key': key(1)}).encode()
        req = urllib.request.Request(url, data=data, headers={
            'Origin': origin, 'Authorization': 'Bearer ' + auth, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req) as response:
                assert response.headers['Cache-Control'] == 'no-store'
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
    try:
        assert request(origin='https://evil.example') == 403
        assert request(auth='') == 400
        assert request(body={'public_key': 'x' * 19000}) == 413
        assert writes == []
        assert request() == 200
        assert writes == [key(1)]
    finally:
        http.shutdown(); http.server_close(); thread.join()


def test_only_selected_site_has_access_route():
    record = {'name': 'welcome', 'kind': 'static', 'private': False, 'public_revision': 'a' * 32}
    assert '/_lab/access/' not in caddy_site(record, 'example.com', '/srv/lab')
    assert 'reverse_proxy /_lab/access/* 127.0.0.1:9876' in caddy_site(record, 'example.com', '/srv/lab', access=True)


def test_notifications_require_enrollment_and_receipt_and_keep_recipients_separate(store):
    invites, _ = store
    sent = []
    invites.sender = lambda *args: sent.append(args)
    owner, _ = invites.create()
    friend, _ = invites.create()
    with pytest.raises(LabError, match='Enable SSH'):
        invites.notification(owner, 'start')
    invites.enroll(owner, key(1))
    invites.enroll(friend, key(2))
    a = invites.notification(owner, 'start')
    b = invites.notification(friend, 'start')
    assert a['topic'] != b['topic']
    assert a['recipient'] != b['recipient']
    with pytest.raises(LabError, match='Send a test'):
        invites.notification(owner, 'confirm')
    with pytest.raises(LabError, match='not confirmed'):
        invites.notify(a['recipient'], 'Ready', 'https://app.example')
    assert invites.notification(owner, 'test')['state'] == 'pending'
    with pytest.raises(LabError, match='30 seconds'):
        invites.notification(owner, 'test')
    assert invites.notification(owner, 'confirm')['state'] == 'ready'
    invites.notify(a['recipient'], 'Ready', 'https://app.example')
    assert sent[-1] == (a['topic'], 'Ready', 'https://app.example')
    invites.notification(friend, 'skip')
    assert invites.notification(owner, 'status')['state'] == 'ready'
    invites.notification(owner, 'skip')
    with pytest.raises(LabError, match='not confirmed'):
        invites.notify(a['recipient'], 'Ready', 'https://app.example')
    assert len(sent) == 2


def test_failed_notification_cannot_be_confirmed_and_revoked_invite_is_denied(store):
    invites, _ = store
    token, digest = invites.create()
    invites.enroll(token, key(1))
    invites.notification(token, 'start')
    def fail(*args):
        raise LabError('unavailable')
    invites.sender = fail
    with pytest.raises(LabError, match='unavailable'):
        invites.notification(token, 'test')
    with pytest.raises(LabError, match='Send a test'):
        invites.notification(token, 'confirm')
    invites.revoke(digest)
    with pytest.raises(LabError, match='revoked'):
        invites.notification(token, 'status')


def test_notification_settings_survive_invitation_renewal(store):
    invites, _ = store
    token, _ = invites.create()
    invites.enroll(token, key(1))
    first = invites.notification(token, 'start')
    renewed, _ = invites.create()
    invites.enroll(renewed, key(1))
    assert invites.notification(renewed, 'start')['topic'] == first['topic']
    with pytest.raises(LabError):
        invites.notify(first['recipient'], 'Ready', 'http://app.example')


def test_notification_http_requires_origin_and_invitation(store):
    invites, _ = store
    token, _ = invites.create()
    invites.enroll(token, key(1))
    sent = []
    invites.sender = lambda *args: sent.append(args)
    http = server(invites, 'https://welcome.example.com', 0)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    def call(action, auth=token, origin='https://welcome.example.com'):
        req = urllib.request.Request(f'http://127.0.0.1:{http.server_port}/_lab/access/notifications',
            data=json.dumps({'action': action}).encode(), headers={
                'Origin': origin, 'Authorization': 'Bearer ' + auth, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)
    try:
        assert call('start', auth='')[0] == 400
        assert call('start', origin='https://evil.example')[0] == 403
        assert call('start')[1]['state'] == 'pending'
        assert call('confirm')[0] == 400
        assert call('test')[1]['state'] == 'pending'
        assert call('confirm')[1]['state'] == 'ready'
        assert len(sent) == 1
    finally:
        http.shutdown(); http.server_close(); thread.join()


def test_sender_uses_fixed_https_and_url_actions(monkeypatch):
    from access import send_notification
    requests = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class Opener:
        def open(self, request, timeout):
            requests.append((request, timeout))
            return Response()
    monkeypatch.setattr(urllib.request, 'build_opener', lambda *args: Opener())
    send_notification('test-topic', 'Ready', 'https://app.example')
    req, timeout = requests[0]
    assert req.full_url == 'https://ntfy.sh'
    assert timeout == 8
    payload = json.loads(req.data)
    assert payload['message'] == 'https://app.example'
    assert payload['actions'][0]['value'] == 'https://app.example'
    assert payload['actions'][1]['url'] == 'https://app.example'
    assert 'click' not in payload
