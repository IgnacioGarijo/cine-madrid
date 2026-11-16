"""Download FilmAgenda's documented partner snapshot without exposing its credential."""
import gzip
import hashlib
import io
import json
import os
import re
from collections import Counter
from datetime import date
from urllib.parse import urlparse

import requests

BASE = 'https://data.filmagenda.es'
DATASET = 'upcoming-films.ndjson.gz'
MAX_COMPRESSED = 50 * 1024 * 1024
MAX_UNCOMPRESSED = 250 * 1024 * 1024


class FilmAgendaError(RuntimeError):
    """A safe diagnostic that never includes a credential or signed URL."""


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _auth_get(session, url, token):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'data.filmagenda.es' or parsed.username or parsed.password:
        raise FilmAgendaError('La dirección de la API no es válida.')
    try:
        response = session.get(url, headers={'Authorization':'Bearer '+token}, timeout=45, allow_redirects=False)
    except requests.RequestException:
        raise FilmAgendaError('No se pudo contactar con la API de FilmAgenda.') from None
    if response.status_code in (401, 403): raise FilmAgendaError('La credencial de FilmAgenda no se ha aceptado.')
    return response


def download(token, session=None):
    """Return pointer, license metadata and records after verifying both SHA-256 hashes."""
    if not token: raise FilmAgendaError('Falta la credencial de FilmAgenda.')
    session = session or requests.Session()
    pointer_response = _auth_get(session, BASE+'/v1/current.json', token)
    if pointer_response.status_code != 200: raise FilmAgendaError('No se pudo obtener la versión publicada.')
    try: pointer = pointer_response.json()
    except ValueError: raise FilmAgendaError('La versión publicada no es JSON válido.') from None
    version = pointer.get('snapshot_version','')
    if pointer.get('api_version') != 'v1' or not isinstance(version,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',version):
        raise FilmAgendaError('La versión publicada tiene un formato desconocido.')
    manifest_url = pointer.get('manifest_url')
    expected_manifest = BASE+'/v1/snapshots/'+version+'/manifest.json'
    if manifest_url != expected_manifest: raise FilmAgendaError('La dirección del manifiesto no corresponde a la versión publicada.')
    manifest_response = _auth_get(session, manifest_url, token)
    if manifest_response.status_code != 200: raise FilmAgendaError('No se pudo obtener el manifiesto.')
    if _digest(manifest_response.content) != pointer.get('manifest_sha256'): raise FilmAgendaError('El manifiesto no supera la comprobación de integridad.')
    try: manifest = json.loads(manifest_response.content)
    except (ValueError,UnicodeDecodeError): raise FilmAgendaError('El manifiesto no es JSON válido.') from None
    if manifest.get('api_version') != 'v1' or manifest.get('snapshot_version') != version:
        raise FilmAgendaError('La versión del manifiesto no coincide.')
    files = [f for f in manifest.get('files',[]) if isinstance(f,dict) and f.get('path') == DATASET]
    if len(files) != 1 or not re.fullmatch(r'[a-f0-9]{64}',str(files[0].get('sha256',''))):
        raise FilmAgendaError('El manifiesto no identifica inequívocamente el archivo de Madrid.')
    license_info = manifest.get('license') or {}
    if not isinstance(license_info.get('attribution'),str) or not license_info['attribution'].strip():
        raise FilmAgendaError('El manifiesto no contiene la atribución necesaria.')
    payload_url = BASE+'/v1/snapshots/'+version+'/'+DATASET
    redirect = _auth_get(session, payload_url, token)
    if redirect.status_code not in (302,303,307,308): raise FilmAgendaError('No se recibió el enlace temporal de descarga.')
    location = redirect.headers.get('Location',''); parsed = urlparse(location)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.hostname in ('localhost','data.filmagenda.es'):
        raise FilmAgendaError('El enlace temporal de descarga no es válido.')
    # A separate request without Authorization: the signed URL is not logged.
    try:
        response = requests.get(location, timeout=90, allow_redirects=False, stream=True)
        if response.status_code != 200: raise FilmAgendaError('No se pudo descargar el archivo publicado.')
        chunks=[]; size=0
        for chunk in response.iter_content(1024*1024):
            size += len(chunk)
            if size > MAX_COMPRESSED: raise FilmAgendaError('El archivo publicado supera el límite de tamaño.')
            chunks.append(chunk)
        payload = b''.join(chunks)
    except requests.RequestException:
        raise FilmAgendaError('No se pudo descargar el archivo publicado.') from None
    if _digest(payload) != files[0]['sha256']: raise FilmAgendaError('El archivo de cartelera no supera la comprobación de integridad.')
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as zipped: raw=zipped.read(MAX_UNCOMPRESSED+1)
        if len(raw)>MAX_UNCOMPRESSED: raise FilmAgendaError('La cartelera supera el límite de tamaño.')
        records=[json.loads(line) for line in raw.decode('utf8').splitlines() if line.strip()]
    except (OSError,UnicodeDecodeError,ValueError):
        raise FilmAgendaError('No se pudo interpretar el archivo de cartelera.') from None
    expected=(manifest.get('datasets') or {}).get('upcoming_films') or {}
    if not records or len(records) != expected.get('record_count'):
        raise FilmAgendaError('El número de películas no coincide con el manifiesto.')
    if sum(len(x.get('screenings',[])) for x in records if isinstance(x,dict)) != expected.get('screening_count'):
        raise FilmAgendaError('El número de sesiones no coincide con el manifiesto.')
    return pointer,manifest,records


def audit(pointer, manifest, records, today=None):
    """Summarize the actual snapshot, without dumping records or credentials."""
    today = today or date.today()
    months=Counter(); venues=Counter(); future=[]
    for record in records:
        film=record.get('film') or {}; title=(film.get('title') or {}).get('display') or (film.get('title') or {}).get('es') or (film.get('title') or {}).get('original') or ''
        for screening in record.get('screenings') or []:
            day=str(screening.get('showtime_local',''))[:10]
            try: parsed=date.fromisoformat(day)
            except ValueError: continue
            if parsed<today: continue
            theater=screening.get('theater') or {}
            months[day[:7]]+=1; venues[(theater.get('id',''),theater.get('name',''))]+=1
            future.append((day,title,theater.get('name','')))
    lines=['Versión: '+str(pointer.get('snapshot_version')),
           'Publicada: '+str(pointer.get('published_at')),
           'Generada: '+str(manifest.get('generated_at')),
           'Atribución: '+manifest['license']['attribution'],
           'Películas: '+str(len(records)), 'Sesiones futuras: '+str(len(future))]
    lines.extend('Mes '+month+': '+str(count) for month,count in sorted(months.items()))
    lines.extend('Sala '+str(venue_id)+' | '+str(name)+' | '+str(count) for (venue_id,name),count in sorted(venues.items()))
    lines.extend('Pase lejano '+day+' | '+title+' | '+name for day,title,name in sorted(future,reverse=True)[:15])
    for record in records:
        film=record.get('film') or {}; titles=film.get('title') or {}
        title=titles.get('display') or titles.get('es') or titles.get('original') or ''
        if title.casefold() not in ('iron boy','muerte entre las flores','la bola negra'): continue
        directors=[c for c in (film.get('research') or {}).get('credits',[]) if 'direct' in str(c.get('department','')).casefold() or 'director' in str(c.get('role','')).casefold()]
        example=next((s for s in record.get('screenings',[]) if 'embajadores' in str((s.get('theater') or {}).get('id',''))),None)
        lines.append('Ejemplo '+json.dumps({'film_id':film.get('id'),'title':titles,'year':film.get('year'),'tmdb_id':film.get('tmdb_id'),'directors':directors[:2],'screening':example},ensure_ascii=False))
    return '\n'.join(lines)


if __name__ == '__main__':
    try:
        pointer, manifest, records = download(os.getenv('FILMAGENDA_API_KEY',''))
        print(audit(pointer, manifest, records))
    except FilmAgendaError as exc:
        raise SystemExit(str(exc)) from None
