const CACHE = 'repro-v1', ASSETS = ['/', '/index.html', '/app.js'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))));
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.mode === 'navigate')
    e.respondWith(fetch(e.request).catch(() => caches.match('/index.html')));
  else if (ASSETS.includes(url.pathname))
    e.respondWith(caches.match(url.pathname).then(hit => hit || fetch(e.request)));
});
