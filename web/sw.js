/* Only public assets under this project's path are cached. API requests and ticket sites are never intercepted. */
const VERSION = 'cine-madrid-0.4.0';
const STATIC = VERSION + '-shell';
const DATA = 'cine-madrid-data-v1';
const ROOT = new URL('./', self.location.href);
const SHELL = ['./', 'index.html', 'style.css?v=0.4.0', 'app.js?v=0.4.0', 'calendar-utils.js?v=0.4.0',
  'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png', 'icons/icon-512.png',
  'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png', 'icons/tmdb.svg'].map(path => new URL(path, ROOT).href);
const PUBLIC_DATA = ['data.json', 'favorites.json', 'catalog.json', 'newsletters.json', 'calendario.ics'];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(STATIC);
    await cache.addAll(SHELL);
    const dataCache = await caches.open(DATA);
    await Promise.allSettled(PUBLIC_DATA.map(async path => {
      const url = new URL(path, ROOT).href, response = await fetch(url, {cache:'no-cache'});
      if (response.ok) await dataCache.put(url, response);
    }));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith('cine-madrid-') && name !== STATIC && name !== DATA).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});
async function networkFirst(request, cacheName, markOffline = false) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (!response.ok) throw new Error('Public resource unavailable');
    await cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    if (!cached) return new Response('Sin conexión y sin datos guardados.', {status:503, headers:{'Content-Type':'text/plain; charset=utf-8'}});
    if (!markOffline) return cached;
    const headers = new Headers(cached.headers); headers.set('X-Cine-Madrid-Cache','offline');
    return new Response(await cached.arrayBuffer(), {status:cached.status, headers});
  }
}
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== ROOT.origin || !url.pathname.startsWith(ROOT.pathname)) return;
  const relative = url.pathname.slice(ROOT.pathname.length);
  if (PUBLIC_DATA.includes(relative)) {
    event.respondWith(networkFirst(event.request, DATA, relative === 'data.json'));
  } else if (event.request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const response = await fetch(event.request);
        if (!response.ok) throw new Error();
        const cache = await caches.open(STATIC); await cache.put(ROOT.href, response.clone());
        return response;
      } catch {
        return (await caches.match(ROOT.href)) || new Response('Abre Cine Madrid con conexión al menos una vez.', {status:503});
      }
    })());
  } else if (SHELL.includes(url.href)) {
    event.respondWith((async () => (await caches.match(event.request)) || fetch(event.request))());
  }
});
