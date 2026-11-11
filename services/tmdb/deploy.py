"""CI deployment. Secrets are passed via environment/stdin, never source or arguments."""
import json,os,re,subprocess,sys,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[2]
CONFIG=str(ROOT/'services/tmdb/wrangler.jsonc')
SECRET_NAMES = ('CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'TMDB_READ_TOKEN', 'FAVORITES_OWNER_SECRET')

def safe_diagnostic(message):
    """Keep actionable CLI errors while masking credentials before logging."""
    message = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', message)
    for key in SECRET_NAMES:
        value = os.getenv(key)
        if value:
            message = message.replace(value, '[oculto]')
    message = re.sub(r'(?i)(bearer\s+)[\w.\-]+', r'\1[oculto]', message)
    return message[-6000:]

def run(arguments,input=None):
    result=subprocess.run(['npx','--yes','wrangler@4.160.1',*arguments,'--config',CONFIG],input=input,text=True,capture_output=True,cwd=ROOT)
    if result.returncode:
        raise SystemExit('Cloudflare no ha completado '+arguments[0]+':\n'+safe_diagnostic(result.stdout+'\n'+result.stderr))
    return result.stdout

def diagnose_access():
    """Report access checks, never account names, identifiers or token contents."""
    headers = {'Authorization': 'Bearer '+os.environ['CLOUDFLARE_API_TOKEN']}
    account = os.environ['CLOUDFLARE_ACCOUNT_ID']
    print('Formato del identificador de cuenta:', 'correcto' if re.fullmatch(r'[a-f0-9]{32}', account) else 'incorrecto', flush=True)
    for label, path in [('Cuentas accesibles', '/accounts?per_page=50'),
                        ('Acceso a Workers', '/accounts/'+account+'/workers/scripts')]:
        try:
            response = requests.get('https://api.cloudflare.com/client/v4'+path, headers=headers, timeout=15)
            body = response.json()
            print(label+': HTTP '+str(response.status_code), flush=True)
            if label == 'Cuentas accesibles' and body.get('success'):
                accounts = body.get('result', [])
                print('La cuenta configurada figura en las cuentas accesibles:', any(item.get('id') == account for item in accounts), flush=True)
            for error in body.get('errors', []):
                print(safe_diagnostic(str(error.get('code'))+': '+str(error.get('message'))), flush=True)
        except (requests.RequestException, ValueError):
            print(label+': no se pudo completar la comprobación.', flush=True)

def main():
    for key in SECRET_NAMES[:3]:
        if not os.getenv(key):raise SystemExit('Falta el secreto de Actions '+key+'. Consulta docs/CLOUDFLARE.md.')
    public_favorites=json.loads(Path(CONFIG).read_text(encoding='utf-8')).get('vars',{}).get('PUBLIC_FAVORITES')=='true'
    if not public_favorites and not os.getenv('FAVORITES_OWNER_SECRET'):raise SystemExit('Falta el secreto FAVORITES_OWNER_SECRET para el acceso privado.')
    try:
        output=run(['deploy'])
    except SystemExit:
        diagnose_access()
        raise
    match=re.search(r'https://cine-madrid-tmdb\.[a-z0-9-]+\.workers\.dev',output)
    if not match:raise SystemExit('No se reconoce la URL de despliegue; no se modifica la web.')
    base=match[0]
    run(['secret','put','TMDB_READ_TOKEN'],input=os.environ['TMDB_READ_TOKEN'])
    if os.getenv('FAVORITES_OWNER_SECRET'):
        run(['secret','put','FAVORITES_OWNER_SECRET'],input=os.environ['FAVORITES_OWNER_SECRET'])
    for attempt in range(6):
        try:
            response=requests.get(base+'/search',params={'q':'Piratas del'},headers={'Origin':'https://ignaciogarijo.github.io'},timeout=15)
            if response.ok and isinstance(response.json().get('movies'),list):break
        except requests.RequestException:pass
        if attempt==5:raise SystemExit('El servicio no responde correctamente; no se modifica la configuración de Pages.')
        time.sleep(3)
    if not public_favorites:
        for attempt in range(6):
            try:
                response=requests.post(base+'/session',json={'secret':os.environ['FAVORITES_OWNER_SECRET']},headers={'Origin':'https://ignaciogarijo.github.io'},timeout=15)
                if response.ok and response.json().get('token'):break
                status=response.status_code
            except (requests.RequestException,ValueError):status='sin respuesta'
            if attempt==5:raise SystemExit('No se pudo verificar el acceso de edición (HTTP '+str(status)+'); no se modifica Pages.')
            time.sleep(5)
    response=requests.get(base+'/favorites',timeout=15)
    if not response.ok or not isinstance(response.json(),list):raise SystemExit('No se pudo comprobar la lista compartida; no se modifica Pages.')
    (ROOT/'web/search-config.json').write_text(json.dumps({'tmdb_api_url':base+'/search','favorites_api_url':base+'/favorites','public_favorites':public_favorites})+'\n',encoding='utf-8')
    print('Servicio de sugerencias comprobado:',base)

if __name__ == '__main__':
    main()
