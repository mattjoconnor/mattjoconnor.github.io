// ShowPoint service worker (whole site): makes ShowPoint installable and delivers alert popups.
// It deliberately caches nothing, so every launch loads the latest version (safe for fixes mid-run).
const OFFLINE = '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline</title>'
  + '<body style="margin:0;display:grid;place-items:center;height:100vh;background:#111;color:#fff;font-family:system-ui,sans-serif;text-align:center">'
  + '<div><h1 style="font-size:20px;margin:0 0 8px">No connection</h1><p style="opacity:.7;margin:0">ShowPoint needs a network. It will reload when you reconnect.</p></div>'
  + '<script>addEventListener("online",()=>location.reload())</script>';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;   // database calls, fonts and scripts go straight to the network
  // Pass the browser's own navigation through untouched, so GitHub's folder redirects
  // (e.g. /showcomm/etk/crew -> /crew/) are followed normally. Only step in when offline.
  e.respondWith(fetch(e.request)
    .catch(() => new Response(OFFLINE, {headers: {'Content-Type': 'text/html; charset=utf-8'}})));
});
// Push from the ShowComm alert function: shows even when the phone is locked or the app is closed
self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = {body: e.data ? e.data.text() : ''}; }
  e.waitUntil(self.registration.showNotification(d.title || 'ShowComm', {
    body: d.body || 'New key request', tag: d.tag || undefined, renotify: !!d.tag,
    icon: '/icons/showcomm-any-192.png', badge: '/icons/showcomm-badge-96.png',
    data: {url: d.url || '/showcomm/etk/index.html?role=tm'}
  }));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || self.registration.scope;
  e.waitUntil(self.clients.matchAll({type: 'window', includeUncontrolled: true}).then(list => {
    for (const c of list) if (c.url.startsWith(self.registration.scope) && 'focus' in c) return c.focus();
    return self.clients.openWindow(url);
  }));
});
