"""Minimal offline-reload repro: one page, one cache-first service worker. Usage: repro.py ENGINE [RUNS]"""
import json, subprocess, sys, socket, time, importlib.metadata as md
from pathlib import Path
from playwright.sync_api import sync_playwright, Error

SITE = Path(__file__).parent / 'site'

def start_server():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    proc = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '-d', str(SITE)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try: socket.create_connection(('127.0.0.1', port), .1).close(); break
        except OSError: time.sleep(.1)
    return proc, f'http://127.0.0.1:{port}/'

def loaded(page):
    return page.locator('#shell').inner_text() == 'shell-ok' and page.locator('#js').inner_text() == 'js-ok'

def prime(ctx, url):
    page = ctx.new_page(); page.goto(url)
    page.evaluate('navigator.serviceWorker.ready.then(() => true)')
    page.reload(); page.wait_for_function('navigator.serviceWorker.controller !== null')
    return page

def variant(browser, name):
    proc, url = start_server()
    ctx = browser.new_context()
    try:
        page = prime(ctx, url)
        if name == 'emulated-offline/reload':
            ctx.set_offline(True); page.reload()
        elif name == 'emulated-offline/goto-same-page':
            ctx.set_offline(True); page.goto(url)
        elif name == 'emulated-offline/goto-new-page':
            ctx.set_offline(True); page = ctx.new_page(); page.goto(url)
        elif name == 'server-stopped/reload':
            proc.terminate(); proc.wait(5); page.reload()
        elif name == 'server-stopped/goto-new-page':
            proc.terminate(); proc.wait(5); page = ctx.new_page(); page.goto(url)
        return 'PASS' if loaded(page) else 'FAIL: shell not rendered'
    except Error as e:
        return 'ERROR: ' + str(e).splitlines()[0][:110]
    finally:
        ctx.close()
        if proc.poll() is None: proc.terminate(); proc.wait(5)

VARIANTS = ['emulated-offline/reload', 'emulated-offline/goto-same-page', 'emulated-offline/goto-new-page',
            'server-stopped/reload', 'server-stopped/goto-new-page']

if __name__ == '__main__':
    engine, runs = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3
    with sync_playwright() as p:
        b = getattr(p, engine).launch()
        print(f"playwright {md.version('playwright')} {engine} {b.version}")
        for v in VARIANTS:
            print(f'  {v:34s}', [variant(b, v) for _ in range(runs)])
        b.close()
