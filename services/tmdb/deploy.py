"""CI deployment. Secrets are passed via environment/stdin, never source or arguments."""
import json,os,re,subprocess,sys,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[2]
CONFIG=str(ROOT/'services/tmdb/wrangler.jsonc')
for key in ['CLOUDFLARE_API_TOKEN','CLOUDFLARE_ACCOUNT_ID','TMDB_READ_TOKEN']:
    if not os.getenv(key):raise SystemExit('Falta el secreto de Actions '+key+'. Consulta docs/CLOUDFLARE.md.')

def run(arguments,input=None):
    result=subprocess.run(['npx','--yes','wrangler@4.160.1',*arguments,'--config',CONFIG],input=input,text=True,capture_output=True,cwd=ROOT)
    if result.returncode:
        # Do not log process bodies: a third-party failure must not echo a credential.
        raise SystemExit('Cloudflare no ha completado '+arguments[0]+'. Revisa la cuenta, su subdominio workers.dev y los permisos del token.')
    return result.stdout

output=run(['deploy'])
match=re.search(r'https://cine-madrid-tmdb\.[a-z0-9-]+\.workers\.dev',output)
if not match:raise SystemExit('No se reconoce la URL de despliegue; no se modifica la web.')
base=match[0]
run(['secret','put','TMDB_READ_TOKEN'],input=os.environ['TMDB_READ_TOKEN'])
for attempt in range(6):
    try:
        response=requests.get(base+'/search',params={'q':'Piratas del'},headers={'Origin':'https://ignaciogarijo.github.io'},timeout=15)
        if response.ok and isinstance(response.json().get('movies'),list):break
    except requests.RequestException:pass
    if attempt==5:raise SystemExit('El servicio no responde correctamente; no se modifica la configuración de Pages.')
    time.sleep(3)
(ROOT/'web/search-config.json').write_text(json.dumps({'tmdb_api_url':base+'/search'})+'\n',encoding='utf-8')
print('Servicio de sugerencias comprobado:',base)
