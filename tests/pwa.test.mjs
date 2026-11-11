import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';

async function workerHarness() {
  const handlers = new Map(), stores = new Map();
  let offline = false;
  const key = request => typeof request === 'string' ? request : request.url;
  const caches = {
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const entries = stores.get(name);
      return {
        async put(request,response) {entries.set(key(request),response.clone());},
        async match(request) {return entries.get(key(request))?.clone();},
        async addAll(urls) {for (const url of urls) entries.set(url,new Response('shell'));}
      };
    },
    async keys() {return [...stores.keys()];},
    async delete(name) {return stores.delete(name);},
    async match(request) {for (const entries of stores.values()) if (entries.has(key(request))) return entries.get(key(request)).clone();}
  };
  const context = {
    URL, Request, Response, Headers, caches,
    fetch: async () => {if (offline) throw new Error('No network'); return new Response('{"version":"fresh"}',{headers:{'Content-Type':'application/json'}});},
    self: {location:{href:'https://example.test/cine-madrid/sw.js'},
      addEventListener: (name,handler) => handlers.set(name,handler),
      skipWaiting:async()=>{}, clients:{claim:async()=>{}}}
  };
  vm.runInNewContext(await fs.readFile(new URL('../web/sw.js',import.meta.url),'utf8'),context);
  return {handlers,stores,setOffline:value=>{offline=value;},async lifecycle(name) {let completion; handlers.get(name)({waitUntil:p=>{completion=p;}});await completion;},
    async request(url,mode='cors') {let response;handlers.get('fetch')({request:{url,mode,method:'GET'},respondWith:p=>{response=p;}});return response && await response;}};
}

test('offline data retains content and explicitly identifies the cached response', async () => {
  const worker = await workerHarness(); await worker.lifecycle('install');
  const url='https://example.test/cine-madrid/data.json';
  assert.equal((await worker.request(url)).headers.get('X-Cine-Madrid-Cache'),null);
  worker.setOffline(true);
  const cached = await worker.request(url);
  assert.equal(cached.headers.get('X-Cine-Madrid-Cache'),'offline');
  assert.deepEqual(await cached.json(),{version:'fresh'});
});
test('worker does not intercept other projects or external APIs and ticket sites', async () => {
  const worker = await workerHarness();
  assert.equal(await worker.request('https://example.test/other-project/data.json'),undefined);
  assert.equal(await worker.request('https://tickets.example/cine-madrid/data.json'),undefined);
});
test('offline navigation opens the saved app shell', async () => {
  const worker = await workerHarness();await worker.lifecycle('install');worker.setOffline(true);
  assert.equal(await (await worker.request('https://example.test/cine-madrid/','navigate')).text(),'shell');
});
test('install manifest is relative to the GitHub Pages project and icons exist at actual sizes', async () => {
  const manifest = JSON.parse(await fs.readFile(new URL('../web/manifest.webmanifest',import.meta.url),'utf8'));
  const base='https://example.test/cine-madrid/manifest.webmanifest';
  assert.equal(new URL(manifest.scope,base).pathname,'/cine-madrid/');
  assert.equal(new URL(manifest.start_url,base).pathname,'/cine-madrid/');
  assert.equal(manifest.display,'standalone');
  for (const icon of manifest.icons) {
    const png = await fs.readFile(new URL('../web/'+icon.src,import.meta.url));
    const [width,height]=icon.sizes.split('x').map(Number);
    assert.equal(png.readUInt32BE(16),width);assert.equal(png.readUInt32BE(20),height);
  }
});
