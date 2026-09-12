#!/usr/bin/python3
"""Live, unprivileged scaffold checks in temporary directories; no labctl or ACME.

Run as lab with --source pointing at a readable staged copy of templates/bin/lib.
Downloads locked dev dependencies via uv; needs Playwright Chromium installed as lab.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

TESTS = r'''
import importlib.util
import json
from pathlib import Path
import pytest
from playwright.sync_api import Error
from conftest import ROOT, labdev

def test_native_offer_and_offline(page, base_url):
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('/')
    page.wait_for_function('navigator.serviceWorker.controller !== null')
    page.evaluate("""() => {
        const e=new Event('beforeinstallprompt');
        e.prompt=async()=>{ window.promptCalled=true; };
        e.userChoice=Promise.resolve({outcome:'dismissed'});
        dispatchEvent(e);
    }""")
    assert page.locator('#lab-install-panel').is_hidden()
    page.locator('#lab-install-open').click()
    page.locator('#lab-install-native').click()
    assert page.evaluate('window.promptCalled')
    page.context.set_offline(True)
    page.reload()
    assert page.locator('#lab-install-open').is_visible()
    # Chromium network emulation does not always change navigator.onLine for SW navigations.
    assert page.evaluate('navigator.serviceWorker.controller !== null')
    page.evaluate("Object.defineProperty(navigator,'onLine',{value:false,configurable:true}); dispatchEvent(new Event('offline'));")
    assert 'Offline' in page.locator('#lab-offline-status').inner_text()
    assert not errors

def test_install_event_does_not_interrupt_form(page):
    page.goto('/')
    page.evaluate("""() => {
      const input=document.createElement('input'); input.id='test-name';
      document.body.append(input); input.focus();
      const event=new Event('beforeinstallprompt');
      event.prompt=async()=>{}; event.userChoice=Promise.resolve({outcome:'dismissed'});
      dispatchEvent(event);
    }""")
    page.locator('#test-name').fill('MY SCORE')
    assert page.locator('#lab-install-panel').is_hidden()
    assert page.locator('#test-name').input_value()=='MY SCORE'
    assert page.evaluate('document.activeElement.id')=='test-name'

@pytest.mark.parametrize('round_number',[1,2])
def test_database_starts_clean_for_each_test(base_url,round_number):
    if not (ROOT/'main.py').exists():
        pytest.skip('static fixture has no database')
    import urllib.request
    with urllib.request.urlopen(base_url+'/api/dev-check') as response:
        assert json.load(response)['rows']==1

def test_worker_revision_waits_for_old_tabs(page, base_url):
    import os, subprocess
    page.goto('/')
    page.wait_for_function('navigator.serviceWorker.controller !== null')
    old_worker=(ROOT/'public/sw.js').read_text()
    original=(ROOT/'public/index.html').read_text()
    try:
        (ROOT/'public/index.html').write_text(original+'<!-- revision-probe -->')
        subprocess.run(['/usr/bin/python3','-I',os.environ['LAB_TEST_PWA_BUILDER'],str(ROOT/'public')],check=True)
        assert (ROOT/'public/sw.js').read_text()!=old_worker
        page.evaluate('async () => { const r=await navigator.serviceWorker.getRegistration(); await r.update(); }')
        page.wait_for_function('async () => !!(await navigator.serviceWorker.getRegistration()).waiting')
        # The old controller must keep serving the old coherent shell.
        page.reload()
        assert 'revision-probe' not in page.content()
    finally:
        (ROOT/'public/index.html').write_text(original)
        subprocess.run(['/usr/bin/python3','-I',os.environ['LAB_TEST_PWA_BUILDER'],str(ROOT/'public')],check=True)

def test_ios_and_standalone(browser, base_url):
    context=browser.new_context(user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1')
    page=context.new_page();page.goto(base_url)
    assert 'Safari' in page.locator('#lab-install-help').inner_text()
    context.close()
    context=browser.new_context()
    context.add_init_script("Object.defineProperty(navigator,'standalone',{value:true})")
    page=context.new_page();page.goto(base_url)
    assert page.locator('#lab-install-open').is_hidden()
    assert page.locator('#lab-install-panel').is_hidden()
    context.close()

def test_fast_forward_and_bound(page, fast_forward):
    page.goto('/')
    count=fast_forward(''' + '"""' + r'''() => {window.position=0;window.labTestStep=dt=>{window.position+=dt;return window.position>=6000;};}''' + '"""' + r''')
    assert count==120
    assert page.evaluate('window.position')==6000
    with pytest.raises(Error,match='wheel did not reach idle within 3 steps'):
        fast_forward('() => {window.labTestStep=dt=>false}',max_steps=3,model_name='wheel')

