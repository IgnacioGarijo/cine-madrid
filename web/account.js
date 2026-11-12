// Vendored official Supabase SDK, pinned to 2.119.0 (MIT).
export async function createAccount(config){
  if(!window.supabase){
    await new Promise((resolve,reject)=>{
      const script=document.createElement('script');script.src='./vendor/supabase-2.119.0.js';
      script.onload=resolve;script.onerror=reject;document.head.append(script);
    });
  }
  return window.supabase.createClient(config.supabase_url,config.supabase_publishable_key,{
    auth:{flowType:'pkce',persistSession:true,autoRefreshToken:true,detectSessionInUrl:true,storageKey:'cm-account-session'}
  });
}
