import argparse
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import pwd
import sqlite3
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
import controller
from controller import Controller
import labcore
from labcore import LabError, atomic_write, caddy_site, keys, locked, name, read_env, systemd_env, write_json
from sqlite_worker import snapshot

ROOT = Path(__file__).resolve().parents[1]
HASH = '$2a$14$' + 'A'*53

def rec(app='demo', kind='app', db='none'):
    return {'version':3, 'name':app, 'kind':kind, 'db':db, 'private':False,
            'title':app, 'port':8100 if kind == 'app' else None, 'grants':[],
            'created':'2026-09-07T00:00:00+00:00', 'status':'prepared',
            'resources':{'identity':True, 'identity_intent':True, 'code':True}}

@pytest.fixture
def ctl(tmp_path):
    c = Controller()
    c.root = tmp_path/'srv'
    c.public = tmp_path/'public'
    c.state = tmp_path/'state'
    c.etc = tmp_path/'etc'
    c.units = tmp_path/'units'
    c.caddy = tmp_path/'caddy'
    for d in (c.root,c.public,c.state,c.state/'records',c.state/'credentials',c.etc,c.etc/'apps',c.units,c.caddy):
        d.mkdir(mode=0o700)
    write_json(c.etc/'platform.json', {'version':3, 'domain':'example.test'})
    (c.etc/'secrets.env').write_text('FIRST=dummy-one\nSECOND=dummy-two\n')
    (c.caddy/'lab-sites.caddy').write_text('previous site configuration\n')
    (c.caddy/'Caddyfile').write_text('{\n\tadmin unix//run/caddy/admin.sock\n\tskip_install_trust\n}\nimport /etc/caddy/lab-sites.caddy\n')
    return c

@pytest.mark.parametrize('value', ['../aa','a','a'*25,'-ab','ab-','ab\nfoo','a.b','docs'])
def test_names_reject_invalid(value):
    with pytest.raises(LabError): name(value)

@pytest.mark.parametrize('value', ['ab','a-b','a'*24])
def test_names_accept_portable_identity(value):
    assert len('labapp-'+name(value)) <= 32

@pytest.mark.parametrize('value', ['A,,B',',A','A,','1A','DATABASE_URL','PORT'])
def test_grant_keys_reject_invalid_or_platform_names(value):
    with pytest.raises(LabError): keys(value)

def test_atomic_failure_preserves_prior_record(tmp_path, monkeypatch):
    path=tmp_path/'state.json'
    write_json(path, {'old': True})
    def fail(*a): raise OSError('simulated interrupted replace')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError): write_json(path, {'new': True})
    assert json.loads(path.read_text()) == {'old':True}
    assert list(tmp_path.iterdir()) == [path]

def test_atomic_write_replaces_link_not_target(tmp_path):
    target=tmp_path/'dummy'
    target.write_text('preserve')
    link=tmp_path/'state'
    link.symlink_to(target)
    atomic_write(link, 'replacement')
    assert not link.is_symlink() and target.read_text() == 'preserve'

def test_environment_is_literal_and_rejects_duplicates(tmp_path):
    p=tmp_path/'env'
    p.write_text('KEY=$(no-execution) # literal\n')
    assert read_env(p)['KEY'] == '$(no-execution) # literal'
    assert systemd_env({'KEY':'quote" slash\\ $value'}) == 'KEY="quote\\" slash\\\\ $value"\n'
    p.write_text('KEY=one\nKEY=two\n')
    with pytest.raises(LabError): read_env(p)

