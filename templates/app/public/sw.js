// Offline shell for {{NAME}}.
//
// Deliberately conservative:
//   * only the listed shell assets are pre-cached — nothing is cached opportunistically
//   * /api/* is never cached, so authenticated or private responses are not persisted
//   * non-200 and non-basic responses are never stored
//   * navigations fall back to the cached shell only when the network fails
//
// Bump CACHE whenever the ASSETS list changes, or clients keep the old shell.
const CACHE = '{{NAME}}-v1';
const ASSETS = ['/', '/index.html', '/app.js', '/icon.svg', '/manifest.webmanifest'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;   // always live, never stored

  // Navigations: network first, cached shell only if the network is unavailable.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Shell assets: serve from cache, refresh in the background.
  event.respondWith(
    caches.match(request).then(hit => {
      const fresh = fetch(request).then(res => {
        if (res.ok && res.type === 'basic' && ASSETS.includes(url.pathname)) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || fresh;
    })
  );
});
