import test from 'node:test';
import assert from 'node:assert/strict';
import {handle} from './worker.mjs';
import {AccountData} from './accounts.mjs';
import {Favorites} from './favorites.mjs';
const origin='https://ignaciogarijo.github.io';
const ids={alice:'11111111-1111-4111-8111-111111111111',bob:'22222222-2222-4222-8222-222222222222'};
function binding(Class){
  const objects=new Map();
  return {idFromName:name=>name,get(name){
    if(!objects.has(name)){
      const values=new Map();let queue=Promise.resolve();
      objects.set(name,new Class({storage:{get:async key=>structuredClone(values.get(key)),put:async(key,value)=>values.set(key,structuredClone(value))},
        blockConcurrencyWhile:fn=>{const task=queue.then(fn);queue=task.catch(()=>{});return task;}}));
    }
    return objects.get(name);
  }};
}
function fixture(){
  const env={ALLOWED_ORIGIN:origin,SUPABASE_URL:'https://project.supabase.co',SUPABASE_PUBLISHABLE_KEY:'public-test-key',
    ACCOUNTS:binding(AccountData),FAVORITES:binding(Favorites),TMDB_READ_TOKEN:'private-tmdb-token',
    SEARCH_RATE_LIMITER:{limit:async()=>({success:true})}};
  const deps={upstreamFetch:async(url,options)=>{
    if(String(url)==='https://project.supabase.co/auth/v1/user'){
      assert.equal(options.headers.apikey,'public-test-key');
      const id=ids[options.headers.Authorization?.slice(7)];
      return id ? Response.json({id}) : Response.json({error:'invalid session'},{status:401});
    }
    assert.match(String(url),/^https:\/\/api.themoviedb.org\/3\/movie\/149\?/);
    return Response.json({id:149,title:'Akira',release_date:'1988-07-16',credits:{crew:[{job:'Director',name:'Katsuhiro Otomo'}]}});
  }};
  const call=(path,token='alice',method='GET',body)=>handle(new Request('https://worker.test'+path,{method,
    headers:{Origin:origin,...(token?{Authorization:'Bearer '+token}:{}),'Content-Type':'application/json'},
    ...(body===undefined?{}:{body:JSON.stringify(body)})}),env,deps);
  return {env,deps,call};
}
test('private routes reject absent, invalid and expired sessions without exposing data',async()=>{
  const {call}=fixture();
  for(const token of [null,'invalid','expired'])for(const path of ['/me/favorites','/me/profile']){
    const response=await call(path,token);assert.equal(response.status,401);
    assert.equal(response.headers.get('Cache-Control'),'no-store');
  }
});
test('verified identity isolates favorite reads and writes, ignoring forged user IDs',async()=>{
  const {call}=fixture();
  assert.deepEqual(await (await call('/me/favorites')).json(),[]);
  const saved=await call('/me/favorites','alice','POST',{tmdb_id:149,user_id:ids.bob,title:'forged'});
  assert.equal(saved.status,200);assert.equal((await saved.json())[0].title,'Akira');
  assert.deepEqual(await (await call('/me/favorites','bob')).json(),[]);
  await call('/me/favorites/149','bob','DELETE');
  assert.equal((await (await call('/me/favorites')).json()).length,1);
  await call('/me/favorites/149','alice','DELETE');
  assert.deepEqual(await (await call('/me/favorites')).json(),[]);
});
test('origins are private, strictly validated and cleared without touching other users',async()=>{
  const {call}=fixture(),point={lat:40.4,lon:-3.7,label:'Dirección de prueba'};
  assert.equal((await call('/me/profile','alice','PUT',{origin:point,user_id:ids.bob})).status,200);
  assert.deepEqual(await (await call('/me/profile')).json(),{origin:point});
  assert.deepEqual(await (await call('/me/profile','bob')).json(),{origin:null});
  for(const invalid of [{lat:91,lon:0,label:'x'},{lat:'40',lon:0,label:'x'},{lat:0,lon:0,label:''}]){
    assert.equal((await call('/me/profile','alice','PUT',{origin:invalid})).status,400);
  }
  assert.deepEqual(await (await call('/me/profile','alice','PUT',{origin:null})).json(),{origin:null});
});
test('legacy import is explicit, duplicate-safe and never affects another account or public list',async()=>{
  const {call}=fixture(),legacy=await (await call('/favorites',null)).json();
  assert.equal((await call('/favorites','alice','POST',{tmdb_id:149})).status,410);
  for(let i=0;i<2;i++)assert.deepEqual(await (await call('/me/import','alice','POST')).json(),legacy);
  assert.deepEqual(await (await call('/me/favorites','bob')).json(),[]);
  await call('/me/favorites/'+legacy[0].tmdb_id,'alice','DELETE');
  assert.deepEqual(await (await call('/favorites',null)).json(),legacy);
});
test('auth outage and foreign origins fail closed without returning upstream errors',async()=>{
  const {env,call}=fixture();
  const foreign=new Request('https://worker.test/me/profile',{headers:{Origin:'https://foreign.test',Authorization:'Bearer alice'}});
  assert.equal((await handle(foreign,env)).status,403);
  const response=await handle(new Request('https://worker.test/me/profile',{headers:{Origin:origin,Authorization:'Bearer alice'}}),env,
    {upstreamFetch:async()=>new Response('upstream secret',{status:500})});
  assert.equal(response.status,503);assert.ok(!(await response.text()).includes('upstream secret'));
  assert.equal((await call('/me/profile')).headers.get('Access-Control-Allow-Origin'),origin);
});
