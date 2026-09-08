// Edit this preserved template; publish regenerates sw.js from shell content.
const PREFIX = '{{NAME}}-shell-';
const CACHE = PREFIX + '__LAB_CACHE__';
const ASSETS = __LAB_ASSETS__;
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  // Wait for existing tabs to close; never replace a running game's worker.
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith(PREFIX) && key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  // Keep this shell revision coherent; never cache API or arbitrary network responses.
  if (ASSETS.includes(url.pathname)) {
    event.respondWith(caches.open(CACHE).then(cache => cache.match(url.pathname)).then(hit => hit || fetch(request)));
  } else if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.open(CACHE).then(cache => cache.match('/index.html'))));
  }
});
