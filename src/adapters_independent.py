"""Publicine schedules for the two distinct Embajadores cinemas."""
import re
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from .adapters import text
from .core import normalize, clean_title
from .sources import parse_day, event_tags

VENUES = {
    'cines-embajadores': ('cinesembajadores', 'mariadelacabeza5'),
    'cines-embajadores-r-o': ('cinesembajadoresrio', 'ercilla53'),
}

def publicine_embajadores(reader):
    cinema = reader.cinema
    if cinema['id'] not in VENUES:
        raise ValueError('Sede de Embajadores desconocida')
    url = cinema['schedule_url']
    soup = reader.soup(url)
    address = soup.select_one('#adreca')
    name, street = VENUES[cinema['id']]
    if not address or normalize(text(address.select_one('strong'))) != name or street not in normalize(text(address)):
        raise ValueError('La fuente no identifica inequívocamente la sede')
    blocks = soup.select('.sessions')
    if not blocks:
        raise ValueError('No se reconoce la cartelera de Publicine')
    for block in blocks:
        link = block.select_one('a[href] h2')
        if not link:
            continue
        film = link.parent
        title = text(link)
        film_url = urljoin(url, film['href'])
        director = ''
        duration = None
        for label in block.select('span.up'):
            value = label.next_sibling
            value = str(value).strip() if value else ''
            if normalize(text(label)) == 'director': director = value
            if normalize(text(label)) == 'duracion':
                match = re.search(r'\d+', value)
                if match: duration = int(match[0])
        for day_node in block.select('.box_dia'):
            day_label = text(day_node)
            day_match = re.search(r'\b\d{1,2}/\d{1,2}(?:/\d{4})?\b', day_label)
            times = day_node.find_next_sibling(class_='box_projeccions')
            if not day_match or not times:
                reader.partial(title, 'Fecha o bloque de horarios no reconocible.', url)
                continue
            try: day = parse_day(day_match[0], reader.today)
            except ValueError:
                reader.partial(title, 'Fecha no reconocible.', url); continue
            for entry in times.select('.horari_pelicula'):
                raw = entry.find(string=True, recursive=False)
                match = re.fullmatch(r'\s*(\d{1,2})[.:](\d{2})\s*', str(raw or ''))
                if not match or int(match[1]) > 23 or int(match[2]) > 59:
                    reader.partial(title, 'Hora no reconocible.', url); continue
                start = datetime.combine(day, datetime.min.time()) + timedelta(hours=int(match[1]), minutes=int(match[2]))
                version = 'VOSE' if 'vose' in normalize(text(entry.select_one('.versio_pelicula'))) else 'Sin especificar'
                anchor = entry.find_parent('a')
                booking = urljoin(url, anchor.get('data-href') or anchor.get('href') or '') if anchor else url
                reader.result.add(title, start, film_url, director, duration, booking, version=version, tags=event_tags(title), work_id='publicine:'+film_url)


def reserva_embajadores(reader):
    """Official ticketing pages: one explicit date/time and booking URL per screening."""
    locations={'cines-embajadores':('cineembajadores','cineembajadores'),
               'cines-embajadores-r-o':('cineembajadoresrio','cineembajadoresrio')}
    cid=reader.cinema['id'];slug,expected=locations[cid];index=reader.cinema['schedule_url']
    soup=reader.soup(index)
    if normalize(text(soup.select_one('h1')))!=expected:
        raise ValueError('La taquilla no identifica inequívocamente la sede')
    films={}
    pattern=re.compile(r'^/(?:reservaentradas/)?sesiones/madrid/'+re.escape(slug)+r'/[^/]+/(\d+)/?$',re.I)
    for a in soup.select('a[href]'):
        target=urlparse(urljoin(index,a['href']))
        match=pattern.fullmatch(target.path)
        if target.hostname=='www.reservaentradas.com' and match:
            films[match[1]]='https://www.reservaentradas.com'+target.path.replace('/reservaentradas/','/',1)
    if not films:raise ValueError('No se reconocen las fichas de la taquilla')
    # Publicine supplements missing directors only when title and director match unambiguously.
    metadata={}
    try:
        alternative=reader.soup(reader.cinema['metadata_url'])
        address=alternative.select_one('#adreca');name,street=VENUES[cid]
        if not address or normalize(text(address.select_one('strong')))!=name or street not in normalize(text(address)):
            raise ValueError('La fuente complementaria corresponde a otra sede')
        for block in alternative.select('.sessions'):
            heading=block.select_one('a[href] h2')
            if not heading:continue
            director='';duration=None
            for label in block.select('span.up'):
                value=str(label.next_sibling or '').strip()
                if normalize(text(label))=='director':director=value
                if normalize(text(label))=='duracion':
                    duration_match=re.search(r'\d+',value)
                    if duration_match:duration=int(duration_match[0])
            if director:metadata.setdefault(normalize(clean_title(text(heading))),set()).add((director,duration))
    except Exception:
        reader.partial('metadata','No se pudo consultar la fuente complementaria de direcciones de películas.',reader.cinema['metadata_url'])
    for film_id,url in films.items():
        try:
            page=reader.soup(url)
            analytics=next((s.get_text() for s in page.select('script') if 'window.reAnalyticsSesiones =' in s.get_text()),'')
            match=re.search(r'window\.reAnalyticsSesiones\s*=\s*(\{.*?\})\s*;',analytics,re.S)
            if not match and 'nohaysesionesprogramadas' in normalize(text(page)) and not page.select('a.sesion[href]'):
                continue
            if not match:raise ValueError('No se reconocen los datos de sesiones')
            sessions=json.loads(match[1])
            if not isinstance(sessions,dict):raise ValueError('Formato de sesiones no reconocido')
            for native,record in sessions.items():
                if record.get('location_id')!=slug or not str(native).isdigit():raise ValueError('Sesión atribuida a otra sede')
                title=record.get('item_name','').strip();start=datetime.fromisoformat(record['session_datetime'])
                booking=next((a for a in page.select('a.sesion[href]') if re.search(r'/'+re.escape(str(native))+r'/?(?:\?|$)',a['href'])),None)
                if not title or booking is None:raise ValueError('Sesión sin título o enlace verificable')
                target=urlparse(urljoin(index,booking['href']))
                if target.hostname!='www.reservaentradas.com' or '/entrada/madrid/'+slug+'/' not in target.path:raise ValueError('Enlace de otra sede')
                ticket='https://www.reservaentradas.com'+target.path.replace('/reservaentradas/','/',1)
                if target.query:ticket+='?'+target.query
                candidates=metadata.get(normalize(clean_title(title)),set());director,duration=next(iter(candidates)) if len(candidates)==1 else ('',None)
                raw=record.get('item_category4','');version='VOSE' if 'vose' in normalize(raw) else 'Doblada' if 'doblada' in normalize(raw) else 'Sin especificar'
                reader.result.add(title,start,url,director,duration,ticket,version,record.get('item_category5',''),native=native,tags=event_tags(title),work_id='reserva:'+slug+':'+film_id)
        except Exception as exc:
            reader.partial(film_id,'No se pudo leer una ficha de sesiones: '+str(exc)[:160],url)
