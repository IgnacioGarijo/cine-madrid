"""Cinema-specific adapters. Every date and booking link comes from an official public source."""
import html as html_module
import json
import re
from datetime import date,datetime,timedelta
from urllib.parse import urljoin,urlparse,parse_qs
from bs4 import BeautifulSoup
from .core import MADRID,stable_id,normalize
from .sources import Fetcher,parse_paz,parse_day,event_tags,classic_members,CLASSIC_URL

MONTHS={normalize(name):index for index,name in enumerate(['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'],1)}
MONTHS.update({name[:3]:number for name,number in list(MONTHS.items())})

def text(node):return node.get_text(' ',strip=True) if node else ''
def minutes(value):
    match=re.search(r'(\d+)\s*(?:min|[\'’])',value,re.I)
    return int(match[1]) if match else None

def spanish_day(label,today,month=None):
    match=re.search(r'(\d{1,2})\s+([A-Za-zÁÉÍÓÚáéíóú]+)',label)
    if match:
        day=int(match[1]);month=MONTHS.get(normalize(match[2]))
    else:
        match=re.search(r'\d{1,2}',label)
        if not match or not month:raise ValueError('Fecha de programación no reconocida')
        day=int(match[0])
    if not month:raise ValueError('Mes no reconocido')
    value=date(today.year,month,day)
    return value.replace(year=today.year+1) if (today-value).days>180 else value

def json_nodes(soup):
    def walk(value):
        if isinstance(value,list):
            for item in value:yield from walk(item)
        elif isinstance(value,dict):
            yield value
            if '@graph' in value:yield from walk(value['@graph'])
    for script in soup.select('script[type="application/ld+json"]'):
        try:yield from walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):continue

class Result:
    def __init__(self,cinema,today):
        self.cinema=cinema;self.today=today;self.sessions={};self.movies={};self.pages=[]
    def add(self,title,start,url,director='',duration=None,booking=None,version=None,room='',native=None,category='unclassified',tags=None):
        if isinstance(start,str):start=datetime.fromisoformat(start.replace('Z','+00:00'))
        if start.tzinfo is None:start=start.replace(tzinfo=MADRID)
        start=start.astimezone(MADRID)
        if start.date()<self.today:return
        title=html_module.unescape(title).strip()
        if not title or re.search(r'\bpase\s+privado\b',title,re.I):return
        cid=self.cinema['id'];mid=cid+':film:'+stable_id(normalize(title),normalize(director),duration)
        if version is None:
            version='VOSE' if re.search(r'V\.?\s*O\.?\s*S\.?\s*E\.?|subtitulad[ao].*castellano',title,re.I) else 'Doblada' if re.search(r'doblad[ao]',title,re.I) else 'Sin especificar'
        movie=dict(id=mid,source_id=cid,title=title,director=director.strip(),duration_minutes=duration,source_url=url)
        self.movies[mid]=movie
        sid=cid+':session:'+str(native or stable_id(mid,start.isoformat(),room,version))
        self.sessions[sid]=dict(id=sid,source_id=cid,cinema_id=cid,movie_id=mid,title=title,director=director.strip(),
            start=start.isoformat(),duration_minutes=duration,booking_url=booking or url,source_url=url,version=version,room=room,
            format=None,status='confirmed',stale=False,source_category=category,category=category,special_tags=tags or [])
    def finish(self):
        return list(self.sessions.values()),list(self.movies.values())

class Reader:
    def __init__(self,cinema,today,incidents):
        self.cinema=cinema;self.today=today;self.incidents=incidents;self.fetcher=Fetcher();self.result=Result(cinema,today);self.memo={}
    def get(self,url):
        if url not in self.memo:
            self.memo[url]=self.fetcher.get(url);self.result.pages.append(url)
        return self.memo[url]
    def soup(self,url):return BeautifulSoup(self.get(url),'html.parser')
    def partial(self,entity,message,url):
        self.incidents.add(self.cinema['id'],'partial_read',entity,message,url)

