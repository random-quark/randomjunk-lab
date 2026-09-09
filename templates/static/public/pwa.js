// Reusable install UX. Keep this separate from app.js when replacing the scaffold.
let installEvent = null;
const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone;
const remember = () => { try { localStorage.setItem('lab-install-dismissed', 'yes'); } catch {} };
const panel = document.getElementById('lab-install-panel');
const open = document.getElementById('lab-install-open');
const install = document.getElementById('lab-install-native');
const help = document.getElementById('lab-install-help');
function update() {
  open.hidden = !!standalone();
  install.hidden = !installEvent || !!standalone();
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  help.textContent = installEvent ? 'Install this app for quick access from your home screen.' :
    ios ? 'On iPhone or iPad: open in Safari, tap Share, then Add to Home Screen.' :
    'In Chrome or Brave, open the browser menu and choose Install app or Add to Home screen. If unavailable, try opening this link in Chrome.';
  if (standalone()) panel.close();
}
open.addEventListener('click', () => { update(); panel.showModal(); });
document.getElementById('lab-install-later').addEventListener('click', () => panel.close());
panel.addEventListener('close', remember);
window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); installEvent = event; update(); });
window.addEventListener('appinstalled', () => { installEvent = null; remember(); panel.close(); open.hidden = true; });
install.addEventListener('click', async () => {
  const event = installEvent;
  if (!event) return;
  installEvent = null;
  try { await event.prompt(); await event.userChoice; panel.close(); } finally { update(); }
});
// Installation opens only on an explicit Install app tap, never on a timer.
update();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {
  document.getElementById('lab-offline-status').textContent = 'Offline setup is unavailable. You can continue online.';
});
function connectivity() {
  document.getElementById('lab-offline-status').textContent = navigator.onLine ? '' : 'Offline: saved pages can open; network features need a connection.';
}
window.addEventListener('online', connectivity);
window.addEventListener('offline', connectivity);
connectivity();
