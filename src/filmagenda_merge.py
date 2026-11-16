"""Normalize FilmAgenda showtimes and merge them without replacing cinema data."""
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from .core import MADRID, normalize, clean_title
from .sources import event_tags
from .tmdb import title_variants


def valid_public_link(url, kind):
    parsed=urlparse(url or '')
    if parsed.scheme!='https' or parsed.hostname not in ('www.filmagenda.es','www.madridfilmcalendar.com') or parsed.username or parsed.password:
        return False
    return parsed.path.startswith('/pelicula/') if kind=='film' else parsed.path.startswith('/s/') and parse_qs(parsed.query).get('destination')==['film']


def directors(film):
    result=[]
    for credit in (film.get('research') or {}).get('credits') or []:
        department=normalize(str(credit.get('department') or ''));role=normalize(str(credit.get('role') or ''))
        if role in ('director','directora','codirector','codirectora') or (department in ('director','directing','direccion') and not role):
            name=str(credit.get('name') or '').strip()
            if name and name not in result:result.append(name)
    return ', '.join(result)


def convert(records, mapping, cinema_ids, today, incidents):
    """Use only manually identified venues; never turn missing film metadata into certainty."""
    if len(set(mapping.values()))!=len(mapping) or not set(mapping.values()) <= set(cinema_ids):
        raise ValueError('El mapa de cines de FilmAgenda no es válido.')
    films={}; sessions={}; invalid=0
    for record in records:
        if not isinstance(record,dict) or not isinstance(record.get('film'),dict):invalid+=1;continue
        film=record['film']; film_id=film.get('id'); title_map=film.get('title') or {}
        if not isinstance(film_id,int) or isinstance(film_id,bool) or film_id<1 or not isinstance(title_map,dict):invalid+=1;continue
        title=title_map.get('display') or title_map.get('es') or title_map.get('original')
        if not isinstance(title,str) or not title.strip() or not valid_public_link(film.get('film_url'),'film'):invalid+=1;continue
        mid='filmagenda:film:'+str(film_id);director=directors(film)
        duration=film.get('runtime_minutes');duration=duration if isinstance(duration,int) and not isinstance(duration,bool) and duration>0 else None
        movie={'id':mid,'source_id':'filmagenda','title':title.strip(),'director':director,'duration_minutes':duration,
               'source_url':film['film_url'],'source_work_id':'filmagenda:'+str(film_id),'provider':'filmagenda'}
        year=film.get('year')
        if isinstance(year,int) and not isinstance(year,bool) and 1800<=year<=2200:movie['source_year']=year
        for show in record.get('screenings') or []:
            if not isinstance(show,dict):invalid+=1;continue
            venue=show.get('theater') or {};cid=mapping.get(venue.get('id')) if isinstance(venue,dict) else None
            if not cid:continue
            native=show.get('id');raw=show.get('showtime_local','')
            try:
                if not isinstance(native,int) or isinstance(native,bool) or native<1 or show.get('film_id')!=film_id or show.get('timezone')!='Europe/Madrid':raise ValueError()
                start=datetime.strptime(raw,'%Y-%m-%dT%H:%M:%S').replace(tzinfo=MADRID)
                if not valid_public_link(show.get('screening_url'),'screening'):raise ValueError()
            except (TypeError,ValueError):invalid+=1;continue
            if start.date()<today:continue
            version={'vose':'VO','dubbed':'Doblada',None:'Sin especificar'}.get(show.get('version'),'Sin especificar')
            annotations=show.get('annotations') or []
            detail=' '.join(str(a.get(k,'')) for a in annotations if isinstance(a,dict) for k in ('tag','label_es','detail_es'))
            tags=event_tags(detail)
            sid='filmagenda:session:'+str(native)
            sessions[sid]={'id':sid,'source_id':cid,'cinema_id':cid,'movie_id':mid,'title':title.strip(),'director':director,
                'start':start.isoformat(),'duration_minutes':duration,'booking_url':show['screening_url'],
                'source_url':show['screening_url'],'version':version,'room':'','format':None,'status':'confirmed',
                'stale':False,'source_category':'unclassified','category':'unclassified','special_tags':tags,'provider':'filmagenda'}
            films[mid]=movie
    if invalid:incidents.add('filmagenda','partial_read','records',f'No se han incorporado {invalid} registros de FilmAgenda con datos incompletos o no reconocidos.','https://data.filmagenda.es/docs')
    if not sessions:raise ValueError('No hay sesiones reconocibles de los cines configurados.')
    return list(sessions.values()),list(films.values())


def title_keys(movie):
    values=[movie.get('title',''),movie.get('canonical_title',''),movie.get('original_title',''),*(movie.get('aliases') or [])]
    return {normalize(v) for value in values if isinstance(value,str) for v in title_variants(value) if len(normalize(v))>=5}


def same_film(a,b):
    if a.get('identity_status')=='verified' and b.get('identity_status')=='verified' and a.get('canonical_id') and b.get('canonical_id'):
        return a['canonical_id']==b['canonical_id']
    if not title_keys(a)&title_keys(b):return False
    ay=a.get('year') or a.get('source_year');by=b.get('year') or b.get('source_year')
    if ay and by and ay!=by:return False
    ad=normalize(a.get('director',''));bd=normalize(b.get('director',''))
    if ad and bd and ad!=bd:return False
    return True


def merge(primary, extra, movies):
    """Drop only matched same-cinema, same-time works; preserve conflicting versions."""
    by_slot=defaultdict(list);by_id={m['id']:m for m in movies}
    for session in primary:by_slot[(session['cinema_id'],session['start'])].append(session)
    added=[];duplicates=0;superseded=set()
    for session in extra:
        film=by_id.get(session['movie_id'],{});matches=[]
        for existing in by_slot[(session['cinema_id'],session['start'])]:
            old=by_id.get(existing['movie_id'],{})
            v1=existing.get('version');v2=session.get('version')
            if v1=='Doblada' and v2 in ('VO','VOSE') or v2=='Doblada' and v1 in ('VO','VOSE'):continue
            if same_film(old,film):matches.append(existing)
        if any(not x.get('stale') for x in matches):
            duplicates+=1
            continue
        superseded.update(x['id'] for x in matches)
        added.append(session)
    return [x for x in primary if x['id'] not in superseded]+added,duplicates
