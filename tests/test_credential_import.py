"""Optional initial integrations, with fixture credentials in isolated files."""
import importlib.util
import os
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('credential_import',Path(__file__).parents[1]/'tools/import-credentials.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def write(path,text):
    path.write_text(text);path.chmod(0o600)

@pytest.fixture
def dirs(tmp_path):
    source=tmp_path/'staged';target=tmp_path/'target';source.mkdir();target.mkdir()
    write(target/'secrets.env','UNCHANGED_SETTING=oldkey\n')
    write(target/'backup.env','RESTIC_PASSWORD=oldpass\n')
    write(target/'notify.env','NTFY_TOPIC=oldtopic\n')
    return source,target

def test_single_provider_preserves_other_settings(dirs,capsys):
    source,target=dirs
    write(source/'providers.env','OPENROUTER_API_KEY=newkey\n')
    old=(target/'notify.env').read_bytes()
    module.import_staged(source,target,os.getgid())
    assert module.read_env(target/'secrets.env')=={'UNCHANGED_SETTING':'oldkey','OPENROUTER_API_KEY':'newkey'}
    assert (target/'notify.env').read_bytes()==old
    assert 'newkey' not in capsys.readouterr().out
    assert (target/'secrets.env').stat().st_mode&0o777==0o600

def test_notifications_without_ai(dirs,capsys):
    source,target=dirs
    write(source/'ntfy.env','NTFY_URL=https://ntfy.sh\nNTFY_TOPIC=topic\n')
    old=(target/'secrets.env').read_bytes()
    module.import_staged(source,target,os.getgid())
    assert (target/'secrets.env').read_bytes()==old
    assert module.read_env(target/'backup.env')['RESTIC_PASSWORD']=='oldpass'
    assert module.read_env(target/'notify.env')['NTFY_TOPIC']=='topic'
    assert (target/'notify.env').stat().st_mode&0o777==0o640
    assert 'oldpass' not in capsys.readouterr().out

@pytest.mark.parametrize('invalid',['INVALID_KEY=fixture\n','OPENAI_API_KEY=\n',''])
def test_invalid_provider_fails_without_writes(dirs,invalid):
    source,target=dirs;write(source/'providers.env',invalid)
    before={p.name:p.read_bytes() for p in target.iterdir()}
    with pytest.raises(module.LabError):module.import_staged(source,target,os.getgid())
    assert before=={p.name:p.read_bytes() for p in target.iterdir()}

def test_bad_notify_validated_before_provider_write(dirs):
    source,target=dirs;write(source/'providers.env','OPENAI_API_KEY=newkey\n');write(source/'ntfy.env','NTFY_TOPIC=fixture\n')
    before=(target/'secrets.env').read_bytes()
    with pytest.raises(module.LabError):module.import_staged(source,target,os.getgid())
    assert (target/'secrets.env').read_bytes()==before

def test_symlink_rejected(dirs):
    source,target=dirs;write(source/'other','OPENAI_API_KEY=fixture\n');(source/'providers.env').symlink_to(source/'other')
    with pytest.raises(module.LabError):module.import_staged(source,target,os.getgid())

def test_no_selection_fails_safely(dirs):
    source,target=dirs
    with pytest.raises(module.LabError):module.import_staged(source,target,os.getgid())
