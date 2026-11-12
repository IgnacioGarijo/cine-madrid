const reply=(body,status,origin)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json; charset=utf-8','Access-Control-Allow-Origin':origin,'Vary':'Origin','Cache-Control':'no-store'}});

import {handleAccount} from './accounts.mjs';
export {AccountData} from './accounts.mjs';
import {handleFavorites} from './favorites.mjs';
export {Favorites} from './favorites.mjs';

export async function handle(request,env,{upstreamFetch=fetch,cache=globalThis.caches?.default}={}) {
  const url=new URL(request.url), allowed=env.ALLOWED_ORIGIN || 'https://ignaciogarijo.github.io';
  if (url.pathname==='/health' && request.method==='GET') return reply({ready:!!env.TMDB_READ_TOKEN},200,allowed);
  const accountRoute=url.pathname.startsWith('/me/');
  const favoritesRoute=url.pathname==='/favorites' || url.pathname==='/session' || /^\/favorites\/\d+$/.test(url.pathname);
  if ((favoritesRoute || accountRoute) && request.method!=='OPTIONS') {
    const result=await (accountRoute ? handleAccount : handleFavorites)(request,env,{upstreamFetch});
    const response=new Response(result.body,result);
    response.headers.set('Access-Control-Allow-Origin',allowed);response.headers.set('Vary','Origin');
    return response;
  }
  if (request.headers.get('Origin')!==allowed) return reply({error:'origin_not_allowed'},403,allowed);
  if (request.method==='OPTIONS') return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':allowed,'Access-Control-Allow-Methods':'GET, POST, PUT, DELETE, OPTIONS','Access-Control-Allow-Headers':'Authorization, Content-Type','Access-Control-Max-Age':'600','Vary':'Origin'}});
  if (request.method!=='GET' || url.pathname!=='/search') return reply({error:'not_found'},404,allowed);
  const query=(url.searchParams.get('q') || '').trim(), rawPage=url.searchParams.get('page') || '1', page=Number(rawPage);
  if (query.length<2 || query.length>100 || !/^\d+$/.test(rawPage) || page<1 || page>500) return reply({error:'invalid_query'},400,allowed);
  if (!env.TMDB_READ_TOKEN || !env.SEARCH_RATE_LIMITER) return reply({error:'not_configured'},503,allowed);
  const limit=await env.SEARCH_RATE_LIMITER.limit({key:request.headers.get('CF-Connecting-IP') || 'unknown'});
  if (!limit.success) return reply({error:'rate_limited'},429,allowed);
  const key=new URL('/search',url.origin);key.search=new URLSearchParams({q:query.toLocaleLowerCase('es'),page:String(page)}).toString();
  const cacheKey=new Request(key);
  const cached=cache ? await cache.match(cacheKey) : null;
  if (cached) return cached;
  try {
    // Only this fixed TMDB read endpoint is reachable; no arbitrary upstream URLs or writes.
    const upstream=new URL('https://api.themoviedb.org/3/search/movie');
    upstream.search=new URLSearchParams({query,language:'es-ES',include_adult:'false',page:String(page)}).toString();
    const response=await upstreamFetch(upstream,{headers:{Authorization:'Bearer '+env.TMDB_READ_TOKEN,Accept:'application/json'},signal:AbortSignal.timeout(6000)});
    if (!response.ok) return reply({error:'tmdb_unavailable'},502,allowed);
    const payload=await response.json();
    const movies=(payload.results || []).filter(movie=>Number.isInteger(movie.id)).slice(0,20).map(movie=>({
      id:'tmdb:'+movie.id,tmdb_id:movie.id,title:movie.title || movie.original_title,original_title:movie.original_title || '',
      year:movie.release_date ? Number(movie.release_date.slice(0,4)) || null : null,
      source_url:'https://www.themoviedb.org/movie/'+movie.id
    }));
    const result=reply({query,page,total_pages:Math.min(payload.total_pages || 0,500),total_results:payload.total_results || 0,movies},200,allowed);
    result.headers.set('Cache-Control','public, max-age=900');
    if (cache) await cache.put(cacheKey,result.clone());
    return result;
  } catch {return reply({error:'tmdb_unavailable'},502,allowed);}
}
export default {fetch(request,env){return handle(request,env);}};