def test_successive_grants_preserve_postgres(ctl):
    r=rec(db='postgres')
    ctl.save(r)
    url='postgresql+psycopg://dummy:dummy@localhost/dummy'
    write_json(ctl.state/'credentials/demo.json', {'DATABASE_URL':url})
    ctl.grant('demo','FIRST')
    ctl.grant('demo','SECOND')
    text=(ctl.etc/'apps/demo.env').read_text()
    assert all(value in text for value in (url, 'dummy-one', 'dummy-two'))
    assert ctl.record('demo')['grants'] == ['FIRST','SECOND']
    assert (ctl.etc/'apps/demo.env').stat().st_mode & 0o777 == 0o600
    before=text
    with pytest.raises(LabError): ctl.grant('demo','MISSING')
    assert (ctl.etc/'apps/demo.env').read_text() == before
    assert ctl.record('demo')['grants'] == ['FIRST','SECOND']

def test_unit_never_defaults_to_root():
    text=(ROOT/'etc/lab-app@.service').read_text()
    assert 'User=labapp-%i' in text and 'Group=labapp-%i' in text
    assert 'ConditionPathExists=' in text
    assert 'EnvironmentFile=/etc/lab/apps/%i.env' in text
    assert 'EnvironmentFile=-' not in text

def test_service_rejects_unprovisioned(ctl):
    r=rec(); r['resources']={}; ctl.save(r)
    with pytest.raises(LabError, match='not been provisioned'): ctl.service('start','demo')

def test_effective_root_identity_rejected(ctl,monkeypatch):
    ctl.save(rec()); ctl.dropin('demo').mkdir()
    (ctl.dropin('demo')/'identity.conf').write_text('[Service]\nUser=labapp-demo\nGroup=labapp-demo\n')
    monkeypatch.setattr(pwd,'getpwnam',lambda _:SimpleNamespace(pw_uid=12345,pw_gid=12345))
    ctl.run=Mock(return_value=SimpleNamespace(returncode=0,stdout='root\nroot\n'))
    with pytest.raises(LabError,match='does not match'): ctl.service('enable','demo')
    assert ctl.run.call_count == 1

def test_caddy_structured_only():
    r=rec(); r.update(private=True, auth_hash=HASH)
    text=caddy_site(r,'example.test','/srv/lab')
    assert 'basic_auth' in text and '127.0.0.1:8100' in text
    r['port']='8100\nimport /tmp/untrusted'
    with pytest.raises(LabError): caddy_site(r,'example.test','/srv/lab')
    r['port']=8100; r['auth_hash']='bad\n}'
    with pytest.raises(LabError): caddy_site(r,'example.test','/srv/lab')

def test_caddy_validation_failure_does_not_publish(ctl):
    old=(ctl.caddy/'lab-sites.caddy').read_bytes()
    ctl.run=Mock(side_effect=LabError('validation failed'))
    with pytest.raises(LabError): ctl.caddy_publish([rec()])
    assert (ctl.caddy/'lab-sites.caddy').read_bytes() == old
    assert ctl.run.call_count == 1

def test_caddy_reload_failure_rolls_back(ctl):
    old=(ctl.caddy/'lab-sites.caddy').read_bytes()
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=1 if len(calls)==2 else 0,stdout='')
    ctl.run=run
    with pytest.raises(LabError,match='restored and reloaded'): ctl.caddy_publish([rec()])
    assert (ctl.caddy/'lab-sites.caddy').read_bytes() == old
    assert len(calls)==3

def test_failed_stop_blocks_all_destructive_steps(ctl):
    r=rec(db='postgres');r['resources']['postgres_intent']=True;ctl.save(r)
    directory=ctl.root/'demo';directory.mkdir();(directory/'sentinel').write_text('data')
    ctl.run=Mock(side_effect=LabError('cannot stop'))
    ctl.sql=Mock();ctl.caddy_publish=Mock()
    with pytest.raises(LabError):ctl.remove('demo')
    assert (directory/'sentinel').read_text()=='data'
    ctl.sql.assert_not_called();ctl.caddy_publish.assert_not_called()
    assert ctl.record('demo')['status']=='removal-failed'

