"""Per-worker isolated servers and per-test browser contexts; run as lab."""
import importlib.util
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('labdev_fixture', ROOT / 'tools/labdev.py')
labdev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(labdev)

@pytest.fixture(scope='session')
def app_server():
    with labdev.server(ROOT) as info:
        yield info

@pytest.fixture(scope='session')
def base_url(app_server):
    return app_server['url']

@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(base_url=base_url, viewport={'width':390,'height':844})
    page = context.new_page()
    yield page
    context.close()

@pytest.fixture
def fast_forward(page):
    def advance(adapter, *, max_steps=4000, dt=50):
        # Explicit function, not eval of a guessed model name. It returns true at rest.
        return page.evaluate('''([maxSteps, dt]) => {
            if (typeof window.labTestStep !== 'function')
                throw new Error('Install a labTestStep(dt) adapter returning true when idle');
            for (let n=0; n<maxSteps; n++) if (window.labTestStep(dt)) return n+1;
            throw new Error('Model did not reach idle within max_steps');
        }''', [max_steps, dt])
    # Adapter installation uses Playwright's function API, not string eval in the app.
    def run(adapter, **kwargs):
        page.evaluate(adapter)
        return advance(adapter, **kwargs)
    return run
