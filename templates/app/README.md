# {{TITLE}}

{{URL}}

FastAPI + static PWA shell, scaffolded by `newlab`. **This is scaffolding — the
requested app has not been built yet.**

    main.py        the API; serves public/ via an explicit catch-all route
    public/        the PWA (index.html, app.js, sw.js, manifest, icons)
    pyproject.toml + uv.lock — the reproducible dependency set
    .env           non-secret settings (APP_NAME, PORT, SQLite URL)
    install.md     what exists outside this directory
    data/          the only directory this app may write to

Secrets are NOT in this directory. They live in `/etc/lab/apps/{{NAME}}.env`,
owned by root and readable only by this app's user, and are injected by systemd.
Request more with `labctl secrets-grant`.

    sudo /usr/local/sbin/labctl service restart {{NAME}}
    sudo /usr/local/sbin/labctl logs {{NAME}}
