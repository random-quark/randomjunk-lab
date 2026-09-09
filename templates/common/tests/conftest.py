"""Per-test isolated servers/databases and contexts; one browser per worker; run as lab."""
import importlib.util
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('labdev_fixture', ROOT / 'tools/labdev.py')
labdev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(labdev)

@pytest.fixture
def app_server():
    with labdev.server(ROOT) as info:
        yield info

@pytest.fixture
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
    def advance(*, max_steps=4000, dt=50, model_name="model"):
        if max_steps <= 0 or dt <= 0:
            raise ValueError("max_steps and dt must be positive")
        # Explicit function, not eval of a guessed model name. It returns true at rest.
        return page.evaluate('''([maxSteps, dt, modelName]) => {
            if (typeof window.labTestStep !== 'function')
                throw new Error('Install a labTestStep(dt) adapter returning true when idle');
            for (let n=0; n<maxSteps; n++) if (window.labTestStep(dt)) return n+1;
            throw new Error(`${modelName} did not reach idle within ${maxSteps} steps`);
        }''', [max_steps, dt, model_name])
    # Adapter installation uses Playwright's function API, not string eval in the app.
    def run(adapter, **kwargs):
        page.evaluate(adapter)
        return advance(**kwargs)
    return run