def test_static_teardown_never_calls_postgres_and_can_repeat(ctl,monkeypatch):
    ctl.save(rec(kind='static'))
    (ctl.root/'demo').mkdir()
    ctl.run=Mock(return_value=SimpleNamespace(returncode=0,stdout=''))
    ctl.sql=Mock(side_effect=AssertionError('must not touch postgres'))
    def absent(_):raise KeyError()
    monkeypatch.setattr(pwd,'getpwnam',absent)
    ctl.remove('demo');ctl.remove('demo')
    assert not ctl.path('demo').exists() and not (ctl.root/'demo').exists()

def test_removal_does_not_follow_symlinks(ctl,tmp_path,monkeypatch):
    ctl.save(rec(kind='static'))
    outside=tmp_path/'dummy';outside.mkdir();(outside/'keep').write_text('keep')
    container=ctl.root/'demo';container.mkdir();(container/'link').symlink_to(outside,target_is_directory=True)
    ctl.run=Mock(return_value=SimpleNamespace(returncode=0,stdout=''))
    def absent(_):raise KeyError()
    monkeypatch.setattr(pwd,'getpwnam',absent)
    ctl.remove('demo')
    assert (outside/'keep').read_text()=='keep'

def test_root_container_symlink_is_rejected(ctl,tmp_path):
    ctl.save(rec(kind='static'))
    outside=tmp_path/'dummy';outside.mkdir();(ctl.root/'demo').symlink_to(outside)
    with pytest.raises(LabError,match='root-owned'):ctl.remove('demo')
    assert outside.exists()

def test_corrupt_record_prevents_mutation(ctl):
    ctl.path('demo').write_text('{partial')
    with pytest.raises(LabError,match='invalid record'):ctl.remove('demo')

def test_private_verify_passes_credentials_without_printing(ctl,capsys):
    r=rec(kind='static');r['private']=True;r['resources']['caddy']=True;ctl.save(r)
    (ctl.state/'credentials/demo.basic').write_text('dummy-private-password')
    ctl.wait_http=Mock(return_value=True)
    assert ctl.verify('demo')
    assert ctl.wait_http.call_args.kwargs['password']=='dummy-private-password'
    assert 'dummy-private-password' not in capsys.readouterr().out
    assert ctl.record('demo')['status']=='http-verified'

def test_failed_https_is_not_verified(ctl):
    r=rec(kind='static');r['resources']['caddy']=True;ctl.save(r);ctl.wait_http=Mock(return_value=False)
    assert not ctl.verify('demo')
    assert ctl.record('demo')['status']=='verification-pending'

@pytest.mark.parametrize('filename', ["quote'name.db",'question?hash#percent%.sqlite','line\nname.sqlite3'])
def test_sqlite_unusual_filenames_and_consistent_snapshot(tmp_path,filename):
    source=tmp_path/filename
    connection=sqlite3.connect(source)
    connection.execute('pragma journal_mode=wal')
    connection.execute('create table data (value text)')
    connection.execute("insert into data values ('committed')");connection.commit()
    connection.execute("insert into data values ('uncommitted')")
    output=tmp_path/'backup.db'
    snapshot(source,output)
    with sqlite3.connect(output) as restored:
        assert restored.execute('select value from data').fetchall()==[('committed',)]
        assert restored.execute('pragma integrity_check').fetchone()==('ok',)
    connection.rollback();connection.close()

