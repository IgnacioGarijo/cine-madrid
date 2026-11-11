import test from 'node:test';
import assert from 'node:assert/strict';
import {handle} from './worker.mjs';
const origin='https://ignaciogarijo.github.io';
const env=()=>({ALLOWED_ORIGIN:origin,TMDB_READ_TOKEN:'test-only-secret',SEARCH_RATE_LIMITER:{limit:async()=>({success:true})}});
const request=(query='Piratas del',headers={})=>new Request('https://test.workers.dev/search?'+new URLSearchParams({q:query}),{headers:{Origin:origin,...headers}});
test('global TMDB suggestions return stable identities and never expose the credential',async()=>{
  let target,options;
  const response=await handle(request(),env(),{upstreamFetch:async(url,init)=>{target=url;options=init;return Response.json({page:1,total_pages:2,total_results:25,results:[{id:22,title:'Piratas del Caribe',release_date:'2003-07-09'}]});}});
  const body=await response.text();assert.equal(response.status,200);assert.equal(JSON.parse(body).movies[0].id,'tmdb:22');
  assert.equal(target.origin,'https://api.themoviedb.org');assert.equal(target.pathname,'/3/search/movie');assert.equal(options.headers.Authorization,'Bearer test-only-secret');assert.ok(!body.includes('test-only-secret'));
});
test('foreign origins, invalid input and non-search routes cannot use the upstream',async()=>{
  const fail=()=>{throw Error('Should not call TMDB');};
  assert.equal((await handle(request('Piratas',{Origin:'https://other.example'}),env(),{upstreamFetch:fail})).status,403);
  assert.equal((await handle(request('p'),env(),{upstreamFetch:fail})).status,400);
  assert.equal((await handle(new Request('https://test.workers.dev/arbitrary',{headers:{Origin:origin}}),env(),{upstreamFetch:fail})).status,404);
});
test('rate limiting stops upstream calls',async()=>{
  const settings=env();settings.SEARCH_RATE_LIMITER.limit=async()=>({success:false});
  const response=await handle(request(),settings,{upstreamFetch:()=>{throw Error('Should not call');}});assert.equal(response.status,429);
});
test('repeated suggestions are cached and preserve CORS',async()=>{
  const entries=new Map();let calls=0;
  const cache={match:async key=>entries.get(key.url)?.clone(),put:async(key,response)=>entries.set(key.url,response)};
  const dependencies={cache,upstreamFetch:async()=>{calls++;return Response.json({results:[],total_results:0});}};
  await handle(request(),env(),dependencies);const second=await handle(request(),env(),dependencies);
  assert.equal(calls,1);assert.equal(second.headers.get('Access-Control-Allow-Origin'),origin);
});
test('upstream errors do not return upstream bodies or credentials',async()=>{
  const response=await handle(request(),env(),{upstreamFetch:async()=>new Response('upstream test-only-secret',{status:401})});
  assert.equal(response.status,502);assert.equal(await response.text(),'{"error":"tmdb_unavailable"}');
});
