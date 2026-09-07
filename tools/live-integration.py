#!/usr/bin/python3 -I
"""AUTHORIZED INSTALLATION ONLY: exercise real lab services with dummy apps.

Requires a freshly installed, otherwise empty platform. Uses .test/internal TLS,
never production ACME. Restores config/hosts and removes its app resources.
"""
import base64
import concurrent.futures
import tempfile
import sqlite3
import json
import os
from pathlib import Path
import pwd
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0,'/usr/local/lib/lab')
from labcore import atomic_write, read_env, write_json

APPS=['check-static','check-private','check-none','check-sqlite','check-pg','check-parallel-a','check-parallel-b','check-restore']
DOMAIN='lab-integration.test'
LOG=Path('/root/workspaces/labserver-review/installation-logs/live-integration.log')

def note(message):
    print(message,flush=True)
    with LOG.open('a') as f:f.write(message+'\n')

def command(args,*,user=None,data=None,check=True):
    args=[str(a) for a in args]
    if user:args=['runuser','-u',user,'--',*args]
    result=subprocess.run(args,input=data,text=True,capture_output=True,timeout=600,cwd='/tmp')
    if check and result.returncode:
        # Operation output is restricted to platform status; don't print arbitrary
        # app/SQL stderr because later customizations could contain values.
        raise RuntimeError(f'{Path(args[0]).name} operation failed: exit {result.returncode}; inspect named step')
    return result

def lab(*args):
    return command(['sudo','-n','/usr/local/sbin/labctl',*args],user='lab')

