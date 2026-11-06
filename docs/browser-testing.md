# Browser testing profile

This server supports Chromium and Playwright WebKit testing. For shared web apps,
run both engines: `labpreflight NAME --engines chromium webkit`. Preflight only
proves browser launch and synthetic screenshots; configure the app tests to run
both engines too. Linux WebKit does not replace physical iPhone installation,
push, microphone, media or gesture testing.

## Ubuntu 24.04 LTS (recommended)

The package list below records a previous 24.04 installation. Re-evaluate the
requirements with the experiment's locked Playwright version and the actual host
before installing; point releases and browser versions can change dependencies.
Ubuntu 26.04 is experimental. Do not reuse the 24.04 package list unchanged there;
review browser support and any dependency/lockfile update separately.

As lab, in the experiment app directory with locked dev dependencies installed:

```sh
.venv/bin/playwright install-deps --dry-run webkit
```

The dry run can exit with status 1 when dependencies are missing, while still
printing the required package plan. Inspect that output; it is not proof that
browser setup failed, and it does not install packages.

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

## Fresh 24.04 browser evidence — 2026-11-06

A clean Ubuntu 24.04.5 installation with the templates' locked Playwright 1.62.0
passed Chromium and WebKit launch plus phone/desktop screenshot preflight after
reviewed OS dependency installation. The unprivileged runtime checks passed for
static and backend scaffolds. A publicly served welcome app passed normal HTTPS,
install-dialog and JavaScript checks in both engines; Chromium also passed offline
reload and reconnect, including from an external browser.

Linux WebKit 26.5 repeatedly reported `Page.reload: WebKit encountered an internal
error` during simulated offline reload, even after service-worker control and all
10 cached assets were confirmed. This is unresolved: do not label WebKit offline
behavior passed or assume the failure proves an iPhone bug. Real Safari/iPhone
installation and offline checks remain necessary. Retain the failing result in
app evidence rather than swallowing it or weakening offline assertions.
