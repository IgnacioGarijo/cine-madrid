import {Favorites,handleFavorites,body} from './favorites.mjs';
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});

// Separate durable objects and empty seeds prevent shared-list and account data mixing.
export class AccountData extends Favorites {
  constructor(state){super(state,[]);}
  async fetch(request){
    const path=new URL(request.url).pathname;
    if(path==='/profile')return this.state.blockConcurrencyWhile(async()=>{
      if(request.method==='PUT')await this.state.storage.put('origin',await request.json());
      else if(request.method!=='GET')return json({error:'method_not_allowed'},405);
      return json({origin:await this.state.storage.get('origin') || null});
    });
    if(path==='/import')return this.state.blockConcurrencyWhile(async()=>{
      const existing=await this.state.storage.get('movies') || [], incoming=await request.json();
      const merged=[...new Map([...existing,...incoming].map(movie=>[movie.id,movie])).values()];
      if(merged.length>2000)return json({error:'list_full'},409);
      await this.state.storage.put('movies',merged);return json(merged);
    });
    return super.fetch(request);
  }
}

export async function handleAccount(request,env,{upstreamFetch=fetch}={}){
  const path=new URL(request.url).pathname;
  if(request.headers.get('Origin')!==env.ALLOWED_ORIGIN)return json({error:'origin_not_allowed'},403);
  if(!env.SUPABASE_URL || !env.SUPABASE_PUBLISHABLE_KEY || !env.ACCOUNTS)return json({error:'not_configured'},503);
  const authorization=request.headers.get('Authorization');
  if(!/^Bearer [^\s]{1,8192}$/.test(authorization || ''))return json({error:'unauthorized'},401);
  if(!env.SEARCH_RATE_LIMITER || !(await env.SEARCH_RATE_LIMITER.limit({key:'account:'+ (request.headers.get('CF-Connecting-IP') || 'unknown')})).success)return json({error:'rate_limited'},429);
  let user;
  try{
    // Auth server verifies the session. No client-provided user ID determines storage.
    const response=await upstreamFetch(env.SUPABASE_URL+'/auth/v1/user',{
      headers:{apikey:env.SUPABASE_PUBLISHABLE_KEY,Authorization:authorization},signal:AbortSignal.timeout(6000)});
    if(response.status===401 || response.status===403)return json({error:'unauthorized'},401);
    if(!response.ok)return json({error:'auth_unavailable'},503);
    user=await response.json();
    if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(user.id || ''))return json({error:'unauthorized'},401);
  }catch{return json({error:'auth_unavailable'},503);}
  const account=env.ACCOUNTS.get(env.ACCOUNTS.idFromName('user:'+user.id));
  if(path==='/me/profile'){
    if(request.method==='GET')return account.fetch(new Request('https://account/profile'));
    if(request.method!=='PUT')return json({error:'method_not_allowed'},405);
    let input;try{input=await body(request);}catch{return json({error:'invalid_request'},400);}
    const point=input?.origin;
    if(point!==null && (!point || typeof point.label!=='string' || !point.label.trim() || point.label.length>300 || !Number.isFinite(point.lat) || Math.abs(point.lat)>90 || !Number.isFinite(point.lon) || Math.abs(point.lon)>180))return json({error:'invalid_origin'},400);
    const origin=point===null ? null : {label:point.label.trim(),lat:point.lat,lon:point.lon};
    return account.fetch(new Request('https://account/profile',{method:'PUT',body:JSON.stringify(origin)}));
  }
  if(path==='/me/import' && request.method==='POST'){
    const legacy=env.FAVORITES.get(env.FAVORITES.idFromName('public-watchlist'));
    const response=await legacy.fetch(new Request('https://favorites/favorites'));
    if(!response.ok)return json({error:'import_unavailable'},503);
    return account.fetch(new Request('https://account/import',{method:'POST',body:JSON.stringify(await response.json())}));
  }
  if(path==='/me/favorites' || /^\/me\/favorites\/[1-9]\d{0,9}$/.test(path)){
    const target=new URL(request.url);target.pathname=path.slice(3);
    // Reuse TMDB verification and mutations, with storage bound to verified identity.
    return handleFavorites(new Request(target,request),{...env,PUBLIC_FAVORITES:'true',ACCOUNT_VERIFIED:true,
      FAVORITES:{idFromName:()=>user.id,get:()=>account},SEARCH_RATE_LIMITER:{limit:async()=>({success:true})}},{upstreamFetch});
  }
  return json({error:'not_found'},404);
}
