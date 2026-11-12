"""Publicine schedules for the two distinct Embajadores cinemas."""
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from .adapters import text
from .core import normalize
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
