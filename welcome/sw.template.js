// Welcome guide only: prefer current instructions without refreshing active forms.
const PREFIX = 'welcome-shell-';
const CACHE = PREFIX + '__LAB_CACHE__';
const ASSETS = __LAB_ASSETS__;
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key.startsWith(PREFIX) && key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('message', event => {
  if (event.data === 'welcome-version' && event.ports[0]) event.ports[0].postMessage('network-first-v1');
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/_lab/') || url.pathname.startsWith('/api/')) return;
  if (ASSETS.includes(url.pathname)) {
    // Do not store network responses: the published shell cache contains only
    // public build assets. Credentials and enrollment responses never enter it.
    event.respondWith(fetch(request, {cache: 'no-store'}).catch(() =>
      caches.open(CACHE).then(cache => cache.match(url.pathname))));
  }
});
