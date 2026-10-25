const VERSION = "exorehab-v2";
const FILES = ["app.html","index.html","shared/tokens.css","shared/content.js","shared/logo-mark.svg","shared/fonts/PlusJakartaSans.ttf","css/app.css","css/landing.css","js/app.js","js/icons.js","js/exoarm.js","js/landing.js","js/model.js","js/firebase-live.js","simulator.html"];
self.addEventListener("install", e => e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== VERSION).map(x => caches.delete(x))))));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || !e.request.url.startsWith(self.location.origin)) return;
  e.respondWith(fetch(e.request).then(r => { if (r.status === 200) { const c = r.clone(); caches.open(VERSION).then(x => x.put(e.request, c)); } return r; }).catch(() => caches.match(e.request)));
});
