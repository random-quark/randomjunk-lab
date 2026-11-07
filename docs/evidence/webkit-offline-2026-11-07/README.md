# WebKit offline reproduction

Preserved from the lab agent's temporary scratchpad on 2026-11-07. The original
PLATFORM-HANDOFF.md is historical testimony, not current setup instructions;
its claims about all later versions and upstream report absence are not adopted.
Use ../../browser-testing.md for the maintained procedure.

Run as lab with a locked Playwright environment and matching browsers:

```sh
/path/to/app/.venv/bin/python repro.py webkit 3
/path/to/app/.venv/bin/python repro.py chromium 3
```

The script prints each outcome; inspect every result (its exit code alone does
not establish success). It serves only a temporary loopback fixture. Stopping
that server tests origin unavailability, not total network loss. Original
results files retain the investigating agent's evidence; administrator reruns
are recorded separately. Actual iPhone behaviour is not tested here.