def get(app,path='/',private=False):
    headers={}
    if private:
        password=(Path('/var/lib/lab/credentials')/(app+'.basic')).read_text()
        headers['Authorization']='Basic '+base64.b64encode(('lab:'+password).encode()).decode()
    context=ssl.create_default_context(cafile='/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context))
    try:
        with opener.open(urllib.request.Request(f'https://{app}.{DOMAIN}{path}',headers=headers),timeout=10) as response:
            return response.status,response.read().decode()
    except urllib.error.HTTPError as error:return error.code,''

def can(user,flag,path):
    return command(['test',flag,path],user=user,check=False).returncode==0

def inject_db_probe(app):
    snippet='''\n@app.get('/api/check-db')
def check_db():
    from sqlalchemy import create_engine, text
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE IF NOT EXISTS integration_values (value TEXT)'))
        connection.execute(text('DELETE FROM integration_values'))
        connection.execute(text("INSERT INTO integration_values VALUES ('dummy')"))
        ok=connection.execute(text('SELECT value FROM integration_values')).scalar()=='dummy'
        vector_ok=True
        if engine.dialect.name=='postgresql':
            vector_ok=connection.execute(text("SELECT '[1,2,3]'::vector <-> '[1,2,3]'::vector")).scalar()==0
            connection.execute(text('CREATE TABLE IF NOT EXISTS integration_vectors (value vector(3))'))
            connection.execute(text('DELETE FROM integration_vectors'))
            connection.execute(text("INSERT INTO integration_vectors VALUES ('[1,2,3]')"))
    engine.dispose()
    return {'database':ok,'vector':vector_ok,'first':os.getenv('LAB_TEST_FIRST')=='dummy-first','second':os.getenv('LAB_TEST_SECOND')=='dummy-second'}
\n'''
    script="from pathlib import Path\np=Path("+repr('/srv/lab/'+app+'/app/main.py')+")\ns=p.read_text()\np.write_text(s.replace(\"@app.get('/{full_path:path}', include_in_schema=False)\", "+repr(snippet)+"+\"@app.get('/{full_path:path}', include_in_schema=False)\"))\n"
    command(['/usr/bin/python3','-I','-'],user='lab',data=script)


def main():
    if os.geteuid()!=0:raise SystemExit('root required for authorized integration')
    if list(Path('/var/lib/lab/records').glob('*.json')):raise SystemExit('requires an empty installed platform')
    LOG.parent.mkdir(parents=True,exist_ok=True)
    if LOG.exists():
        LOG.with_name('live-integration-'+str(time.time_ns())+'.log').write_bytes(LOG.read_bytes())
    LOG.write_text('Live integration started with dummy resources only.\n')
    config=Path('/etc/lab/platform.json');original_config=config.read_bytes()
    hosts=Path('/etc/hosts');original_hosts=hosts.read_bytes()
    master=Path('/etc/lab/secrets.env');original_master=master.read_bytes()
    write_json(config,{'version':3,'domain':DOMAIN,'tls_mode':'internal'})
    hosts.write_bytes(original_hosts+b'\n127.0.0.1 '+(' '.join(a+'.'+DOMAIN for a in APPS)).encode()+b'\n')
    atomic_write(master,original_master+b'LAB_TEST_FIRST=dummy-first\nLAB_TEST_SECOND=dummy-second\n')
    error=None
    try:
        for app,options in [('check-static',['--static']),('check-private',['--static','--private']),('check-none',['--app']),('check-sqlite',['--app','--db','sqlite']),('check-pg',['--app','--db','postgres','--private'])]:
            note('Creating '+app)
            result=lab('create',app,*options)
            note('PASS creation and authenticated HTTP verification: '+app)
            private='--private' in options
            status,_=get(app,private=private)
            assert status==200
            if private:assert get(app)[0]==401
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda app:lab('create',app,'--app'), ['check-parallel-a','check-parallel-b']))
        ports=[json.loads(Path('/var/lib/lab/records',app+'.json').read_text())['port'] for app in ('check-parallel-a','check-parallel-b')]
        assert len(set(ports))==2
        note('PASS concurrent real creates serialize and allocate distinct working ports')
        note('PASS five-app matrix: static/public/private, backend/no-db/SQLite/Postgres')
        for app in ('check-none','check-sqlite','check-pg'):
            user='labapp-'+app
            effective=command(['systemctl','show','lab-app@'+app+'.service','-p','User','--value']).stdout.strip()
            assert effective==user and pwd.getpwnam(user).pw_uid!=0
            assert can(user,'-r','/srv/lab/'+app+'/app/main.py')
            assert can(user,'-w','/srv/lab/'+app+'/data')
            assert not can(user,'-w','/srv/lab/'+app+'/app/main.py')
            assert not can(user,'-r','/etc/lab/apps/'+app+'.env')
            assert not can(user,'-r','/etc/lab/secrets.env')
            assert not can(user,'-w','/run/caddy/admin.sock')
        assert not can('labapp-check-none','-r','/srv/lab/check-pg/data')
        assert not can('lab','-r','/etc/lab/secrets.env')
        assert not can('lab','-w','/run/caddy/admin.sock')
        record=json.loads(Path('/var/lib/lab/records/check-static.json').read_text())
        assert can('caddy','-r','/var/lib/lab-public/check-static-'+record['public_revision']+'/index.html')
        note('PASS real deployment/Caddy/runtime permission matrix')
        for app in ('check-sqlite','check-pg'):
            lab('secrets-grant','LAB_TEST_FIRST',app)
            lab('secrets-grant','LAB_TEST_SECOND',app)
            inject_db_probe(app)
            lab('service','restart',app)
            lab('verify',app)
            status,body=get(app,'/api/check-db',private=(app=='check-pg'))
            assert status==200 and all(json.loads(body).values())
        note('PASS real SQLite/Postgres writes, pgvector operation, successive grants and preserved DATABASE_URL')
        # Real stop-command failure must block all dependent deletion.
        override=Path('/etc/systemd/system/lab-app@check-none.service.d/stop-test.conf')
        override.write_text('[Unit]\nRefuseManualStop=yes\n')
        command(['systemctl','daemon-reload'])
        failed=command(['sudo','-n','/usr/local/sbin/labctl','remove','check-none'],user='lab',check=False)
        assert failed.returncode!=0 and Path('/srv/lab/check-none/app/main.py').exists()
        assert Path('/var/lib/lab/records/check-none.json').exists()
        override.unlink();command(['systemctl','daemon-reload'])
        lab('service','start','check-none');lab('verify','check-none')
        note('PASS real failed service stop preserves app directory and record')
        # Force a real Caddy client failure to an absent socket, then allow
        # the controller to restore and reload through the actual admin socket.
        from controller import Controller
        from labcore import LabError, locked
        ctl=Controller();original_run=ctl.run;reloads=0
        before=Path('/etc/caddy/lab-sites.caddy').read_bytes()
        def fail_first_reload(args,**kwargs):
            nonlocal reloads
            if args[:2]==['caddy','reload']:
                reloads+=1
                if reloads==1:
                    args=list(args);args[-1]='unix//run/caddy/nonexistent-integration.sock'
            return original_run(args,**kwargs)
        ctl.run=fail_first_reload
        with locked(Path('/var/lib/lab/lock')):
            try:ctl.caddy_publish(ctl.published(exclude='check-static'))
            except LabError:pass
            else:raise AssertionError('reload failure did not fail publication')
        assert reloads==2 and Path('/etc/caddy/lab-sites.caddy').read_bytes()==before and get('check-static')[0]==200
        note('PASS real Caddy failed reload restores prior file and serving site')
        # Republish must refuse a deployment-owned symlink and keep the old site.
        command(['ln','-s','/srv/lab/check-none/data/dummy','/srv/lab/check-static/app/public/unsafe'],user='lab')
        failed=command(['sudo','-n','/usr/local/sbin/labctl','publish','check-static'],user='lab',check=False)
        assert failed.returncode!=0 and get('check-static')[0]==200
        command(['rm','/srv/lab/check-static/app/public/unsafe'],user='lab')
        note('PASS live static symlink refusal leaves prior site served')
        # Real custom-format Postgres restore into separately provisioned DB.
        lab('create','check-restore','--app','--db','postgres','--prepare-only')
        with tempfile.TemporaryDirectory(prefix='lab-pg-restore-') as tmp:
            os.chmod(tmp,0o755)
            dump=subprocess.run(['runuser','-u','postgres','--','pg_dump','-Fc','--no-owner','--no-acl','lab_check_pg'],capture_output=True,check=True).stdout
            listing=subprocess.run(['pg_restore','--list'],input=dump,capture_output=True,check=True).stdout.decode()
            toc=Path(tmp)/'restore.list'
            toc.write_text('\n'.join(line for line in listing.splitlines() if ' EXTENSION - vector' not in line and ' COMMENT - EXTENSION vector' not in line)+'\n')
            toc.chmod(0o644)
            restored=subprocess.run(['runuser','-u','postgres','--','pg_restore','--exit-on-error','--no-owner','--no-acl','--role=lab_check_restore','--dbname=lab_check_restore','--use-list='+str(toc)],input=dump,capture_output=True)
            if restored.returncode:
                note('Postgres restore returned failure; diagnostic class: '+str(restored.returncode))
                raise RuntimeError('Postgres restore failed')
            query=command(['psql','-X','-tAc',"SELECT value FROM integration_values; SELECT value::text FROM integration_vectors;",'lab_check_restore'],user='postgres').stdout.splitlines()
            assert query==['dummy','[1,2,3]']
        note('PASS real PostgreSQL restore, including stored vector data, into an isolated DB')
        # Snapshot unusual SQLite names under the REAL runtime uid, then test
        # encrypted local restic backup/restore and the repository staging tool.
        filename="odd'?#.sqlite"
        script="import sqlite3\nwith sqlite3.connect("+repr('/srv/lab/check-sqlite/data/'+filename)+") as db:\n db.execute('CREATE TABLE restored (value TEXT)')\n db.execute(\"INSERT INTO restored VALUES ('dummy-restored')\")\n"
        command(['/usr/bin/python3','-I','-'],user='labapp-check-sqlite',data=script)
        snap=subprocess.run(['runuser','-u','labapp-check-sqlite','--','/usr/bin/python3','-I','/usr/local/lib/lab/sqlite_worker.py','snapshot','/srv/lab/check-sqlite/data',filename],capture_output=True,check=True).stdout
        with tempfile.TemporaryDirectory(prefix='lab-restic-restore-') as tmp:
            base=Path(tmp);tree=base/'tree';generation=tree/'var/backups/lab/generation';generation.mkdir(parents=True)
            (generation/'sqlite-dummy.db').write_bytes(snap)
            with sqlite3.connect(generation/'sqlite-dummy.db') as db:assert db.execute('pragma integrity_check').fetchone()==('ok',)
            write_json(generation/'manifest.json',{'version':3,'apps':[{'name':'check-sqlite','db':'sqlite','sqlite':[{'path':filename,'snapshot':'sqlite-dummy.db'}]}]})
            appdir=tree/'srv/lab/check-sqlite';(appdir/'app').mkdir(parents=True);(appdir/'data').mkdir()
            source=command(['/usr/bin/python3','-I','-c',"from pathlib import Path; print(Path('/srv/lab/check-sqlite/app/main.py').read_text())"],user='lab').stdout
            (appdir/'app/main.py').write_text(source)
            (appdir/'data'/filename).write_bytes(b'raw-copy-replaced-by-snapshot')
            (appdir/'data'/(filename+'-wal')).write_bytes(b'stale-wal')
            records=tree/'var/lib/lab/records';records.mkdir(parents=True)
            (records/'check-sqlite.json').write_bytes(Path('/var/lib/lab/records/check-sqlite.json').read_bytes())
            import secrets
            env=dict(os.environ,RESTIC_REPOSITORY=str(base/'repository'),RESTIC_PASSWORD=secrets.token_hex(24))
            for args in (['restic','init'],['restic','backup',str(tree)],['restic','check'],['restic','restore','latest','--target',str(base/'restored')]):
                subprocess.run(args,env=env,capture_output=True,check=True,timeout=120)
            restored_tree=base/'restored'/str(tree).lstrip('/')
            subprocess.run(['/usr/bin/python3','-I',str(Path(__file__).parent/'restore-stage.py'),str(restored_tree),str(restored_tree/'var/backups/lab/generation'),'check-sqlite',str(base/'staged')],capture_output=True,check=True)
            with sqlite3.connect(base/'staged/data'/filename) as db:assert db.execute('SELECT value FROM restored').fetchone()==('dummy-restored',)
            assert not (base/'staged/data'/(filename+'-wal')).exists()
        note('PASS runtime-uid unusual SQLite snapshot, real encrypted local restic restore, staging and stale-WAL removal')
        result=command(['systemctl','start','lab-app@check-unprovisioned.service'],check=False)
        state=command(['systemctl','show','lab-app@check-unprovisioned.service','-p','ActiveState','--value']).stdout.strip()
        assert state in ('inactive','failed')
        effective=command(['systemctl','show','lab-app@check-unprovisioned.service','-p','User','--value']).stdout.strip()
        assert effective=='labapp-check-unprovisioned'
        note('PASS real unprovisioned unit does not run and has no root fallback')
        lab('remove','check-restore')
        assert lab('doctor').returncode==0
        note('PASS real reconciliation with healthy fixtures')
    except Exception as exc:
        error=exc
        note('FAIL: '+type(exc).__name__+': '+str(exc))
    finally:
        failures=[]
        for app in reversed(APPS):
            if Path('/var/lib/lab/records',app+'.json').exists():
                try:
                    lab('remove',app)
                    lab('remove',app)
                    note('PASS remove and repeat: '+app)
                except Exception:failures.append(app)
        hosts.write_bytes(original_hosts)
        atomic_write(master,original_master)
        if not failures:
            atomic_write(config,original_config)
            command(['systemctl','reset-failed','lab-app@check-unprovisioned.service'],check=False)
            note('Restored production domain/config/hosts and original provider key set.')
        else:
            note('Cleanup needs attention for: '+', '.join(failures))
            error=RuntimeError('cleanup incomplete; internal test mode retained')
    if error:raise SystemExit(1)
    assert not list(Path('/var/lib/lab/records').glob('*.json'))
    note('PASS: integration complete; no disposable app records remain.')

if __name__=='__main__':main()
