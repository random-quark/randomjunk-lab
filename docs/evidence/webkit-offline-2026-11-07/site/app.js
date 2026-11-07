document.getElementById('js').textContent = 'js-ok';
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');
