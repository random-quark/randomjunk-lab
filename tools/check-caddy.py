#!/usr/bin/python3
"""Offline parser checks only. Does not start/reload Caddy or obtain certificates."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bin/lib'))
from labcore import caddy_site
binary = str(Path(sys.argv[1]).resolve())
hashed = subprocess.run([binary,'hash-password'],input='dummy-review-password\n',capture_output=True,text=True,check=True).stdout.strip()
with tempfile.TemporaryDirectory(prefix='lab-caddy-parse-') as temporary:
    for kind in ('static','app'):
        for private in (False,True):
            record={'name':'review-demo','kind':kind,'private':private,'port':8100,'auth_hash':hashed,'public_revision':'a'*32}
            config=Path(temporary)/'Caddyfile'
            config.write_text('{\n\tadmin off\n}\n'+caddy_site(record,'example.test','/srv/lab'))
            result=subprocess.run([binary,'adapt','--config',str(config),'--adapter','caddyfile'],capture_output=True,text=True,check=True)
            parsed=json.loads(result.stdout)
            assert parsed['apps']['http']['servers']
            print(f'PASS: Caddy parses {kind}, private={private}')
