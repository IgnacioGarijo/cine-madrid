import initialMovies from '../../config/favorites.json' with {type:'json'};

const json=(body,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store'}});
const encoder=new TextEncoder();
const encode=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
const signingKey=secret=>crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);

export async function newSession(secret, now=Date.now()) {
  const expires=now+30*24*60*60*1000;
  const payload=btoa(JSON.stringify({expires,nonce:crypto.randomUUID()}));
  const signature=encode(await crypto.subtle.sign('HMAC',await signingKey(secret),encoder.encode(payload)));
  return {token:payload+'.'+signature,expires};
}
export async function validSession(token,secret,now=Date.now()) {
  if (!secret || !token || token.length>1000) return false;
  try {
    const [payload,signature,...extra]=token.split('.');
    const expires=JSON.parse(atob(payload)).expires;
    if (extra.length || !signature || !Number.isFinite(expires) || expires<=now) return false;
    const bytes=Uint8Array.from(atob(signature.replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0));
    return await crypto.subtle.verify('HMAC',await signingKey(secret),bytes,encoder.encode(payload));
  } catch {return false;}
}
async function sameSecret(a,b) {
  const digest=async value=>new Uint8Array(await crypto.subtle.digest('SHA-256',encoder.encode(value)));
  const [left,right]=await Promise.all([digest(a),digest(b)]);
  return left.reduce((difference,value,index)=>difference | (value^right[index]),0)===0;
}
async function body(request) {
  if (Number(request.headers.get('Content-Length') || 0)>2048) throw Error('large');
  if(!request.body)throw Error('missing');
  const reader=request.body.getReader(),chunks=[];let size=0;
  while(true) {
    const {done,value}=await reader.read();if(done)break;
    size+=value.byteLength;
    if(size>2048){await reader.cancel();throw Error('large');}
    chunks.push(value);
  }
  const bytes=new Uint8Array(size);let offset=0;
  for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
  return JSON.parse(new TextDecoder().decode(bytes));
}

// One object serializes changes from every device; redeploying never reseeds it.
export class Favorites {
  constructor(state) {this.state=state;}
  async fetch(request) {
    return this.state.blockConcurrencyWhile(async()=>{
      let movies=await this.state.storage.get('movies');
      if (!movies) {movies=structuredClone(initialMovies);await this.state.storage.put('movies',movies);}
      if(request.method==='POST') {
        const movie=await request.json();
        if (!movies.some(item=>item.id===movie.id)) {
          if(movies.length>=2000)return json({error:'list_full'},409);
          movies=[...movies,movie];await this.state.storage.put('movies',movies);
        }
      } else if(request.method==='DELETE') {
        const id=new URL(request.url).pathname.split('/').pop();
        movies=movies.filter(item=>String(item.tmdb_id)!==id);await this.state.storage.put('movies',movies);
      } else if(request.method!=='GET')return json({error:'method_not_allowed'},405);
      return json(movies);
    });
  }
}

export async function handleFavorites(request,env,{upstreamFetch=fetch}={}) {
  const url=new URL(request.url), allowed=env.ALLOWED_ORIGIN || 'https://ignaciogarijo.github.io';
  const publicRead=request.method==='GET' && url.pathname==='/favorites';
  if(!publicRead && request.headers.get('Origin')!==allowed)return json({error:'origin_not_allowed'},403);
  if(!env.FAVORITES)return json({error:'not_configured'},503);
  if(publicRead)return env.FAVORITES.get(env.FAVORITES.idFromName('public-watchlist')).fetch(new Request('https://favorites/favorites'));
  if(!env.FAVORITES_OWNER_SECRET)return json({error:'owner_not_configured'},503);
  const sessionRoute=url.pathname==='/session' && request.method==='POST';
  const limiter=sessionRoute ? env.AUTH_RATE_LIMITER : env.SEARCH_RATE_LIMITER;
  if(!limiter)return json({error:'not_configured'},503);
  if(!(await limiter.limit({key:request.headers.get('CF-Connecting-IP') || 'unknown'})).success)return json({error:'rate_limited'},429);
  if(sessionRoute) {
    let input;try{input=await body(request);}catch{return json({error:'invalid_request'},400);}
    if(typeof input.secret!=='string' || input.secret.length>256 || !await sameSecret(input.secret,env.FAVORITES_OWNER_SECRET))return json({error:'unauthorized'},401);
    return json(await newSession(env.FAVORITES_OWNER_SECRET));
  }
  if(!await validSession(request.headers.get('Authorization')?.replace(/^Bearer /,''),env.FAVORITES_OWNER_SECRET))return json({error:'unauthorized'},401);
  const store=env.FAVORITES.get(env.FAVORITES.idFromName('public-watchlist'));
  if(request.method==='DELETE' && /^\/favorites\/[1-9]\d{0,9}$/.test(url.pathname))return store.fetch(new Request('https://favorites'+url.pathname,{method:'DELETE'}));
  if(request.method!=='POST' || url.pathname!=='/favorites')return json({error:'not_found'},404);
  let input;try{input=await body(request);}catch{return json({error:'invalid_request'},400);}
  if(!Number.isSafeInteger(input.tmdb_id) || input.tmdb_id<=0 || input.tmdb_id>9999999999)return json({error:'invalid_movie'},400);
  if(!env.TMDB_READ_TOKEN)return json({error:'not_configured'},503);
  try {
    // Only the ID comes from the browser; TMDB verifies all saved metadata.
    const response=await upstreamFetch('https://api.themoviedb.org/3/movie/'+input.tmdb_id+'?language=es-ES&append_to_response=credits,alternative_titles',{
      headers:{Authorization:'Bearer '+env.TMDB_READ_TOKEN,Accept:'application/json'},signal:AbortSignal.timeout(6000)});
    if(response.status===404)return json({error:'movie_not_found'},404);
    if(!response.ok)return json({error:'tmdb_unavailable'},502);
    const movie=await response.json();
    if(movie.id!==input.tmdb_id || !movie.title)return json({error:'invalid_movie'},502);
    const record={id:'tmdb:'+movie.id,tmdb_id:movie.id,title:movie.title,original_title:movie.original_title || '',
      year:movie.release_date ? Number(movie.release_date.slice(0,4)) || null : null,
      director:(movie.credits?.crew || []).filter(item=>item.job==='Director').map(item=>item.name).join(', '),
      aliases:[...new Set((movie.alternative_titles?.titles || []).map(item=>item.title).filter(Boolean))],
      source_url:'https://www.themoviedb.org/movie/'+movie.id};
    return store.fetch(new Request('https://favorites/favorites',{method:'POST',body:JSON.stringify(record)}));
  } catch {return json({error:'tmdb_unavailable'},502);}
}