def mk2(reader):
    c=reader.cinema
    sessions,movies=parse_paz(reader.get(c['url']),reader.today,reader.incidents,source_id=c['id'],source_url=c['url'],id_prefix='paz' if c['id']=='cine-paz' else 'hielo')
    if c['id']=='cine-paz':
        try:
            ids=classic_members(reader.get(CLASSIC_URL))
            for movie in movies:
                if movie['id'] in ids:movie.update(category='repertory',category_evidence_url=CLASSIC_URL)
        except Exception:reader.partial('classic','No se pudo actualizar la pertenencia al ciclo Classic.',CLASSIC_URL)
    reader.result.sessions={s['id']:s for s in sessions if s['start'][:10]>=reader.today.isoformat()}
    reader.result.movies={m['id']:dict(m,source_id=c['id']) for m in movies}

def renoir(reader):
    c=reader.cinema;first=reader.soup(c['url'])
    options=first.select('#elige-dia option[value]')
    if not options:raise ValueError('No se reconoce el selector de fechas de Renoir')
    for option in options:
        if not option.get('value'):continue
        url=urljoin(c['url'],option['value']);day=date.fromisoformat(parse_qs(urlparse(url).query)['fecha'][0])
        if day<reader.today:continue
        try:soup=first if option.has_attr('disabled') else reader.soup(url)
        except Exception:reader.partial(day.isoformat(),'No se pudo leer este día de cartelera.',url);continue
        for a in soup.select('a[href*="pillalas.com/pase/"]'):
            time_match=re.search(r'\b(\d{1,2}):(\d{2})\b',text(a))
            if not time_match:continue
            row=next((parent for parent in a.parents if parent.select_one('a[href^="/pelicula/"]')),None)
            if row is None:continue
            film=row.select_one('a[href^="/pelicula/"]');description=text(row)
            director=next((text(n).strip()[3:].strip() for n in row.select('small') if text(n).strip().startswith('de ')),'')
            version='VOSE' if 'Original subtitulada a Castellano' in description else 'Sin especificar'
            room_node=a.find_parent(class_='pase-cartelera')
            room_match=re.search(r'sala\s+(\S+)',text(room_node),re.I)
            reader.result.add(text(film),datetime.combine(day,datetime.min.time())+timedelta(hours=int(time_match[1]),minutes=int(time_match[2])),
                urljoin(url,film['href']),director,minutes(description),a['href'],version,room_match[1] if room_match else '',native=a['href'].rstrip('/').split('/')[-1],tags=event_tags(text(film)))

def verdi(reader):
    c=reader.cinema;origin=urljoin(c['url'],'/')
    theaters=json.loads(reader.get(urljoin(origin,'api/get-theaters')))['result']
    madrid=[t for t in theaters if normalize(t.get('location',''))=='madrid']
    if len(madrid)!=1:raise ValueError('No se identifica inequívocamente el recinto Verdi Madrid')
    theater=madrid[0];events=json.loads(reader.get(urljoin(origin,'api/get-events')))['result']
    for event in events:
        title=event.get('locale_title') or event.get('title') or event.get('name')
        if not title:continue
        director=', '.join(d[1] if isinstance(d,list) else str(d) for d in event.get('directors',[]))
        duration=event.get('duration') or event.get('runtime')
        try:duration=int(duration) if duration else None
        except (ValueError,TypeError):duration=None
        for session in event.get('performances',[]):
            if session.get('theater_id') and session['theater_id']!=theater['id']:continue
            raw=str(session.get('time',''))
            start=datetime.strptime(raw,'%Y%m%d%H%M') if re.fullmatch(r'\d{12}',raw) else datetime.fromisoformat(raw)
            code=session.get('code') or session.get('performance_code')
            booking=theater['shop_url'].replace('%s',str(code),1)
            reader.result.add(title,start,c['url'],director,duration,booking,native=code,room=str(session.get('screen_name','')))

