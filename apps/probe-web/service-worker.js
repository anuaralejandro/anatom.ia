// Service Worker for anatom.ia Diagnostic Probe App Shell (M04-H6)
// Provides verified offline shell boot without external network requests.

const SHELL_CACHE_NAME = 'anatomia-shell-v0.4.0';
const SHELL_ASSETS = [
  './',
  './index.html',
  './app.js',
  './asset-stream-manager.js',
  './structures.json',
  './pkg-webgpu/atlas_web.js',
  './pkg-webgpu/atlas_web_bg.wasm',
  './pkg-webgl2/atlas_web.js',
  './pkg-webgl2/atlas_web_bg.wasm',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE_NAME).then((cache) => {
      return cache.addAll(SHELL_ASSETS).catch((err) => {
        console.warn('[SW] Some shell assets failed to precache:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key.startsWith('anatomia-shell-') && key !== SHELL_CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Ignore non-GET or cross-origin requests
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Handle glb asset requests: network-first, falling back to all caches
  if (url.pathname.endsWith('.glb')) {
    event.respondWith(
      fetch(event.request).catch(async () => {
        // Search across all open caches (including anatomia-atlas-v*)
        const allCaches = await caches.keys();
        for (const cName of allCaches) {
          const cache = await caches.open(cName);
          const matched = await cache.match(event.request.url);
          if (matched) return matched;
          // Also check by filename match
          const keys = await cache.keys();
          for (const k of keys) {
            if (k.url.endsWith(url.pathname.split('/').pop())) {
              const fileMatch = await cache.match(k);
              if (fileMatch) return fileMatch;
            }
          }
        }
        return new Response('Asset not found offline', { status: 503, statusText: 'Offline Unavailable' });
      })
    );
    return;
  }

  // Manifest and catalog are verified by AssetStreamManager; do not intercept so
  // integrity tests and test mocks (page.route) work cleanly.
  if (url.pathname.endsWith('catalog.json') || url.pathname.endsWith('manifest.json')) {
    return;
  }

  // Shell assets: Cache-first, falling back to network
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch update in background to keep cache fresh
        fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(SHELL_CACHE_NAME).then((cache) => cache.put(event.request, networkResponse));
          }
        }).catch(() => {/* Offline, ignore */});
        return cachedResponse;
      }

      return fetch(event.request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200) {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(SHELL_CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return networkResponse;
      }).catch(async (fetchError) => {
        // If navigation request failed offline, serve index.html
        if (event.request.mode === 'navigate') {
          const shellIndex = await caches.match('./index.html');
          if (shellIndex) return shellIndex;
        }
        throw fetchError;
      });
    })
  );
});
