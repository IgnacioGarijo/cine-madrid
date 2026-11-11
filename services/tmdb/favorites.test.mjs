import test from 'node:test';
import assert from 'node:assert/strict';
import {handle} from './worker.mjs';
import {Favorites,newSession,validSession} from './favorites.mjs';

const origin='https://ignaciogarijo.github.io', secret='a-long-password-for-tests-only';
function fixture() {
  const data=new Map();let queue=Promise.resolve();
  const state={storage:{get:async key=>structuredClone(data.get(key)),put:async(key,value)=>data.set(key,structuredClone(value))},
    blockConcurrencyWhile:action=>{const result=queue.then(action);queue=result.catch(()=>{});return result;}};
  let object=new Favorites(state);
  const settings={ALLOWED_ORIGIN:origin,FAVORITES_OWNER_SECRET:secret,TMDB_READ_TOKEN:'tmdb-test-secret',
    FAVORITES:{idFromName:name=>name,get:()=>({fetch:request=>object.fetch(request)})},
    AUTH_RATE_LIMITER:{limit:async()=>({success:true})},SEARCH_RATE_LIMITER:{limit:async()=>({success:true})}};
  return {settings,restart:()=>{object=new Favorites(state);}};
}
const request=(path,method='GET',body,token)=>new Request('https://test.workers.dev'+path,{method,
  headers:{Origin:origin,...(token?{Authorization:'Bearer '+token}:{}),'Content-Type':'application/json'},
  ...(body?{body:JSON.stringify(body)}:{})});
const movie={id:149,title:'Akira',original_title:'AKIRA',release_date:'1988-07-16',
  credits:{crew:[{job:'Director',name:'Katsuhiro Otomo'}]},alternative_titles:{titles:[{title:'AKIRA (VOSE)'}]}};

test('public reading is allowed but unauthorized and foreign-origin writes cannot change the list',async()=>{
  const {settings}=fixture();const before=await (await handle(request('/favorites'),settings)).json();
  assert.ok(before.some(m=>m.id==='tmdb:157336'));
  assert.equal((await handle(request('/favorites','POST',{tmdb_id:149}),settings)).status,401);
  const token=(await newSession(secret)).token;
  const foreign=new Request('https://test.workers.dev/favorites/157336',{method:'DELETE',headers:{Origin:'https://other.test',Authorization:'Bearer '+token}});
  assert.equal((await handle(foreign,settings)).status,403);
  assert.deepEqual(await (await handle(request('/favorites'),settings)).json(),before);
});
test('sessions reject wrong passwords, tampering, expiry and revoked credentials',async()=>{
  const {settings}=fixture();
  assert.equal((await handle(request('/session','POST',{secret:'wrong'}),settings)).status,401);
  const response=await handle(request('/session','POST',{secret}),settings);assert.equal(response.status,200);
  const {token}=await response.json();assert.ok(await validSession(token,secret));
  assert.ok(!await validSession(token+'x',secret));assert.ok(!await validSession(token,'rotated-password'));
  const expired=await newSession(secret,0);assert.ok(!await validSession(expired.token,secret));
  assert.equal(response.headers.get('Cache-Control'),'no-store');assert.equal(response.headers.get('Access-Control-Allow-Origin'),origin);
});
test('saving rechecks TMDB identity, persists aliases and is duplicate-safe across restarts',async()=>{
  const f=fixture(),token=(await newSession(secret)).token;let upstream;
  const deps={upstreamFetch:async url=>{upstream=String(url);return Response.json(movie);}};
  let response=await handle(request('/favorites','POST',{tmdb_id:149,title:'forged-title'},token),f.settings,deps);
  assert.equal(response.status,200);let saved=(await response.json()).find(m=>m.id==='tmdb:149');
  assert.equal(saved.title,'Akira');assert.equal(saved.director,'Katsuhiro Otomo');assert.deepEqual(saved.aliases,['AKIRA (VOSE)']);
  assert.ok(upstream.startsWith('https://api.themoviedb.org/3/movie/149?'));
  f.restart();response=await handle(request('/favorites','POST',{tmdb_id:149},token),f.settings,deps);
  assert.equal((await response.json()).filter(m=>m.id==='tmdb:149').length,1);
  await handle(request('/favorites/149','DELETE',null,token),f.settings);f.restart();
  assert.ok(!(await (await handle(request('/favorites'),f.settings)).json()).some(m=>m.id==='tmdb:149'));
});
test('failed TMDB validation does not save anything and rate limiting protects login',async()=>{
  const {settings}=fixture(),token=(await newSession(secret)).token;
  const response=await handle(request('/favorites','POST',{tmdb_id:149},token),settings,{upstreamFetch:async()=>new Response('secret error',{status:500})});
  assert.equal(response.status,502);assert.ok(!(await (await handle(request('/favorites'),settings)).json()).some(m=>m.id==='tmdb:149'));
  settings.AUTH_RATE_LIMITER.limit=async()=>({success:false});
  assert.equal((await handle(request('/session','POST',{secret}),settings)).status,429);
});
test('CORS preflight allows authenticated changes only from the site',async()=>{
  const {settings}=fixture();
  const response=await handle(request('/favorites','OPTIONS'),settings);
  assert.equal(response.status,204);assert.match(response.headers.get('Access-Control-Allow-Headers'),/Authorization/);
});
