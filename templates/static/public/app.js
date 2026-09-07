// Registers the service worker so this installs as a PWA.
// Replace with the actual app.
if ('serviceWorker' in navigator) {
  addEventListener('load', () => navigator.serviceWorker.register('/sw.js'));
}
