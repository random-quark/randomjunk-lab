# WebKit offline failure: findings and platform changes

Date: 2026-11-07 · Investigated as `lab` · Repro: `wk-offline/` (site/, repro.py, results-*.txt)

## Finding

The "Page.reload: WebKit encountered an internal error" failure recorded in browser-testing.md (2026-11-06) is caused by
**Playwright 1.62.0's WebKit 26.5 under emulated offline** (`context.set_offline(True)`). It is not caused by app code,
and reload is not the specific trigger.

Minimal repro: one page, one cache-first service worker, loopback server. 3 runs per cell:

| Variant | 1.62.0 Chromium 151 | 1.62.0 WebKit 26.5 | 1.64.1 Chromium 156 | 1.64.1 WebKit 27.2 |
|---|---|---|---|---|
| emulated offline + reload | 3/3 pass | **3/3 internal error** | 3/3 | 3/3 |
| emulated offline + goto (same page) | 3/3 | **3/3 internal error** | 3/3 | 3/3 |
| emulated offline + goto (new page) | 3/3 | **3/3 internal error** | 3/3 | 3/3 |
| real loss (server stopped) + reload | 3/3 | 3/3 | 3/3 | 3/3 |
| real loss (server stopped) + goto | 3/3 | 3/3 | 3/3 | 3/3 |

On 1.64.1, glyphfall's full suite passes, and its WebKit offline test passes for real (XPASS):
49 passed, 1 xpassed. This ran in a scratch clone; the app's lock file is unchanged.
No matching upstream report was found. The newer build fixes it, so there is nothing to file.

## Changes for the platform repository (administrator)

1. **Re-lock templates to Playwright 1.64.1.** The range `playwright>=1.50,<2` in templates/{static,app}/pyproject.toml is
   fine. Regenerate the template uv.lock files so new scaffolds get 1.64.1 instead of 1.62.0.
2. **OS packages.** WebKit 27.2 and Chromium 156 launched and passed on this host's current packages.
   `install-deps --dry-run` exited 0. Still record the reviewed package versions in docs/webkit-packages.txt.
3. **browser-testing.md:** replace the "unresolved" WebKit paragraph with:
   > Fixed by Playwright ≥ 1.64.1 (WebKit 27.2). Older locks fail every navigation under `set_offline(True)` in WebKit.
   > Real network loss still worked there. Do not mark WebKit offline tests xfail on ≥ 1.64.1. Real iPhone checks remain separate.
4. **Shared browser cache warning.** Installing 1.64.1 browsers deleted the cached 1.62.0 builds (chromium-1234,
   webkit-2336). Playwright garbage-collects builds that no registered install still references. Add to browser-testing.md:
   > After installing a different Playwright version, run `.venv/bin/playwright install chromium webkit` in each existing
   > experiment whose tests you'll run (or upgrade its lock deliberately).
   They were restored here from glyphfall's venv.
5. **CLAUDE.md / experiment-workflow.md:** add one line so agents don't repeat this investigation:
   > WebKit offline tests are expected to pass with the template's Playwright (≥ 1.64.1). An offline failure there is a real
   > failure, not the old known issue. Do not add xfail markers for it.

## Existing apps

- glyphfall (lab-owned): can be re-locked to 1.64.1 and its xfail marker removed. Owner's call.
- welcome: still on 1.62.0 and needs the same upgrade if its WebKit offline evidence matters.
