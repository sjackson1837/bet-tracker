/* Bet Tracker service worker.
   Network-first for pages so a fresh deploy is never masked by a stale cache --
   that failure mode is worse than being briefly offline. Cache is only a
   fallback for when there's genuinely no connection. */
const CACHE = 'bet-tracker-v1';
const SHELL = ['index.html', 'results.html', 'manifest.json', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(function(c) { return c.addAll(SHELL).catch(function() {}); }));
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.filter(function(k) { return k !== CACHE; })
                             .map(function(k) { return caches.delete(k); }));
    }).then(function() { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(event) {
  var req = event.request;
  if (req.method !== 'GET') return;
  // Never cache the picks API.
  if (req.url.indexOf('/picks') !== -1 || req.url.indexOf('/toggle-pick') !== -1) return;

  event.respondWith(
    fetch(req).then(function(res) {
      var copy = res.clone();
      caches.open(CACHE).then(function(c) { c.put(req, copy); });
      return res;
    }).catch(function() {
      return caches.match(req).then(function(hit) {
        return hit || caches.match('index.html');
      });
    })
  );
});