def cba(reader):
    c=reader.cinema;soup=reader.soup(c['url']);blocks=soup.select('.cba_cine_table_container')
    if not blocks:raise ValueError('No se reconoce la agenda de Cine Estudio')
    for block in blocks:
        day=spanish_day(text(block.select_one('.cba_cine_table_dia')),reader.today)
        container=block.select_one('.cba_cine_sesiones_container')
        if not container:continue
        for hour in container.select('.cba_cine_table_hora'):
            title_node=hour.find_next_sibling(class_='cba_cine_table_titulo')
            if title_node is None:continue
            link=title_node.select_one('a[href]')
            if link is None:continue
            title=text(link);director=text(title_node).removeprefix(title).strip()
            type_node=title_node.find_next_sibling(class_='cba_cine_table_tipo')
            info_node=title_node.find_next_sibling(class_='cba_cine_table_info')
            time_match=re.search(r'(\d{1,2}):(\d{2})',text(hour))
            if not time_match:continue
            start=datetime.combine(day,datetime.min.time())+timedelta(hours=int(time_match[1]),minutes=int(time_match[2]))
            reader.result.add(title,start,link['href'],director,tags=event_tags(text(info_node)),category='premiere' if text(type_node)=='Estreno' else 'unclassified')

def artistic(reader):
    c=reader.cinema;soup=reader.soup(c['url'])
    events=[e for e in json_nodes(soup) if e.get('@type')=='Event' and e.get('startDate') and '/sesion/' in e.get('url','')]
    if not events:raise ValueError('No se reconocen las sesiones estructuradas de Artistic Metropol')
    for event in events:
        original=event['name']
        if re.search(r'\b(?:PRIVADO|ESTUDIOS DE CINE)\b',original,re.I):continue
        title=re.sub(r'^SALA\s*\d+\s*:\s*','',original,flags=re.I)
        room=re.search(r'^SALA\s*(\d+)',original,re.I)
        # Preserve a source-supplied year as corroborating identity evidence.
        title=re.sub(r'(?<=\))\s*(?:V\.?O\.?S\.?E\.?|Doblada al español|Muda con intert[ií]tulos.*).*$','',title,flags=re.I).strip()
        version='VOSE' if re.search(r'V\.?O\.?S\.?E',original,re.I) else 'Doblada' if 'doblada' in original.casefold() else 'Sin especificar'
        reader.result.add(title,event['startDate'],event['url'],version=version,room=room[1] if room else '',native=event['url'].rstrip('/').split('/')[-1],tags=event_tags(original))

def cineteca(reader):
    c=reader.cinema;agenda=c['url']+'?to='+reader.today.isoformat();first=reader.soup(agenda);pages={agenda}
    pages.update(urljoin(c['url'],a['href']) for a in first.select('.pager a[href]'))
    if len(pages)>8:reader.partial('pagination','La programación publica más páginas de las que se han leído.',c['url'])
    urls=set()
    for url in sorted(pages)[:8]:
        try:soup=first if url==agenda else reader.soup(url)
        except Exception:reader.partial(url,'No se pudo leer una página de programación.',url);continue
        urls.update(urljoin(c['url'],a['href']) for a in soup.select('.node--type-activity .field-name-node-title a[href]'))
    if not urls:raise ValueError('No se reconocen fichas de programación de Cineteca')
    for url in sorted(urls):
        try:soup=reader.soup(url)
        except Exception:reader.partial(url,'No se pudo leer la ficha y sus pases.',url);continue
        section=soup.select_one('.sb-sessions')
        if section is None:continue
        title=text(soup.select_one('.field-name-node-title h1,.field-name-node-title h2,h1'))
        if not title:
            meta=soup.select_one('meta[property="og:title"]');title=meta.get('content','').split(' | ')[0] if meta else ''
        director=text(soup.select_one('.field--name-field-director,.field-name-field-director'))
        duration=minutes(text(soup.select_one('.field-name-field-duration')))
        buy=next((a['href'] for a in soup.select('a[href]') if 'Comprar entradas' in text(a)),url)
        month=None;day=None
        for node in section.select('.sb-sessions__date-month,.sb-sessions__date-day,.sb-sessions__date-hours'):
            classes=node.get('class',[])
            if 'sb-sessions__date-month' in classes:month=MONTHS.get(normalize(text(node)))
            elif 'sb-sessions__date-day' in classes:day=spanish_day(text(node),reader.today,month)
            elif day:
                for time_node in node.select('.sb-sessions__date-hours-hour'):
                    match=re.search(r'(\d{1,2}):(\d{2})',text(time_node))
                    if not match:continue
                    start=datetime.combine(day,datetime.min.time())+timedelta(hours=int(match[1]),minutes=int(match[2]))
                    reader.result.add(title,start,url,director,duration,buy,room=text(node.select_one('.sb-sessions__date-hours-space')))

