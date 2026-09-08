"""Capture a viewport screenshot and diagnostic report without writing app data."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

def capture(url, output, viewport='390x844'):
    from playwright.sync_api import sync_playwright
    match = re.fullmatch(r'(\d{2,4})x(\d{2,4})', viewport)
    if not match or not all(100 <= int(v) <= 4096 for v in match.groups()):
        raise ValueError('viewport must be WIDTHxHEIGHT, each 100–4096')
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('URL must use HTTP(S)')
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    report = {'url': url, 'viewport': viewport, 'console_errors': [], 'page_errors': [],
              'failed_requests': [], 'http_errors': [], 'navigation_error': None}
    # Avoid recording query strings or request bodies in diagnostics.
    def safe_url(value):
        parts = urlsplit(value)
        return f'{parts.scheme}://{parts.hostname}{parts.path}'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width': int(match[1]), 'height': int(match[2])})
            page.on('console', lambda msg: report['console_errors'].append(msg.text) if msg.type == 'error' else None)
            page.on('pageerror', lambda exc: report['page_errors'].append(str(exc)))
            page.on('requestfailed', lambda req: report['failed_requests'].append({'url': safe_url(req.url), 'error': req.failure}))
            page.on('response', lambda res: report['http_errors'].append({'url': safe_url(res.url), 'status': res.status}) if res.status >= 400 else None)
            try:
                page.goto(url, wait_until='load', timeout=15000)
                page.evaluate('document.fonts.ready')
                page.screenshot(path=str(directory / 'screenshot.png'), full_page=True)
            except Exception as exc:
                report['navigation_error'] = str(exc)
        finally:
            browser.close()
    (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return not any(report[key] for key in ('console_errors','page_errors','failed_requests','http_errors','navigation_error'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('--out', default='artifacts/labshot')
    parser.add_argument('--viewport', default='390x844')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('run browser checks as lab')
    try:
        okay = capture(args.url, args.out, args.viewport)
    except ImportError:
        parser.error('run uv sync --locked and .venv/bin/playwright install chromium as lab first')
    print(f'Screenshot and diagnostics: {args.out}; inspect for private content before sharing')
    return 0 if okay else 1

if __name__ == '__main__':
    sys.exit(main())