def test_server_isolation_and_cleanup(app_server):
    import urllib.request
    with labdev.server(ROOT) as second:
        assert second['url']!=app_server['url']
        assert second['database']!=app_server['database']
        if (ROOT/'main.py').exists():
            with urllib.request.urlopen(second['url']+'/api/dev-check') as r:
                result=json.load(r)
            assert result=={'rows':1,'has_provider_key':False}
            assert Path(second['database']).is_file()
        pid=second['pid'];db=second['database']
    assert not Path(db).parent.exists()
    with pytest.raises(ProcessLookupError):
        import os
        os.kill(pid,0)

def test_shot_and_errors(base_url,tmp_path):
    import subprocess, sys
    okay=subprocess.run([sys.executable,str(ROOT/'tools/labshot.py'),base_url,'--out',str(tmp_path/'good')])
    assert okay.returncode==0
    assert (tmp_path/'good/screenshot.png').is_file()
    bad=subprocess.run([sys.executable,str(ROOT/'tools/labshot.py'),base_url+'/missing-file.js','--out',str(tmp_path/'bad')])
    assert bad.returncode==1
    assert json.loads((tmp_path/'bad/report.json').read_text())['http_errors']
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    if os.geteuid()==0:
        parser.error('run as lab')
    source=args.source.resolve()
    with tempfile.TemporaryDirectory(prefix='lab-tool-check-') as directory:
        for kind in ('static','app'):
            target=Path(directory)/kind
            subprocess.run(['/usr/bin/python3','-I',str(source/'bin/lib/scaffold.py'),
                            str(source/'templates'/kind),str(target),'fixture-'+kind,
                            'Fixture '+kind,'http://localhost','example.test','sqlite' if kind=='app' else 'none'],check=True)
            # Preflight uses only synthetic pages, never the app or its credentials.
            check=subprocess.run([str(target/'.venv/bin/python'),str(target/'tools/preflight.py'),'--app-dir',str(target)],capture_output=True,text=True)
            report=json.loads(check.stdout)
            assert report['browsers']['chromium']['screenshots']=='phone and desktop passed', report
            assert all(item.startswith('missing tool:') for item in report['failures']), report
            if kind=='app':
                p=target/'main.py';s=p.read_text();s=s.replace("@app.get('/api/health')",'''@app.get('/api/dev-check')
def dev_check():
    import sqlite3
    with sqlite3.connect(os.environ['DATABASE_URL'].removeprefix('sqlite:///')) as db:
        db.execute('CREATE TABLE IF NOT EXISTS sample (value INTEGER)')
        db.execute('INSERT INTO sample VALUES (1)')
        return {'rows':db.execute('SELECT count(*) FROM sample').fetchone()[0],
                'has_provider_key':bool(os.getenv('OPENAI_API_KEY'))}

@app.get('/api/health')''');p.write_text(s)
            (target/'tests/test_runtime.py').write_text(TESTS)
            env=dict(os.environ,OPENAI_API_KEY='dummy-must-not-be-inherited',LAB_TEST_PWA_BUILDER=str(source/'bin/lib/pwa_build.py'))
            subprocess.run([str(target/'.venv/bin/python'),'-m','pytest','-q','--durations=5'],cwd=target,env=env,check=True)
    print('PASS: both scaffold kinds, browser install/offline/actions, isolated servers and deterministic timing')

if __name__=='__main__':
    main()