def capitol(reader):
    c=reader.cinema;first=reader.soup(c['url'])
    urls={urljoin(c['url'],a['href']) for a in first.select('a[href*="/es/cartelera/"]') if a['href'].rstrip('/').split('/')[-1]!='cartelera'}
    if not urls:raise ValueError('No se reconocen películas en la cartelera de Capitol')
    for url in sorted(urls):
        try:soup=reader.soup(url)
        except Exception:reader.partial(url,'No se pudo leer una ficha con sus horarios.',url);continue
        title=text(soup.select_one('h1'));director=''
        for label in soup.select('.item small'):
            if text(label)=='Director':director=text(label.find_next_sibling('span'))
        # Only explicit session tabs; the date range in the heading is not a daily schedule.
        duration=minutes(text(soup.select_one('.panel_fichacine')) or text(soup))
        for block in soup.select('.m-section[data-tabs]'):
            raw=block['data-tabs']
            if not re.fullmatch(r'\d{8}',raw):continue
            day=datetime.strptime(raw,'%Y%m%d').date()
            for a in block.select('a[href*="perfCode="]'):
                match=re.search(r'(\d{1,2}):(\d{2})',text(a))
                if not match:continue
                start=datetime.combine(day,datetime.min.time())+timedelta(hours=int(match[1]),minutes=int(match[2]))
                reader.result.add(title,start,url,director,duration,a['href'],native=parse_qs(urlparse(a['href']).query)['perfCode'][0])

def morasol(reader):
    c=reader.cinema;page=reader.get(c['url']);soup=BeautifulSoup(page,'html.parser');records={}
    for match in re.finditer(r"addToJSON\('s',\s*",page):
        payload=json.JSONDecoder().raw_decode(page[match.end():])[0];records.update(payload)
    if not records:raise ValueError('No se reconocen las sesiones de Morasol')
    # Today's film cards supplement the source's explicit dated sessions, including advance events.
    films={}
    for card in soup.select('.ficha-pelicula'):
        title=text(card.select_one('.titulo-ficha'));url=card.select_one('.img-ficha a[href]')
        duration=text(card.select_one('.info-durac'))
        films[normalize(title)]=(urljoin(c['url'],url['href']) if url else c['url'],int(duration) if duration.isdigit() else None)
    for session in records.values():
        if session.get('PasePrivado'):continue
        title=session['NombreEvento'];url,duration=films.get(normalize(title),(c['url'],None))
        # FechaSesion may append a tariff footnote, e.g. '11/11/2026 (*6)'.
        day=parse_day(session['FechaSesion'],reader.today)
        time_match=re.fullmatch(r'\s*(\d{1,2}):(\d{2})\s*',session.get('Horatxt') or session['Hora'])
        if not time_match:
            reader.partial(str(session['Id']),'Hora de sesión no reconocida.',url);continue
        start=datetime.combine(day,datetime.min.time())+timedelta(hours=int(time_match[1]),minutes=int(time_match[2]))
        # The official ficha opens the correct sale flow; no guessed purchase URL.
        reader.result.add(title,start,url,duration=duration,room=str(session.get('Sala','')),native=session['Id'],tags=event_tags(session.get('InfoAdicional','')))

ADAPTERS={'mk2':mk2,'renoir':renoir,'verdi':verdi,'cba':cba,'artistic':artistic,'cineteca':cineteca,'capitol':capitol,'morasol':morasol}

def read_cinema(cinema,today,incidents):
    reader=Reader(cinema,today,incidents)
    ADAPTERS[cinema['adapter']](reader)
    sessions,movies=reader.result.finish()
    if not sessions:raise ValueError('No se han leído sesiones futuras verificables; se conserva la última lectura válida')
    return sessions,movies,reader.result.pages
