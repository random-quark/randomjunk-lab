"""Private onboarding boundaries; fixture secrets only, no live external services."""
import importlib.util
import json
import os
from pathlib import Path
import threading
import tempfile
import urllib.error
import urllib.request

import pytest

spec = importlib.util.spec_from_file_location('setup_wizard', Path(__file__).parents[1] / 'tools/setup-wizard.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

@pytest.fixture
def wizard(tmp_path):
    private = tmp_path / 'private'
    private.mkdir(mode=0o700)
    return w.Wizard(private, sender=lambda topic: None)


def save(wizard, choices=None, keys=None, remove=None):
    return wizard.action('save', {'choices': choices or {}, 'secrets': keys or {}, 'remove': remove or []})


def finish(wizard):
    save(wizard, {'DOMAIN': 'lab.example.com', 'NOTIFICATIONS': 'skip', 'BACKUPS': 'skip'})
    wizard.action('finish', {})


def test_optional_keys_and_private_resumable_storage(wizard):
    save(wizard, keys={'REPLICATE_API_TOKEN': 'fixture-secret'})
    snapshot = wizard.status()
    assert snapshot['saved_keys'] == ['REPLICATE_API_TOKEN']
    assert 'fixture-secret' not in json.dumps(snapshot)
    assert (wizard.directory / 'setup.json').stat().st_mode & 0o777 == 0o600
    save(wizard, {'PROJECT_NAME': 'New name'})
    assert wizard.data['secrets']['REPLICATE_API_TOKEN'] == 'fixture-secret'
    again = w.Wizard(wizard.directory)
    assert again.data['choices']['PROJECT_NAME'] == 'New name'
    assert again.token != wizard.token
    save(again, remove=['REPLICATE_API_TOKEN'])
    assert not again.data['secrets']


@pytest.mark.parametrize('keys', [
    {'BAD_KEY': 'fixture'}, {'OPENAI_API_KEY': 'line\nINJECTED=oops'},
    {'OPENAI_API_KEY': '\x00bad'}, {'STRIPE_SECRET_KEY': 'sk_live_fixture'},
    {'OPENAI_API_KEY': ''}, {'OPENAI_API_KEY': []},
    {'OPENAI_API_KEY': 'line\u2028INJECTED=oops'},
    {'OPENAI_API_KEY': 'line\x85INJECTED=oops'},
    {'OPENAI_API_KEY': 'line\u2029INJECTED=oops'},
])
def test_invalid_secret_does_not_change_anything(wizard, keys):
    before = (wizard.directory / 'setup.json').read_bytes()
    with pytest.raises(w.LabError):
        save(wizard, {'PROJECT_NAME': 'Should not change'}, keys)
    assert (wizard.directory / 'setup.json').read_bytes() == before


def test_invalid_choices_and_removal_fail_atomically(wizard):
    before = wizard.data.copy()
    for choices in [{'DOMAIN': 'x; touch /tmp/bad'}, {'SSH_PORT': '0'}, {'SSH_PORT': '65536'},
                    {'NOTIFICATIONS': 'custom'}, {'NTFY_URL': 'http://localhost'}, {'DOMAIN': []}]:
        with pytest.raises(w.LabError):
            save(wizard, choices)
    with pytest.raises(w.LabError):
        save(wizard, remove=[{}])
    assert wizard.data == before


def test_finish_requires_decisions_but_no_paid_provider(wizard):
    with pytest.raises(w.LabError):
        wizard.action('finish', {})
    finish(wizard)
    assert wizard.data['finished']
    assert not wizard.data['secrets']
    with pytest.raises(w.LabError):
        save(wizard)


def test_notifications_require_send_and_owner_receipt(wizard):
    topic = wizard.action('topic', {})['topic']
    assert topic.startswith('lab-')
    assert topic not in json.dumps(wizard.status())
    assert wizard.action('subscription', {})['topic'] == topic
    with pytest.raises(w.LabError):
        wizard.action('confirm-ntfy', {})
    wizard.action('test-ntfy', {})
    assert wizard.status()['notification'] == 'sent'
    with pytest.raises(w.LabError):
        wizard.action('test-ntfy', {})  # Rate limit prevents repeated sends.
    save(wizard, {'DOMAIN': 'lab.example.com', 'BACKUPS': 'skip'})
    with pytest.raises(w.LabError):
        wizard.action('finish', {})
    wizard.action('confirm-ntfy', {})
    wizard.action('finish', {})


def test_failure_does_not_leak_topic(wizard):
    wizard.action('topic', {})
    def fail(topic):
        raise OSError('https://ntfy.sh/' + topic)
    wizard.sender = fail
    with pytest.raises(w.LabError) as exc:
        wizard.action('test-ntfy', {})
    assert wizard.data['topic'] not in str(exc.value)
    assert wizard.status()['notification'] == 'failed'


def test_selected_backup_requires_recovery_copy(wizard):
    save(wizard, {'DOMAIN': 'lab.example.com', 'NOTIFICATIONS': 'skip', 'BACKUPS': 'b2',
                  'B2_BUCKET': 'bucket', 'B2_ENDPOINT': 's3.example.com', 'BACKUP_SERVER_NAME': 'one'},
         {'B2_KEY_ID': 'id', 'B2_APP_KEY': 'key', 'RESTIC_PASSWORD': 'password'})
    with pytest.raises(w.LabError, match='outside'):
        wizard.action('finish', {})
    save(wizard, {'RECOVERY_DETAILS_SAVED': 'yes'})
    wizard.action('finish', {})


def test_bundle_rejects_symlink_or_loose_permissions(wizard):
    path = wizard.directory / 'setup.json'
    path.chmod(0o644)
    with pytest.raises(w.LabError):
        w.read_bundle(wizard.directory)
    path.chmod(0o600)
    original = wizard.directory / 'original'
    path.rename(original)
    path.symlink_to(original)
    with pytest.raises(OSError):
        w.read_bundle(wizard.directory)


@pytest.fixture
def http(wizard):
    server = w.make_server(wizard, {'/': ('text/html', b'fixture')}, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    def request(path='/api/status', token=True, origin=None, body=None, host=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + wizard.token
        if origin:
            headers['Origin'] = origin
        if host:
            headers['Host'] = host
        req = urllib.request.Request(base + path, headers=headers, data=json.dumps(body).encode() if body is not None else None)
        try:
            return urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as response:
            return response
    yield request
    server.shutdown()
    thread.join(timeout=3)
    server.server_close()


def test_http_auth_origin_host_expiry_and_headers(wizard, http):
    assert http(token=False).status == 401
    assert http(origin='https://evil.example').status == 403
    assert http(host='evil.example').status == 403
    response = http()
    assert response.status == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    wizard.expires = 0
    assert http().status == 401


def test_http_save_and_closed_session(wizard, http):
    response = http('/api/save', body={'choices': {'DOMAIN': 'lab.example.com', 'NOTIFICATIONS': 'skip', 'BACKUPS': 'skip'},
                                      'secrets': {'OPENAI_API_KEY': 'fixture-secret'}, 'remove': []})
    assert response.status == 200
    assert b'fixture-secret' not in response.read()
    assert http('/api/finish', body={}).status == 200
    assert http().status == 401
    assert http('/api/save', body={}).status == 401


def test_http_rejects_unknown_action_and_oversized_body(http):
    assert http('/api/run-shell', body={'command': 'id'}).status == 400
    assert http('/api/save', body={'value': 'x' * 66000}).status == 400


def test_apply_preserves_existing_and_does_not_activate_skipped(wizard, tmp_path):
    save(wizard, keys={'REPLICATE_API_TOKEN': 'fixture-secret'})
    finish(wizard)
    stage = tmp_path / 'staged'
    w.stage_bundle(wizard.data, stage)
    target = tmp_path / 'target'
    target.mkdir(mode=0o700)
    w.atomic_write(target / 'secrets.env', 'UNCHANGED_KEY=keep\n')
    w.atomic_write(target / 'backup.env', 'RESTIC_PASSWORD=existing\n')
    w.atomic_write(target / 'notify.env', 'NTFY_TOPIC=existing\n')
    w.apply_integrations(wizard.data, target, stage, os.getgid())
    assert w.read_env(target / 'secrets.env') == {'UNCHANGED_KEY': 'keep', 'REPLICATE_API_TOKEN': 'fixture-secret'}
    assert (target / 'notify.env').read_text() == 'NTFY_TOPIC=existing\n'
    assert (target / 'backup.env').read_text() == 'RESTIC_PASSWORD=existing\n'
    for name in ['owner-settings.txt', 'capabilities.json']:
        assert 'fixture-secret' not in (stage / name).read_text()
    assert (target / 'secrets.env').stat().st_mode & 0o777 == 0o600
    assert not (target / 'stripe.env').exists()


def test_apply_ntfy_email_and_separate_test_payment(wizard, tmp_path):
    wizard.action('topic', {})
    wizard.action('test-ntfy', {})
    wizard.action('confirm-ntfy', {})
    save(wizard, {'DOMAIN': 'lab.example.com', 'BACKUPS': 'skip', 'EMAIL_PROVIDER': 'resend',
                  'EMAIL_SENDING_DOMAIN': 'mail.example.com', 'PAYMENTS_PROVIDER': 'stripe'},
         {'RESEND_API_KEY': 'fixture-email', 'STRIPE_SECRET_KEY': 'sk_test_fixture'})
    wizard.action('finish', {})
    stage = tmp_path / 'staged'
    w.stage_bundle(wizard.data, stage)
    target = tmp_path / 'target'
    target.mkdir(mode=0o700)
    w.atomic_write(target / 'secrets.env', 'UNCHANGED_KEY=keep\n')
    w.atomic_write(target / 'backup.env', 'RESTIC_PASSWORD=existing\n')
    w.apply_integrations(wizard.data, target, stage, os.getgid())
    assert w.read_env(target / 'notify.env')['NTFY_URL'] == 'https://ntfy.sh'
    assert (target / 'notify.env').stat().st_mode & 0o777 == 0o640
    assert w.read_env(target / 'backup.env')['RESTIC_PASSWORD'] == 'existing'
    assert w.read_env(target / 'secrets.env') == {'UNCHANGED_KEY': 'keep', 'RESEND_API_KEY': 'fixture-email'}
    assert w.read_env(target / 'stripe.env') == {'STRIPE_SECRET_KEY': 'sk_test_fixture'}
    assert json.loads((target / 'email.json').read_text())['sending_domain'] == 'mail.example.com'


def test_recovery_password_preserves_spaces(wizard):
    save(wizard, keys={'RESTIC_PASSWORD': '  fixture password  '})
    assert wizard.data['secrets']['RESTIC_PASSWORD'] == '  fixture password  '
    assert w.read_bundle(wizard.directory)['secrets']['RESTIC_PASSWORD'] == '  fixture password  '


@pytest.mark.skipif(os.geteuid() != 0, reason='Privilege-drop integration needs root in the disposable test checkout')
def test_root_launcher_drops_privileges_before_binding(monkeypatch):
    # Exercise a real setuid in an isolated child, without creating host users.
    # nobody is only a stand-in for the production dedicated labsetup account.
    with tempfile.TemporaryDirectory(prefix='lab-drop-test-') as directory:
        pid = os.fork()
        if pid == 0:
            try:
                expected = w.pwd.getpwnam('nobody')
                original_lookup = w.pwd.getpwnam
                w.pwd.getpwnam = lambda name: expected if name == 'labsetup' else original_lookup(name)
                original_server = w.make_server
                def checked_server(wizard, assets, port):
                    assert os.geteuid() == expected.pw_uid != 0
                    assert os.getgroups() == []
                    assert (Path(directory) / 'setup.json').stat().st_uid == expected.pw_uid
                    server = original_server(wizard, assets, port)
                    server.serve_forever = lambda: None
                    return server
                w.make_server = checked_server
                w.sys.argv = ['setup-wizard.py', 'serve', '--state-dir', directory, '--port', '0']
                w.sys.stdout = open(os.devnull, 'w')
                w.main()
                os._exit(0)
            except BaseException:
                os._exit(1)
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 0


def test_ip_only_setup_derives_hostname(wizard):
    save(wizard, {'SERVER_IPV4': '8.8.8.8', 'NOTIFICATIONS': 'skip', 'BACKUPS': 'skip'})
    wizard.action('finish', {})
    assert 'DOMAIN=8-8-8-8.sslip.io\n' in w.settings_text(wizard.data)
    assert w.install_domain('lab.example.com') == 'lab.example.com'


@pytest.mark.parametrize('address', ['127.0.0.1', '192.168.1.1', '10.0.0.1', '999.1.1.1', '224.0.0.1'])
def test_non_public_or_invalid_ip_rejected(wizard, address):
    with pytest.raises(w.LabError):
        save(wizard, {'SERVER_IPV4': address})
    with pytest.raises(w.LabError):
        w.install_domain(address)


def test_old_saved_form_without_ip_field_is_upgraded(wizard):
    wizard.data['choices'].pop('SERVER_IPV4')
    wizard.save()
    loaded = w.read_bundle(wizard.directory)
    assert loaded['choices']['SERVER_IPV4'] == ''


def test_agent_can_review_unfinished_form_without_secret_values(wizard, monkeypatch, capsys):
    save(wizard, {'SERVER_IPV4': '8.8.8.8', 'BACKUPS': 'b2'},
         {'REPLICATE_API_TOKEN': 'fixture-private-token'})
    wizard.action('topic', {})
    before = (wizard.directory / 'setup.json').read_bytes()
    monkeypatch.setattr(w.sys, 'argv', ['setup-wizard.py', 'review', '--state-dir', str(wizard.directory)])
    monkeypatch.setattr(w.os, 'geteuid', lambda: 0)
    w.main()
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report['choices']['BACKUPS'] == 'b2'
    assert report['finished'] is False
    assert report['saved_keys'] == ['REPLICATE_API_TOKEN']
    assert 'fixture-private-token' not in output
    assert wizard.data['topic'] not in output
    assert (wizard.directory / 'setup.json').read_bytes() == before


def test_review_missing_form_explains_handoff(tmp_path, monkeypatch):
    monkeypatch.setattr(w.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(w.sys, 'argv', ['setup-wizard.py', 'review', '--state-dir', str(tmp_path / 'absent')])
    with pytest.raises(w.LabError, match='No saved setup form'):
        w.main()
