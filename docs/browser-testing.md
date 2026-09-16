# Browser testing profile

This server supports Chromium and Playwright WebKit testing. For shared web apps,
run both engines: `labpreflight NAME --engines chromium webkit`. Preflight only
proves browser launch and synthetic screenshots; configure the app tests to run
both engines too. Linux WebKit does not replace physical iPhone installation,
push, microphone, media or gesture testing.

## Reproduce on Ubuntu 24.04

As lab, in the experiment app directory with locked dev dependencies installed:

```sh
.venv/bin/playwright install-deps --dry-run webkit
```

An administrator reviews its package requirements. Never execute an app-owned
Playwright executable as root or pipe its output into a privileged shell. These
reviewed packages were installed on 2026-09-16 through the system package manager:

```sh
DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l apt-get install -y --no-install-recommends libgtk-4-1 libgraphene-1.0-0 libatomic1 liblcms2-2 libevent-2.1-7t64 libopus0 libgstreamer-plugins-base1.0-0 libgstreamer-gl1.0-0 libgstreamer-plugins-bad1.0-0 gstreamer1.0-libav gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad libflite1 libwebpdemux2 libavif16 libharfbuzz-icu0 libepoxy0 libwebpmux3 libwayland-server0 libwayland-egl1 libwayland-client0 libmanette-0.2-0 libenchant-2-2 libhyphen0 libsecret-1-0 libgles2 libx264-164 libsoup-3.0-0 libwoff1
```

Run apt-get update first on a fresh host. Package names are Ubuntu-specific; review
requirements again for another OS or Playwright version. NEEDRESTART_MODE=l keeps
unrelated service restarts out of this installation; schedule maintenance separately.
Then, as lab (not root):

```sh
.venv/bin/playwright install chromium webkit
labpreflight NAME --engines chromium webkit
```

Browser builds must match each experiment's locked Playwright version. Downloads
are cached under lab's home and shared when versions match. No browser daemon or
new public port is needed. Keep the base bootstrap minimal; this is an explicit
browser-testing profile. Detailed installed package versions are recorded in
docs/webkit-packages.txt.
