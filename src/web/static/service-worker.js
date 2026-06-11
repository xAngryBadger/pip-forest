const CACHE_NAME = 'orca-v7-shell-v1';
const STATIC_CACHE = 'orca-v7-static-v1';
const API_CACHE = 'orca-v7-api-v1';

const SHELL_URLS = [
  '/',
  '/app',
  '/login',
  '/static/manifest.json',
  '/static/app.js',
];

const STATIC_ASSETS_PATTERNS = [
  /^\/static\//,
  /^https:\/\/fonts\.googleapis\.com/,
  /^https:\/\/fonts\.gstatic\.com/,
  /^https:\/\/cdn\.tailwindcss\.com/,
  /^https:\/\/unpkg\.com/,
  /^https:\/\/cdn\.jsdelivr\.net/,
];

const API_PATTERNS = [
  /^\/step\//,
  /^\/term\/api\//,
  /^\/term\/upload\//,
  /^\/upload/,
  /^\/download\//,
];

function isStaticAsset(url) {
  return STATIC_ASSETS_PATTERNS.some(pattern => pattern.test(url));
}

function isApiRequest(url) {
  return API_PATTERNS.some(pattern => pattern.test(url));
}

async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request) {
  const cache = await caches.open(API_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cached);
  return cached || fetchPromise;
}

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME && key !== STATIC_CACHE && key !== API_CACHE)
          .map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') {
    return;
  }

  if (SHELL_URLS.includes(url.pathname) || url.pathname === '/') {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  if (isStaticAsset(request.url)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (isApiRequest(request.url)) {
    event.respondWith(networkFirst(request));
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});

self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});