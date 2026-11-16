"""Read the public data service used by Cine Yelmo's own website."""
import json
import re
from datetime import datetime
from urllib.parse import urlencode, urljoin

from .adapters import cinerama, minutes

SITE = 'https://cineyelmo.com/'
API = 'https://api-g.cinepolis.com/v2/billboards/graphql'
SHOWS = '''query Billboard($countryId:String!,$cinemaId:String!,$timezone:String!){
 billboardByCinema(countryId:$countryId,cinemaId:$cinemaId,timezone:$timezone){dates
 schedules{cinemaId movieId dates{date languages{language displayLanguage
 showtimes{format{name} sessionId datetime screen experience{name}}}}}}}'''
FILMS = '''query Movies($countryId:String!,$cinemas:String,$after:String,$limit:Int){
 movies(countryId:$countryId,cinemas:$cinemas,after:$after,limit:$limit){
 pageInfo{endCursor hasNextPage} totalCount edges{node{id name originalName length cast{directors{name}}}}}}'''


def query(reader, key, query_text, variables):
    payload = json.loads(reader.fetcher.post(API, json={'query':query_text, 'variables':variables},
        headers={'x-apikey':key, 'country-id':'ES', 'language':'ES'}))
    if payload.get('errors') or not isinstance(payload.get('data'), dict):
        raise ValueError('El servicio oficial no devolvió una respuesta completa.')
    if API not in reader.result.pages: reader.result.pages.append(API)
    return payload['data']


def read_official(reader):
    cinema = reader.cinema
    slug = cinema['yelmo_id']
    page = reader.soup(SITE)
    script = next((x.get('src') for x in page.select('script[src]')
                   if re.search(r'/_next/static/chunks/pages/_app-[^/]+\.js(?:\?|$)', x.get('src',''))), None)
    if not script: raise ValueError('No se reconoce la aplicación oficial de Yelmo.')
    js = reader.get(urljoin(SITE, script))
    key = re.search(r'API_KEY\s*:\s*"([^"\s]+)"', js)
    if not key: raise ValueError('No se reconoce la configuración pública del servicio oficial.')
    key = key.group(1)
    billboard = query(reader,key,SHOWS,{'countryId':'ES','cinemaId':slug,'timezone':'Europe/Madrid'}).get('billboardByCinema')
    if not isinstance(billboard,dict) or not isinstance(billboard.get('schedules'),list):
        raise ValueError('No se reconoce la cartelera oficial del cine.')
    films = {}; cursor = None
    for _ in range(10):
        listing = query(reader,key,FILMS,{'countryId':'ES','cinemas':slug,'after':cursor,'limit':100}).get('movies')
        if not isinstance(listing,dict) or not isinstance(listing.get('edges'),list):
            raise ValueError('No se reconoce el catálogo oficial del cine.')
        for edge in listing['edges']:
            film = edge.get('node') or {}
            if film.get('id') and film.get('name'): films[film['id']] = film
        info = listing.get('pageInfo') or {}
        if not info.get('hasNextPage'): break
        next_cursor = info.get('endCursor')
        if not next_cursor or next_cursor == cursor: raise ValueError('Paginación de películas incompleta.')
        cursor = next_cursor
    else: raise ValueError('El catálogo oficial supera el límite de páginas.')
    pending = []
    for schedule in billboard['schedules']:
        if schedule.get('cinemaId') != slug: raise ValueError('La sesión pertenece a otro cine.')
        film = films.get(schedule.get('movieId'))
        if not film:
            reader.partial(str(schedule.get('movieId','película')), 'La sesión oficial no tiene ficha identificable.', cinema['url'])
            continue
        directors = (film.get('cast') or {}).get('directors') or []
        director = ', '.join(d['name'].strip() for d in directors if isinstance(d,dict) and d.get('name'))
        duration = minutes(str(film.get('length') or ''))
        for day in schedule.get('dates') or []:
            for language in day.get('languages') or []:
                label = (language.get('language') or '').upper()
                version = 'VOSE' if label == 'SUB ESP' else 'Sin especificar'
                for show in language.get('showtimes') or []:
                    try:
                        start = datetime.fromisoformat(show['datetime'])
                        if start.date().isoformat() != day['date'] or not show.get('sessionId'): raise ValueError()
                    except (KeyError,TypeError,ValueError):
                        reader.partial(film['id'],'La fecha o la hora de la sesión no se puede verificar.',cinema['url'])
                        continue
                    if start.date() < reader.today: continue
                    params = urlencode({'country':'es','cinema':slug,'selected':slug,'movie':film['id'],'session':show['sessionId']})
                    fmt = (show.get('format') or {}).get('name')
                    experience = (show.get('experience') or {}).get('name')
                    pending.append((film,start,director,duration,version,show,fmt,experience,SITE+'es/asientos?'+params))
    if not pending: raise ValueError('No se han encontrado sesiones oficiales verificables.')
    for film,start,director,duration,version,show,fmt,experience,booking in pending:
        reader.result.add(film['name'],start,cinema['url'],director,duration,booking,version,
            room=str(show.get('screen') or ''),native=show['sessionId'],format=fmt if fmt and fmt!='2D' else experience,
            work_id='yelmo:'+film['id'])


def yelmo(reader):
    try:
        read_official(reader)
    except Exception:
        reader.partial('fuente_oficial','No se pudo leer la cartelera oficial de Yelmo; se utiliza Cinerama como alternativa.',reader.cinema['url'])
        original = reader.cinema
        reader.cinema = dict(original, schedule_url=original['fallback_url'])
        try: cinerama(reader)
        finally: reader.cinema = original
