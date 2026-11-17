/* Only public assets under this project's path are cached. API requests and ticket sites are never intercepted. */
const VERSION = 'cine-madrid-0.11.5';
const STATIC = VERSION + '-shell';
const DATA = 'cine-madrid-data-v1';
const ROOT = new URL('./', self.location.href);
const SHELL = ['account.js?v=0.11.5', 'vendor/supabase-2.119.0.js', './', 'images/cinema-paradiso.jpg', 'index.html', 'style.css?v=0.11.5', 'app.js?v=0.11.5', 'calendar-utils.js?v=0.11.5', 'search-utils.js?v=0.11.5', 'poster-utils.js?v=0.11.5',
  'manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png', 'icons/icon-512.png',
  'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png', 'icons/tmdb.svg'].map(path => new URL(path, ROOT).href);
const PUBLIC_DATA = ['data.json', 'search-config.json', 'favorite-searches.json', 'favorites.json', 'catalog.json', 'newsletters.json', 'calendario.ics'];

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
self.addEventListener('push', event => {
  let payload={};
  try {payload=event.data?.json() || {};} catch {payload={};}
  const title=typeof payload.title==='string' ? payload.title.slice(0,100) : 'Cine Madrid';
  const body=typeof payload.body==='string' ? payload.body.slice(0,240) : 'Tienes novedades en tus favoritas.';
  let target=ROOT.href;
  try {const candidate=new URL(payload.url || ROOT.href,ROOT);if(candidate.origin===ROOT.origin && candidate.pathname.startsWith(ROOT.pathname))target=candidate.href;} catch {}
  event.waitUntil(self.registration.showNotification(title,{body,icon:new URL('icons/icon-192.png',ROOT).href,
    badge:new URL('icons/icon-192.png',ROOT).href,data:{url:target}}));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async()=>{
    const target=event.notification.data?.url || ROOT.href;
    for(const client of await self.clients.matchAll({type:'window',includeUncontrolled:true})){
      if(new URL(client.url).origin===ROOT.origin && new URL(client.url).pathname.startsWith(ROOT.pathname)){
        if(client.navigate)await client.navigate(target);
        return client.focus();
      }
    }
    return self.clients.openWindow(target);
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
