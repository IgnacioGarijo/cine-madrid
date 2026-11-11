import re
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import requests
from .core import MADRID, stable_id

USER_AGENT = 'CineMadridPersonal/0.1 (+https://github.com/IgnacioGarijo/cine-madrid)'
PAZ_URL = 'https://www.cinepazmadrid.es/es/cartelera'
SOURCE_ID = 'cine-paz'

class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        self.robots = {}

    def get(self, url):
        origin = urljoin(url, '/')
        if origin not in self.robots:
            robots_url = urljoin(origin, 'robots.txt')
            r = self.session.get(robots_url, timeout=25)
            if r.status_code >= 500 or r.status_code in (401,403,429):
                raise ValueError('No se pudo comprobar robots.txt; no se continúa la lectura.')
            parser = RobotFileParser()
            parser.parse(r.text.splitlines() if r.status_code == 200 else [])
            self.robots[origin] = parser
        if not self.robots[origin].can_fetch(USER_AGENT, url):
            raise ValueError('La fuente no permite esta lectura en robots.txt.')
        time.sleep(.3)
        r = self.session.get(url, timeout=35)
        r.raise_for_status()
        return r.content.decode('utf-8', errors='replace')

def parse_day(label, today):
    if label.casefold() == 'hoy': return today
    if label.casefold() == 'mañana': return today + timedelta(days=1)
    match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{4}))?', label)
    if not match: raise ValueError('Fecha no reconocida: ' + label)
    day, month = map(int, match.group(1,2))
    year = int(match.group(3)) if match.group(3) else today.year
    result = today.replace(year=year, month=month, day=day)
    if not match.group(3) and (today-result).days > 180:
        result = result.replace(year=year+1)
    return result

def parse_paz(html, today, incidents):
    soup = BeautifulSoup(html, 'html.parser')
    labels = soup.select('.rotulo_dia[data-num]')
    if not labels: raise ValueError('La estructura de la cartelera ha cambiado: no hay fechas.')
    sessions, movies = {}, {}
    for label in labels:
        label_text = label.get_text(' ', strip=True)
        try: day = parse_day(label_text, today)
        except ValueError as exc:
            incidents.add(SOURCE_ID,'date_ambiguous', label_text,str(exc), PAZ_URL); continue
        container = soup.select_one('.cines-' + label['data-num'])
        if container is None:
            incidents.add(SOURCE_ID,'layout_changed',label_text,'Fecha publicada sin bloque de sesiones.',PAZ_URL);continue
        for block in container.select('.horarios'):
            title_tag = block.select_one('.peli b')
            detail = block.select_one('.peli a[href]')
            if not title_tag or not detail:
                incidents.add(SOURCE_ID,'layout_changed',label_text,'Sesión sin título o ficha reconocible.',PAZ_URL);continue
            title=title_tag.get_text(' ',strip=True)
            detail_url=urljoin(PAZ_URL,detail['href'])
            director=next((p.get_text(' ',strip=True)[3:] for p in block.select('.peli p') if p.get_text(' ',strip=True).startswith('de ')), '')
            duration=re.search(r'(\d+) minutos',block.get_text(' ',strip=True),re.I)
            movie_id='paz:' + re.search(r'/detalles/([^/]+)',detail_url).group(1).split('_')[0]
            movies[movie_id]=dict(id=movie_id,title=title,director=director,duration_minutes=int(duration[1]) if duration else None,source_url=detail_url)
            for link in block.select('.horas a[href]'):
                text=link.get_text(' ',strip=True)
                match=re.search(r'(\d{1,2}):(\d{2})',text)
                if not match:
                    incidents.add(SOURCE_ID,'time_ambiguous',link.get('data-ho',title),'Horario no reconocido: '+text,detail_url);continue
                hour,minute=map(int,match.groups())
                if hour>29 or minute>59:
                    incidents.add(SOURCE_ID,'time_ambiguous',title,text,detail_url);continue
                dt=datetime.combine(day,datetime.min.time(),tzinfo=MADRID)+timedelta(hours=hour,minutes=minute)
                sid='paz:'+link['data-ho'] if link.get('data-ho') else stable_id(SOURCE_ID,movie_id,dt.isoformat(),text)
                sessions[sid]=dict(id=sid,source_id=SOURCE_ID,cinema_id=SOURCE_ID,movie_id=movie_id,title=title,director=director,
                    start=dt.isoformat(),duration_minutes=movies[movie_id]['duration_minutes'],
                    version='VOSE' if 'VOSE' in (title+' '+text) else 'Sin especificar',
                    format=next((x for x in ['70mm','35mm','4K'] if x.casefold() in (title+' '+text).casefold()),None),
                    booking_url=urljoin(PAZ_URL,link['href']),source_url=detail_url,status='confirmed',stale=False,
                    category='premiere' if block.select_one('.cartel-novedad') else 'unclassified',special_tags=[])
    if not sessions: raise ValueError('No se han leído sesiones; se conserva la última lectura válida.')
    return list(sessions.values()),list(movies.values())

def event_tags(text):
    """Explicit signals only; no claim that every special event is recognized."""
    rules={'live_music':r'(?:acompañamiento|música|piano|pianista|banda sonora).{0,55}(?:en directo|en vivo)',
           'discussion':r'\bcoloquio\b', 'guests':r'con la presencia de', 'marathon':r'\bmaratón\b|programa doble'}
    return [key for key,pattern in rules.items() if re.search(pattern,text,re.I)]
