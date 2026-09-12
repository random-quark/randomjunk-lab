#!/usr/bin/python3 -I
"""Fixed unprivileged worker. Never run app code or uv as root."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent))
import render
from pwa_build import build

def main():
    if os.geteuid() == 0:
        raise SystemExit('scaffold must run as the deployment user')
    os.umask(0o022)
    source, target, app, title, url, domain, db = sys.argv[1:]
    root = Path(target)
    shutil.copytree(source, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(Path(source).parent/'common', root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.venv'))
    (root/'lab.json').write_text(json.dumps({'name': app, 'url': url, 'kind': Path(source).name, 'db': db}, indent=2) + '\n')
    sys.argv = ['render.py', target, f'NAME={app}', f'TITLE={title}', f'URL={url}', f'DOMAIN={domain}']
    render.main()
    for size in (180, 192, 512):
        subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), str(root/'public/icon.svg'), '-o', str(root/f'public/icon-{size}.png')], check=True)
    shutil.copyfile(root/'public/icon-512.png', root/'public/icon-maskable-512.png')
    build(root/'public')
    if (root/'pyproject.toml').exists():
        env = dict(os.environ, UV_PYTHON_DOWNLOADS='never', UV_CACHE_DIR='/tmp/lab-uv-cache-' + str(os.getuid()), HOME='/home/lab')
        # Prefer the shipped lockfile. Optional postgres dependency is explicit.
        command = ['uv', 'sync', '--locked', '--python', '/usr/bin/python3']
        if db == 'postgres':
            command += ['--extra', 'postgres']
        subprocess.run(command, cwd=root, env=env, check=True)
    (root/'.gitignore').write_text('.venv/\n.env\n__pycache__/\n*.pyc\n.pytest_cache/\nartifacts/\n')
    (root/'install.md').write_text(f'# {app}\n\nCode: {target}\n\nRuntime data: /srv/lab/{app}/data\n\nURL: {url}\n\nAuthoritative state is root-owned /var/lib/lab/records/{app}.json.\nUse labctl verify {app} to check HTTP; test application behavior separately.\n\n## Current state\n\nUpdate this section in place: behavior, reproduction commands, release, test evidence and remaining device checks.\n\n## Resources and recovery\n\nRecord external resources and recovery steps. Keep secrets out.\n\n## Owner notes\n\nPreserve owner-authored notes. Store release history in CHANGELOG.md; dated test reports/screenshots in artifacts/YYYY-MM-DD/. Link the latest evidence here.\n')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=lab', '-c', 'user.email=lab@localhost', 'commit', '-qm', 'Initial scaffold'], check=True)

if __name__ == '__main__':
    main()
