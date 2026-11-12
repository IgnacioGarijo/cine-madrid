"""Lectores de carteleras comerciales con fechas explícitas."""
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from .adapters import text, minutes
from .core import normalize, stable_id


def _detail(reader, url, kind):
    try:
        soup=reader.soup(url)
    except Exception:
        reader.partial(url,'No se pudo leer la ficha oficial de la película.',url)
        return '',None,None
    director='';duration=None;year=None
    if kind=='golem':
        for label in soup.select('td.txtLectura'):
            value=label.find_next_sibling('td')
            if not value:continue
            name=normalize(text(label)); content=text(value)
            if name in ('dirigidapor','direccion','director'):director=content
            elif name=='duracion':duration=minutes(content)
            elif name in ('anodeproduccion','anodeestreno'):
                match=re.fullmatch(r'\s*((?:19|20)\d{2})\s*',content)
                if match:year=int(match[1])
    else:
        for label in soup.select('p'):
            if label.contents and isinstance(label.contents[0],str) and normalize(label.contents[0])=='director':
                director=text(label.select_one('span'));break
    return director,duration,year


def _set_year(reader,title,director,duration,year):
    if year:
        mid=reader.cinema['id']+':film:'+stable_id(normalize(title),normalize(director),duration)
        if mid in reader.result.movies:reader.result.movies[mid]['source_year']=year


def odeon(reader):
    url=reader.cinema['schedule_url']
    soup=reader.soup(url)
    cards=soup.select('div[class*="show-"]:has(.show-info)')
    if not cards:
        raise ValueError('No se reconocen las películas de Odeon')
    home=url.rsplit('/peliculas',1)[0]
    try:
        index=reader.soup(home)
        details={normalize(text(a)):urljoin(home,a['href']) for a in index.select('a[href*="/producto/"]') if text(a)}
    except Exception:
        reader.partial(home,'No se pudo leer el índice de fichas oficiales.',home);details={}
    for card in cards:
        title=text(card.select_one('.show-details h5'))
        if not title: continue
        duration=minutes(text(card.select_one('.show-details')))
        detail_url=details.get(normalize(title))
        director,detail_duration,year=_detail(reader,detail_url,'odeon') if detail_url else ('',None,None)
        duration=detail_duration or duration
        for day in card.select('div[class*="day-"]'):
            date_class=next((c for c in day.get('class',[]) if re.fullmatch(r'day-\d{4}-\d{2}-\d{2}',c)),None)
            if not date_class: continue
            for item in day.select('.item-session'):
                description=text(item)
                version='VOSE' if re.search(r'original\s+subtitulada\s+en\s+espa[ñn]ol',description,re.I) else 'Sin especificar'
                fmt=item.select_one('[data-format]')
                fmt=fmt.get('data-format','').strip() if fmt else ''
                for a in item.select('time a[href]'):
                    try: start=datetime.fromisoformat(date_class[4:]+'T'+text(a))
                    except ValueError:
                        reader.partial(title,'Hora de sesión no reconocida.',url);continue
                    booking=urljoin(url,a['href'])
                    if urlparse(booking).hostname != urlparse(url).hostname: continue
                    native=parse_qs(urlparse(booking).query).get('sesion',[None])[0]
                    reader.result.add(title,start,detail_url or url,director,duration=duration,booking=booking,version=version,format=fmt or None,native=native)
                    _set_year(reader,title,director,duration,year)


def golem(reader):
    base=reader.cinema['schedule_url'].rstrip('/')+'/'
    first=base+reader.today.strftime('%Y%m%d')
    soup=reader.soup(first)
    metadata={}
    pages={first}
    pages.update(urljoin(first,a['href']) for a in soup.select('a[href]') if re.fullmatch(r'/golem/golem-madrid/\d{8}',a['href']))
    for url in sorted(pages):
        try:
            day=datetime.strptime(url.rsplit('/',1)[-1],'%Y%m%d').date()
            page=soup if url==first else reader.soup(url)
        except Exception:
            reader.partial(url,'No se pudo leer el día de cartelera.',url);continue
        if day<reader.today:continue
        for title_node in page.select('a.txtNegXXL[href*="/golem/pelicula/"]'):
            block=title_node.find_parent('td',bgcolor='#ffffff')
            if not block:continue
            raw=text(title_node); version='VOSE' if re.search(r'V\.?\s*O\.?\s*S\.?\s*E\.?',raw,re.I) else 'Sin especificar'
            title=re.sub(r'\s*\(V\.?\s*O\.?\s*S\.?\s*E\.?\)\s*$','',raw,flags=re.I).strip()
            film_url=urljoin(url,title_node['href'])
            if film_url not in metadata:metadata[film_url]=_detail(reader,film_url,'golem')
            director,duration,year=metadata[film_url]
            for a in block.select('a.horaXXXL[href]'):
                try:start=datetime.fromisoformat(day.isoformat()+'T'+text(a))
                except ValueError:
                    reader.partial(title,'Hora de sesión no reconocida.',url);continue
                booking=urljoin(url,a['href']);native=parse_qs(urlparse(booking).query).get('perfCode',[None])[0]
                reader.result.add(title,start,film_url,director,duration,booking=booking,version=version,native=native)
                _set_year(reader,title,director,duration,year)
