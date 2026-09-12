"""Readiness checks under deployment identity; no keys or lifecycle mutations."""
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-dir', required=True)
    parser.add_argument('--engines', nargs='+', choices=['chromium', 'webkit', 'firefox'], default=['chromium'])
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('run as lab, never root')
    root = Path(args.app_dir).resolve()
    failures = []
    report = {'identity': pwd.getpwuid(os.geteuid()).pw_name, 'source': str(root),
              'data': str(root.parent/'data'), 'tools': {}, 'browsers': {},
              'device_limits': 'Linux engines only; physical Android/iPhone remain separate checks.'}
    if report['identity'] != 'lab':
        failures.append('expected deployment identity lab')
    for tool in ('uv', 'rg', 'git', 'labbuild', 'labdev', 'labshot'):
        report['tools'][tool] = shutil.which(tool)
        if not report['tools'][tool]:
            failures.append('missing tool: '+tool)
    try:
        with tempfile.TemporaryFile(dir=root):
            pass
    except OSError:
        failures.append('source directory is not writable')
    if shutil.which('git'):
        result = subprocess.run(['git', '-C', str(root), 'status', '--porcelain'], capture_output=True, timeout=15)
        if result.returncode:
            failures.append('Git inspection failed; check ownership as lab')
    try:
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix='lab-preflight-') as directory, sync_playwright() as playwright:
            for engine in args.engines:
                try:
                    browser = getattr(playwright, engine).launch(headless=True)
                    try:
                        for width, height in ((390, 844), (1280, 800)):
                            page = browser.new_page(viewport={'width': width, 'height': height})
                            page.set_content('<h1>Browser preflight</h1>')
                            path = Path(directory)/f'{engine}-{width}.png'
                            page.screenshot(path=str(path))
                            if not path.stat().st_size:
                                raise RuntimeError('empty screenshot')
                            page.close()
                        report['browsers'][engine] = {'version': browser.version, 'screenshots': 'phone and desktop passed'}
                    finally:
                        browser.close()
                except Exception as error:
                    report['browsers'][engine] = {'error': str(error)}
                    failures.append(engine+' failed: install its browser as lab; review OS prerequisites with an administrator')
    except ImportError:
        failures.append('Playwright unavailable: sync dev dependencies as lab')
    report['failures'] = failures
    print(json.dumps(report, indent=2))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