@pytest.fixture
def webapp(tmp_path):
    spec=importlib.util.spec_from_file_location('test_app',ROOT/'templates/app/main.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    public=tmp_path/'public';public.mkdir();(public/'index.html').write_text('<h1>shell</h1>')
    module.PUBLIC=public
    return module,TestClient(module.app),public

def test_real_http_static_and_spa(webapp):
    module,client,public=webapp
    (public/'app.js').write_text('const a=1')
    assert client.get('/').status_code==200
    assert client.get('/app.js').text=='const a=1'
    assert client.get('/navigation',headers={'accept':'text/html'}).text=='<h1>shell</h1>'
    assert client.get('/missing.js',headers={'accept':'text/html'}).status_code==404
    assert client.get('/api/missing',headers={'accept':'text/html'}).status_code==404

def test_index_and_fallback_symlinks_rejected(webapp,tmp_path):
    module,client,public=webapp
    dummy=tmp_path/'dummy';dummy.write_text('outside')
    (public/'index.html').unlink();(public/'index.html').symlink_to(dummy)
    assert client.get('/').status_code==404
    assert client.get('/navigation',headers={'accept':'text/html'}).status_code==404
    (public/'sub').mkdir();(public/'sub/index.html').symlink_to(dummy)
    assert client.get('/sub/').status_code==404
    assert client.get('/%2e%2e/dummy',headers={'accept':'text/html'}).status_code==404

def test_open_descriptor_survives_path_replacement(webapp,tmp_path):
    module,client,public=webapp
    path=public/'asset.txt';path.write_text('original')
    stream,_,_=module.open_public('asset.txt')
    path.unlink();path.symlink_to(tmp_path/'absent')
    with stream: assert stream.read()==b'original'

def _hold_lock(path,ready,release):
    with locked(path):ready.set();release.wait(5)

def test_real_lock_ignores_environment_marker(tmp_path,monkeypatch):
    monkeypatch.setenv('LAB_LOCK_HELD','1')
    ready=multiprocessing.Event();release=multiprocessing.Event()
    child=multiprocessing.Process(target=_hold_lock,args=(tmp_path/'lock',ready,release))
    child.start()
    try:
        assert ready.wait(3)
        import fcntl
        fd=os.open(tmp_path/'lock',os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        finally:os.close(fd)
    finally:
        release.set();child.join(5)
        if child.is_alive():child.terminate();child.join()
    assert child.exitcode==0

def test_backup_missing_config_notifies_without_secrets(monkeypatch,ctl):
    import backup
    monkeypatch.setattr(backup,'Controller',lambda:ctl)
    run=Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(backup.subprocess,'run',run)
    assert backup.main()==1
    assert run.call_args.args[0][0]=='/usr/local/bin/lab-notify-root'

def test_restore_replaces_live_copy_with_snapshot_and_removes_wal(tmp_path):
    spec=importlib.util.spec_from_file_location('restore_stage',ROOT/'tools/restore-stage.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=tmp_path/'restic';app=tree/'srv/lab/demo';(app/'app').mkdir(parents=True);(app/'data').mkdir()
    (app/'app/main.py').write_text('# actual backed-up source')
    (app/'data/test.db').write_text('inconsistent raw copy')
    (app/'data/test.db-wal').write_text('stale WAL')
    generation=tree/'var/backups/lab/generation';generation.mkdir(parents=True)
    with sqlite3.connect(generation/'sqlite-dummy.db') as db:
        db.execute('create table restored (value text)');db.execute("insert into restored values ('yes')")
    write_json(generation/'manifest.json',{'version':3,'apps':[{'name':'demo','db':'sqlite','sqlite':[{'path':'test.db','snapshot':'sqlite-dummy.db'}]}]})
    records=tree/'var/lib/lab/records';records.mkdir(parents=True);write_json(records/'demo.json',rec(db='sqlite'))
    output=tmp_path/'staged'
    module.stage(tree,generation,'demo',output)
    assert (output/'app/main.py').read_text()=='# actual backed-up source'
    assert not (output/'data/test.db-wal').exists()
    with sqlite3.connect(output/'data/test.db') as db:
        assert db.execute('select value from restored').fetchone()==('yes',)
    with pytest.raises(LabError):module.stage(tree,generation,'demo',output)

def test_static_export_rejects_symlink_and_preserves_bytes(tmp_path):
    from export_public import export
    root=tmp_path/'assets';root.mkdir();(root/'index.html').write_text('safe')
    assert export(root)==[{'path':'index.html','data':'c2FmZQ=='}]
    (root/'link').symlink_to(tmp_path/'outside')
    with pytest.raises(OSError):export(root)

def test_static_snapshot_is_root_owned_and_caddy_serves_snapshot(ctl):
    ctl.run=Mock(return_value=SimpleNamespace(stdout='[{"path":"index.html","data":"c2FmZQ=="}]',returncode=0))
    r=rec(kind='static');r['public_revision']=ctl.snapshot_public(r)
    target=ctl.public/('demo-'+r['public_revision'])
    assert (target/'index.html').read_text()=='safe'
    assert (target/'index.html').stat().st_mode & 0o777==0o644
    assert str(target) in caddy_site(r,'example.test',ctl.root,ctl.public)
    assert '/app/public' not in caddy_site(r,'example.test',ctl.root,ctl.public)
    assert ctl.run.call_args.kwargs['user']=='lab'

def test_snapshot_cleanup_does_not_match_other_app(ctl):
    first=ctl.public/('aa-'+'a'*32);first.mkdir()
    second=ctl.public/('aa-other-'+'b'*32);second.mkdir()
    assert ctl.snapshots('aa')==[first]

def test_static_failed_republication_preserves_record_and_previous_snapshot(ctl):
    r=rec(kind='static');r['public_revision']='a'*32;r['resources']['caddy']=True;ctl.save(r)
    old=ctl.public/('demo-'+'a'*32);old.mkdir();(old/'index.html').write_text('previous')
    ctl.run=Mock(return_value=SimpleNamespace(stdout='[{"path":"index.html","data":"bmV3"}]',returncode=0))
    ctl.caddy_publish=Mock(side_effect=LabError('rejected'))
    with pytest.raises(LabError):ctl.publish('demo')
    assert ctl.record('demo')['public_revision']=='a'*32
    assert (old/'index.html').read_text()=='previous'
    assert ctl.snapshots('demo')==[old]

def test_prepare_only_never_starts_or_publishes(ctl,monkeypatch):
    accounts={'lab':SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())}
    def lookup(user):
        if user not in accounts:raise KeyError(user)
        return accounts[user]
    monkeypatch.setattr(pwd,'getpwnam',lookup)
    calls=[]
    def run(args,**kwargs):
        calls.append((args,kwargs))
        if args[0]=='useradd':accounts['labapp-demo']=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())
        return SimpleNamespace(stdout='',returncode=0)
    ctl.run=run
    args=controller.parser().parse_args(['create','demo','--app','--prepare-only'])
    ctl.create(args)
    assert ctl.record('demo')['status']=='prepared'
    assert all('start' not in args and 'enable' not in args and 'caddy' not in args for args,_ in calls)
    scaffold=next((args,kw) for args,kw in calls if any(str(a).endswith('scaffold.py') for a in args))
    assert scaffold[1]['user']=='lab'
    assert (ctl.root/'demo').stat().st_mode & 0o777 == 0o755
    assert (ctl.root/'demo/app').stat().st_mode & 0o777 == 0o755

def test_interrupted_creation_keeps_intent_for_recovery(ctl,monkeypatch):
    def absent(_):raise KeyError()
    monkeypatch.setattr(pwd,'getpwnam',absent)
    ctl.run=Mock(side_effect=LabError('user creation interrupted'))
    with pytest.raises(LabError):ctl.create(controller.parser().parse_args(['create','demo']))
    r=ctl.record('demo')
    assert r['status']=='create-failed' and r['resources']['identity_intent']

def test_postgres_preexisting_role_is_not_adopted_or_rotated(ctl):
    r=rec(db='postgres');ctl.save(r)
    ctl.sql=Mock(return_value=SimpleNamespace(stdout='1\n'))
    with pytest.raises(LabError,match='refuse to adopt'):ctl.db_create(r)
    assert ctl.sql.call_count==1
    assert not (ctl.state/'credentials/demo.json').exists()

def test_doctor_continues_after_corrupt_record(ctl,monkeypatch,capsys):
    ctl.path('bad').write_text('{broken')
    ctl.save(rec(kind='static'))
    ctl.sql=Mock(return_value=SimpleNamespace(stdout=''))
    monkeypatch.setattr(pwd,'getpwall',lambda:[])
    assert ctl.doctor()
    text=capsys.readouterr().out
    assert 'bad.json' in text and 'demo: prepared' in text

def test_restore_stages_static_and_postgres_artifacts(tmp_path):
    spec=importlib.util.spec_from_file_location('restore_stage_more',ROOT/'tools/restore-stage.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=tmp_path/'restic';generation=tree/'var/backups/lab/generation';generation.mkdir(parents=True)
    entries=[]
    for app,kind,db in [('static-demo','static','none'),('pg-demo','app','postgres')]:
        source=tree/'srv/lab'/app;(source/'app').mkdir(parents=True);(source/'data').mkdir()
        (source/'app/README.md').write_text('actual application '+app)
        records=tree/'var/lib/lab/records';records.mkdir(parents=True,exist_ok=True)
        write_json(records/f'{app}.json',rec(app,kind,db))
        item={'name':app,'db':db,'sqlite':[]}
        if db=='postgres':
            item['postgres']=f'pg-{app}.dump';(generation/item['postgres']).write_bytes(b'dummy opaque dump fixture')
        entries.append(item)
    write_json(generation/'manifest.json',{'version':3,'apps':entries})
    for item in entries:
        output=tmp_path/item['name'];module.stage(tree,generation,item['name'],output)
        assert 'actual application' in (output/'app/README.md').read_text()
        if item['db']=='postgres':assert (output/'postgres.dump').read_bytes()==b'dummy opaque dump fixture'

def test_interrupted_grant_keeps_desired_state(ctl,monkeypatch):
    ctl.save(rec())
    original=controller.atomic_write
    def interrupted(path,*args,**kwargs):
        if Path(path).suffix=='.env':raise OSError('simulated env publication failure')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(controller,'atomic_write',interrupted)
    with pytest.raises(OSError):ctl.grant('demo','FIRST')
    assert ctl.record('demo')['grants']==['FIRST']
    assert ctl.record('demo')['status']=='environment-pending'

def test_postgres_driver_loads_without_connecting():
    from sqlalchemy import create_engine
    engine=create_engine('postgresql+psycopg://dummy:dummy@127.0.0.1/dummy')
    assert engine.dialect.driver=='psycopg'
    engine.dispose()

def test_renderer_handles_quotes_and_placeholder_like_title(tmp_path,monkeypatch):
    import render
    destination=tmp_path/'main.py'
    destination.write_text('TITLE = "{{TITLE}}"\nNAME = "{{NAME}}"\n')
    title='R&D "Lab" {{NAME}} \\ demo'
    monkeypatch.setattr('sys.argv',['render.py',str(tmp_path),f'TITLE={title}','NAME=demo'])
    render.main()
    values={};exec(compile(destination.read_text(),str(destination),'exec'),values)
    assert values['TITLE']==title and values['NAME']=='demo'

def test_systemd_backup_failure_uses_one_notification_path(monkeypatch,ctl):
    import backup
    monkeypatch.setattr(backup,'Controller',lambda:ctl)
    monkeypatch.setenv('LAB_BACKUP_ONFAILURE','1')
    command=Mock();monkeypatch.setattr(backup.subprocess,'run',command)
    assert backup.main()==1
    command.assert_not_called()
    assert 'OnFailure=lab-backup-failure.service' in (ROOT/'bootstrap.sh').read_text()

def test_caddy_rollback_failure_is_explicit(ctl):
    results=iter([0,1,1])
    ctl.run=lambda *args,**kwargs:SimpleNamespace(returncode=next(results),stdout='')
    with pytest.raises(LabError,match='ALSO failed'):ctl.caddy_publish([rec()])
    assert (ctl.caddy/'lab-sites.caddy').read_text()=='previous site configuration\n'


def test_unpublished_app_cannot_be_marked_verified(ctl):
    ctl.save(rec(kind='static'));ctl.wait_http=Mock(return_value=True)
    with pytest.raises(LabError,match='not published'):ctl.verify('demo')
    ctl.wait_http.assert_not_called()

def test_internal_tls_restricted_to_test_domains():
    r=rec()
    assert 'tls internal' in caddy_site(r,'lab-integration.test','/srv/lab',tls_mode='internal')
    with pytest.raises(LabError):caddy_site(r,'randomjunk.dev','/srv/lab',tls_mode='internal')

def test_caddy_timeout_restores_previous_configuration(ctl):
    ctl.run=Mock(side_effect=[SimpleNamespace(returncode=0),subprocess.TimeoutExpired('caddy',600),SimpleNamespace(returncode=0)])
    with pytest.raises(LabError,match='restored and reloaded'):ctl.caddy_publish([rec()])
    assert (ctl.caddy/'lab-sites.caddy').read_text()=='previous site configuration\n'

def test_doctor_accepts_installed_agent_instruction_files(ctl,monkeypatch,capsys):
    (ctl.root/'AGENTS.md').write_text('operating instructions')
    (ctl.root/'CLAUDE.md').write_text('operating instructions')
    ctl.sql=Mock(return_value=SimpleNamespace(stdout=''))
    monkeypatch.setattr(pwd,'getpwall',lambda:[])
    (ctl.caddy/'lab-sites.caddy').write_text('')
    assert not ctl.doctor()
    assert 'orphan app entry' not in capsys.readouterr().out

@pytest.mark.parametrize('kind', ['static','app'])
def test_pwa_worker_failure_stops_publication_before_activation(ctl, kind):
    ctl.save(rec(kind=kind))
    before=ctl.path('demo').read_bytes()
    ctl.run=Mock(side_effect=LabError('PWA generation failed'))
    ctl.snapshot_public=Mock();ctl.environment=Mock();ctl.caddy_publish=Mock()
    with pytest.raises(LabError,match='PWA generation failed'):
        ctl.publish('demo')
    args,kwargs=ctl.run.call_args
    assert str(args[0][2]).endswith('/pwa_build.py')
    assert kwargs['user']=='lab'
    assert ctl.path('demo').read_bytes()==before
    ctl.snapshot_public.assert_not_called()
    ctl.environment.assert_not_called()
    ctl.caddy_publish.assert_not_called()


def test_alias_preserves_target_and_auth():
    r=rec();r.update(aliases=['newname'],private=True,auth_hash=HASH)
    text=caddy_site(r,'example.test','/srv/lab')
    assert text.startswith('demo.example.test, newname.example.test {')
    assert 'basic_auth' in text and 'reverse_proxy 127.0.0.1:8100' in text
    for aliases in [['evil.example'], ['demo'], ['bad\nname'], 'newname']:
        r['aliases']=aliases
        with pytest.raises(LabError):caddy_site(r,'example.test','/srv/lab')

def test_alias_persistence_collision_and_rollback(ctl):
    r=rec();r['resources']['caddy']=True;ctl.save(r)
    ctl.caddy_publish=Mock()
    ctl.alias('demo','newname')
    assert ctl.record('demo')['aliases']==['newname']
    assert ctl.published()[0]['aliases']==['newname']
    ctl.alias('demo','newname')
    assert ctl.caddy_publish.call_count==1
    ctl.save(rec('other'))
    with pytest.raises(LabError):ctl.alias('other','newname')
    with pytest.raises(LabError):ctl.alias('demo','other')
    ctl.caddy_publish=Mock(side_effect=LabError('reload failed'))
    with pytest.raises(LabError):ctl.alias('demo','third')
    assert ctl.record('demo')['aliases']==['newname']

def test_create_cannot_claim_alias(ctl):
    r=rec();r['aliases']=['newname'];ctl.save(r)
    args=controller.parser().parse_args(['create','newname','--static'])
    with pytest.raises(LabError,match='reserved by an alias'):ctl.create(args)
