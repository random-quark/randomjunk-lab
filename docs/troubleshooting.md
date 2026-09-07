# Troubleshooting

## Certificate will not issue

- `dig +short <name>.<domain>` — has the wildcard propagated?
- Are ports 80 **and** 443 reachable from outside?
- `journalctl -u caddy -n 80`
- Rate limited? Let's Encrypt allows 50 certificates per registered domain per
  7 days. Check `journalctl -u caddy | grep -i "too many"`. Wait, or use the
  staging issuer for platform testing.

## Service will not start

    sudo /usr/local/sbin/labctl logs <name>

Common causes:

- Missing dependency — check `pyproject.toml`, then `uv sync` in the app dir.
- `ProtectHome=true` plus a uv-managed interpreter under a home directory. The
  venv must be built with `--python /usr/bin/python3`; `UV_PYTHON_DOWNLOADS=never`
  is set in `newlab` to prevent uv fetching its own.
- Writing outside `data/`. That is the only writable path in the unit.

## Caddy deployment refused

`labctl caddy-deploy` validates the whole candidate config and rolls back. The
message names the reason. Structural checks it enforces: the site address must be
`<name>.<domain>`, `import` is not allowed, and any `root` must point inside the
app's own directory.

## `newlab` failed partway

It rolls back automatically. Confirm with:

    labdoctor
    labrm --force <name>     # if anything remains

The resource record in `/srv/lab/.state/<name>.json` is kept when removal is
incomplete, so a retry knows what to clean.

## Ports out of step

`labdoctor` compares `ports.tsv` against the records and against what is actually
listening. Allocation happens under a `flock`, so a collision means something
bypassed `newlab`.

## An app is spending money

    sudo /usr/local/sbin/labctl service stop <name>

Then revoke the key at the provider. A public endpoint calling a paid API needs
its own authentication and rate limiting — the key being server-side does not
stop strangers spending it.

## PWA showing an old app on a reused subdomain

An installed service worker outlives the server-side app. Bump `CACHE` in
`sw.js`, or unregister via DevTools. Best avoided by not reusing a name for a
different app.
