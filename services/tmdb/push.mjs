// Subscriptions are private to verified accounts; only the CI sender can read them.
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
const encoder=new TextEncoder();
const registry=env=>env.ACCOUNTS.get(env.ACCOUNTS.idFromName('push-registry:v1'));
const hex=bytes=>[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('');

function decode(value){
  if(typeof value!=='string' || !/^[A-Za-z0-9_-]+$/.test(value) || value.length>128)throw Error('invalid');
  return Uint8Array.from(atob(value.replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0));
}
export function validPushSubscription(value){
  try {
    if(!value || typeof value.endpoint!=='string' || value.endpoint.length>2048)return false;
    const endpoint=new URL(value.endpoint),host=endpoint.hostname.toLowerCase();
    const allowed=host==='fcm.googleapis.com' || host==='updates.push.services.mozilla.com'
      || host.endsWith('.push.apple.com') || host.endsWith('.notify.windows.com');
    if(!allowed || endpoint.protocol!=='https:' || endpoint.username || endpoint.password || endpoint.port)return false;
    const publicKey=decode(value.keys?.p256dh),auth=decode(value.keys?.auth);
    return publicKey.length===65 && publicKey[0]===4 && auth.length===16;
  } catch {return false;}
}
async function parse(request,limit=4096){
  if(Number(request.headers.get('Content-Length') || 0)>limit || !request.body)throw Error('invalid');
  const reader=request.body.getReader(),chunks=[];let length=0;
  for(;;){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>limit){await reader.cancel();throw Error('invalid');}chunks.push(value);}
  const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
  return JSON.parse(new TextDecoder().decode(bytes));
}

export async function registryFetch(state,request){
  const path=new URL(request.url).pathname;
  return state.blockConcurrencyWhile(async()=>{
    let entries=await state.storage.get('push-subscriptions') || [];
    if(path==='/push-registry/list')return json(entries);
    const input=await request.json();
    if(path==='/push-registry/subscribe'){
      const subscription=input.subscription,id=hex(await crypto.subtle.digest('SHA-256',encoder.encode(subscription.endpoint)));
      const existing=entries.find(e=>e.id===id);
      if(existing && existing.owner!==input.owner && (existing.subscription.keys.p256dh!==subscription.keys.p256dh || existing.subscription.keys.auth!==subscription.keys.auth))return json({error:'conflict'},409);
      if(!existing && (entries.length>=2000 || entries.filter(e=>e.owner===input.owner).length>=5))return json({error:'limit'},409);
      const entry={id,owner:input.owner,subscription,seen:existing?.owner===input.owner ? existing.seen || {} : {}};
      entries=[...entries.filter(e=>e.id!==id),entry];await state.storage.put('push-subscriptions',entries);return json({subscribed:true});
    }
    if(path==='/push-registry/unsubscribe'){
      const id=hex(await crypto.subtle.digest('SHA-256',encoder.encode(input.endpoint)));
      entries=entries.filter(e=>!(e.id===id && e.owner===input.owner));await state.storage.put('push-subscriptions',entries);return json({subscribed:false});
    }
    if(path==='/push-registry/ack'){
      const entry=entries.find(e=>e.id===input.id);if(!entry)return json({error:'not_found'},404);
      if(input.remove){entries=entries.filter(e=>e.id!==input.id);}
      else {
        const current=new Set(input.current),seen={};
        for(const [id,record] of Object.entries(entry.seen || {})){
          const prior=typeof record==='object' && record ? record : {misses:Number(record)||0,last_day:''};
          if(current.has(id))seen[id]={misses:0,last_day:input.day};
          else if(prior.last_day===input.day)seen[id]=prior;
          else if(prior.misses<1)seen[id]={misses:prior.misses+1,last_day:input.day};
        }
        for(const id of current)seen[id]={misses:0,last_day:input.day};entry.seen=seen;
      }
      await state.storage.put('push-subscriptions',entries);return json({ok:true});
    }
    return json({error:'not_found'},404);
  });
}

export async function accountPush(request,env,userId){
  if(!env.PUSH_PUBLIC_KEY || !env.PUSH_SERVER_SECRET)return json({error:'not_configured'},503);
  if(request.method!=='POST' && request.method!=='DELETE')return json({error:'method_not_allowed'},405);
  let value;try{value=await parse(request);}catch{return json({error:'invalid_request'},400);}
  if(request.method==='POST'){
    const sub=value?.subscription;
    if(!validPushSubscription(sub))return json({error:'invalid_subscription'},400);
    const subscription={endpoint:sub.endpoint,keys:{p256dh:sub.keys.p256dh,auth:sub.keys.auth}};
    return registry(env).fetch(new Request('https://account/push-registry/subscribe',{method:'POST',body:JSON.stringify({owner:userId,subscription})}));
  }
  if(typeof value?.endpoint!=='string' || value.endpoint.length>2048)return json({error:'invalid_request'},400);
  return registry(env).fetch(new Request('https://account/push-registry/unsubscribe',{method:'POST',body:JSON.stringify({owner:userId,endpoint:value.endpoint})}));
}

async function authorized(request,secret){
  const input=request.headers.get('Authorization') || '';
  if(!secret || secret.length<32 || !input.startsWith('Bearer ') || input.length>512)return false;
  const [a,b]=await Promise.all([crypto.subtle.digest('SHA-256',encoder.encode(input.slice(7))),crypto.subtle.digest('SHA-256',encoder.encode(secret))]);
  return new Uint8Array(a).reduce((d,x,i)=>d|(x^new Uint8Array(b)[i]),0)===0;
}

export async function internalPush(request,env){
  if(!env.ACCOUNTS || !await authorized(request,env.PUSH_SERVER_SECRET))return json({error:'unauthorized'},401);
  const url=new URL(request.url),hub=registry(env);
  if(url.pathname==='/internal/push-feed' && request.method==='GET'){
    const offset=Number(url.searchParams.get('offset') || 0);
    if(!Number.isSafeInteger(offset) || offset<0 || offset>2000)return json({error:'invalid_request'},400);
    const response=await hub.fetch(new Request('https://account/push-registry/list'));
    if(!response.ok)return json({error:'unavailable'},503);
    const entries=await response.json(), page=entries.slice(offset,offset+20),favorites=new Map();
    for(const entry of page){
      if(!favorites.has(entry.owner)){
        const account=env.ACCOUNTS.get(env.ACCOUNTS.idFromName('user:'+entry.owner));
        const list=await account.fetch(new Request('https://account/favorites'));
        if(!list.ok)return json({error:'unavailable'},503);
        favorites.set(entry.owner,(await list.json()).map(m=>m.id));
      }
    }
    return json({subscriptions:page.map(e=>({id:e.id,subscription:e.subscription,seen:e.seen || {},favorites:favorites.get(e.owner)})),
                 next:offset+page.length<entries.length ? offset+page.length : null});
  }
  if(url.pathname==='/internal/push-ack' && request.method==='POST'){
    let value;try{value=await parse(request,32768);}catch{return json({error:'invalid_request'},400);}
    if(!/^[a-f0-9]{64}$/.test(value?.id || '') || (value.remove!==true && (!/^\d{4}-\d{2}-\d{2}$/.test(value.day || '') || !Array.isArray(value.current) || value.current.length>2000 || value.current.some(id=>!/^tmdb:[1-9]\d{0,9}$/.test(id)))))return json({error:'invalid_request'},400);
    return hub.fetch(new Request('https://account/push-registry/ack',{method:'POST',body:JSON.stringify({id:value.id,remove:value.remove===true,current:value.current || [],day:value.day})}));
  }
  return json({error:'not_found'},404);
}
