#!/usr/bin/python3
"""Optional browser QA with fake credentials and mocked notification transport."""
import argparse
import importlib.util
from pathlib import Path
import tempfile
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wizard', ROOT / 'tools/setup-wizard.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lab-wizard-browser-') as directory:
        wizard = w.Wizard(directory, sender=lambda topic: None)
        assets = {url: (mime, (ROOT / 'tools/setup-ui' / name).read_bytes()) for url, mime, name in [
            ('/', 'text/html', 'index.html'), ('/app.js', 'text/javascript', 'app.js'), ('/style.css', 'text/css', 'style.css')]}
        server = w.make_server(wizard, assets, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': 1440, 'height': 1100})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.locator('#setup-code').fill(wizard.token)
                page.locator('#unlock-button').click()
                expect(page.locator('#workspace')).to_be_visible()
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / 'setup-preview.png'))
                    page.screenshot(path=str(args.screenshots / 'setup-desktop.png'), full_page=True)
                page.locator('#replicate-key').fill('fixture-replicate-key')
                page.locator('[data-choice="SERVER_IPV4"]').fill('8.8.8.8')
                page.locator('#notifications').select_option('ntfy')
                page.locator('#backups').select_option('skip')
                page.locator('#save-button').click()
                expect(page.locator('[data-status="REPLICATE_API_TOKEN"]')).to_have_text('Saved · untested')
                expect(page.locator('#replicate-key')).to_have_value('')
                page.locator('#topic-button').click()
                expect(page.locator('#subscription')).to_be_visible()
                page.locator('#test-ntfy').click()
                expect(page.locator('#confirm-ntfy')).to_be_enabled()
                page.locator('#confirm-ntfy').click()
                expect(page.locator('#ntfy-status')).to_have_text('Phone delivery confirmed')
                # Refresh requires the code again; saved keys must remain unreadable.
                page.reload()
                page.locator('#setup-code').fill(wizard.token)
                page.locator('#unlock-button').click()
                expect(page.locator('[data-status="REPLICATE_API_TOKEN"]')).to_have_text('Saved · untested')
                expect(page.locator('#replicate-key')).to_have_value('')
                assert 'fixture-replicate-key' not in page.content()
                assert page.evaluate('localStorage.length') == 0
                assert page.evaluate('sessionStorage.length') == 0
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / 'setup-mobile.png'), full_page=True)
                page.locator('#finish-button').click()
                expect(page.locator('#done')).to_be_visible()
                assert wizard.data['finished']
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()
    print('PASS: desktop/mobile onboarding, secret save/resume, mocked phone confirmation and session closure')


if __name__ == '__main__':
    main()
