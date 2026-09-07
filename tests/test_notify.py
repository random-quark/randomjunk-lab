import json
import os
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('body,click,expected', [
    ('Game ready: https://example.com', None, None),
    ('https://example.com', None, 'https://example.com'),
    ('Game ready: https://example.com', 'https://example.com', 'https://example.com'),
    ('@literal-message', None, None),
    ('Ready', 'https://example.com/?q=a,b;c', 'https://example.com/?q=a,b;c'),
])
def test_notification_actions(tmp_path, body, click, expected):
    result, args = invoke(tmp_path, body, click)
    assert result.returncode == 0
    payload = args['payload']
    assert payload['message'] == (expected or body)
    assert 'click' not in payload
    assert payload['title'] == 'Ready'
    if expected:
        assert payload['actions'] == [
            {'action': 'copy', 'label': 'Copy link', 'value': expected},
            {'action': 'view', 'label': 'Open in browser', 'url': expected},
        ]
    else:
        assert 'actions' not in payload

@pytest.mark.parametrize('click', ['not a url', 'https://example.com\nInjected: yes', 'javascript:alert(1)'])
def test_invalid_click_never_sends(tmp_path, click):
    result, args = invoke(tmp_path, 'message', click)
    assert result.returncode != 0
    assert args is None

def invoke(tmp_path, body, click):
    conf = tmp_path / 'notify.env'
    conf.write_text('NTFY_URL=https://example.invalid\nNTFY_TOPIC=dummy\n')
    script = tmp_path / 'notify'
    script.write_text((ROOT / 'bin/notify').read_text().replace('CONF=/etc/lab/notify.env', 'CONF=' + str(conf)))
    capture = tmp_path / 'args.json'
    curl = tmp_path / 'curl'
    curl.write_text('#!/usr/bin/python3\nimport json,os,sys\nopen(os.environ["CAPTURE"],"w").write(json.dumps({"args":sys.argv[1:],"payload":json.load(sys.stdin)}))\n')
    curl.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + ':/usr/bin:/bin', CAPTURE=str(capture))
    command = ['bash', str(script), 'Ready', body] + ([] if click is None else [click])
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    return result, json.loads(capture.read_text()) if capture.exists() else None
