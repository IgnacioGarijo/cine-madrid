"""TMDB enrichment, with identity evidence, caching and explicit classification rules."""
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
import requests
from .core import normalize, stable_id, now

class TMDBError(RuntimeError):
    """Safe error: never includes a credential, request or response body."""

def title_variants(title):
    cleaned = re.sub(r'\b(?:VOSE|VOSC|VOS|DOBLADA|35\s*mm|70\s*mm|DIGITAL|4K|3D)\b', ' ', title, flags=re.I)
    cleaned = re.sub(r'\(\s*\)', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -:')
    variants = [cleaned]
    without_cycle = re.sub(r'\s*\[[^\]]*\]\s*',' ',cleaned).strip()
    if without_cycle != cleaned:variants.append(without_cycle)
    event_free = re.sub(r'\b(?:live\s+by|con\s+acompañamiento\s+de|con\s+música\s+(?:de|en\s+directo))\b.*$', '',cleaned,flags=re.I).strip()
    if event_free != cleaned: variants.append(event_free)
    if ':' in cleaned:
        variants.append(cleaned.split(':',1)[1].strip())
    variants += re.findall(r'\(([^)]+)\)', cleaned)
    if '(' in cleaned:
        variants.append(cleaned.split('(',1)[0].strip())
    for value in list(variants):
        without_year = re.sub(r'\b(?:19|20)\d{2}\b','',value).strip(' -()')
        if without_year != value: variants.append(without_year)
    return list(dict.fromkeys(v for v in variants if len(normalize(v)) >= 2))

def title_score(source, movie):
    variants = [normalize(t) for t in title_variants(source['title'])]
    aliases = {normalize(t) for t in [movie['title'],movie.get('original_title',''),*movie.get('aliases',[])] if t}
    if any(value in aliases for value in variants): return 5
    if any(len(alias)>=8 and alias in value for value in variants for alias in aliases): return 3
    # A cinema may abbreviate a longer official title. It still needs director AND runtime corroboration.
    if any(len(value)>=10 and value in alias for value in variants for alias in aliases): return 2
    similarity = max((SequenceMatcher(None,value,alias).ratio() for value in variants for alias in aliases),default=0)
    return 2 if similarity >= .92 else 0

def director_matches(source, movie):
    # Some venues write 'Kurosawa, Akira' or credit several directors together.
    tokens=lambda value:set(re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',value.casefold()).encode('ascii','ignore').decode()))
    credited=tokens(source.get('director',''))
    names=[tokens(d) for d in movie.get('directors',[])]
    return bool(credited and names and (credited in names or credited==set().union(*names)))


def identity_match(source, candidates):
    """Require independent evidence: director, or exact title and an explicit film year."""
    director = normalize(source.get('director',''))
    accepted = []
    years = {int(y) for y in re.findall(r'\b((?:19|20)\d{2})\b',source['title'])}
    if source.get('source_year'):years.add(int(source['source_year']))
    if not director and len(years)!=1:return None, 'missing_director'
    for movie in candidates:
        if director and not director_matches(source,movie): continue
        if years and movie.get('year') not in years: continue
        score = title_score(source,movie)
        if not director and score!=5:continue
        if not score: continue
        duration = source.get('duration_minutes'); runtime = movie.get('runtime')
        gap = abs(duration-runtime) if duration and runtime else None
        # A typo needs an independent duration check. Exact title + director are stronger evidence.
        if score == 2 and (gap is None or gap>10): continue
        accepted.append((score, gap, movie))
    if not accepted: return None, 'metadata_mismatch'
    best = max(item[0] for item in accepted)
    accepted = [item for item in accepted if item[0]==best]
    if len(accepted)>1:
        close = [item for item in accepted if item[1] is not None and item[1]<=10]
        if len(close)==1: accepted=close
    if len(accepted)!=1: return None, 'ambiguous'
    score,gap,movie=accepted[0]
    return movie, {'title_match':'exact_or_alias' if score==5 else 'combined_titles' if score==3 else 'minor_typo',
                   'director':source.get('director',''), 'explicit_year':next(iter(years)) if len(years)==1 else None, 'duration_difference_minutes':gap,
                   'tmdb_url':movie['source_url']}

def classify(movie, session_day, source_category, config):
    """Only commercial theatrical dates count; a festival première is not enough."""
    theatrical = [date.fromisoformat(r['date']) for r in movie.get('releases',[])
                  if r['type'] in (2,3) and r.get('date') and r['date']<=session_day.isoformat()]
    earliest = min(theatrical) if theatrical else None
    if earliest and (session_day-earliest).days>=config['repertory_min_days']:
        return 'repertory', {'rule':'prior_commercial_theatrical_release','first_theatrical_date':earliest.isoformat(),
                             'minimum_days':config['repertory_min_days'],'tmdb_url':movie['source_url']}
    if source_category=='repertory':
        return 'repertory', {'rule':'cinema_classic_programme'}
    if source_category=='premiere':
        return 'premiere', {'rule':'cinema_premiere_label','first_theatrical_date':earliest.isoformat() if earliest else None}
    # An identifiable work in its initial release window stays in current releases.
    if earliest and 0<=(session_day-earliest).days<=config['current_release_max_days']:
        return 'premiere', {'rule':'initial_theatrical_release_window','first_theatrical_date':earliest.isoformat(),
                            'maximum_days':config['current_release_max_days'],'tmdb_url':movie['source_url']}
    return 'unclassified', {'rule':'release_context_needs_review','first_theatrical_date':earliest.isoformat() if earliest else None}

def slim_movie(payload):
    releases=[]
    for country in payload.get('release_dates',{}).get('results',[]):
        for release in country.get('release_dates',[]):
            value=release.get('release_date','')[:10]
            try: date.fromisoformat(value)
            except ValueError: continue
            releases.append({'country':country['iso_3166_1'],'type':release['type'],'date':value})
    directors=[c['name'] for c in payload.get('credits',{}).get('crew',[]) if c.get('job')=='Director']
    return dict(id='tmdb:'+str(payload['id']),tmdb_id=payload['id'],title=payload.get('title') or payload['original_title'],
                original_title=payload.get('original_title',''),year=int(payload['release_date'][:4]) if payload.get('release_date') else None,
                director=', '.join(directors),directors=directors,runtime=payload.get('runtime'),
                aliases=sorted({t['title'] for t in payload.get('alternative_titles',{}).get('titles',[]) if t.get('title')}
                               | {t.get('data',{}).get('title') for t in payload.get('translations',{}).get('translations',[]) if t.get('data',{}).get('title')}),
                releases=releases,source_url='https://www.themoviedb.org/movie/'+str(payload['id']),fetched_at=now())

class Client:
    def __init__(self,token,cache,request_budget=300):
        self.token=token; self.cache=cache
        self.cache.setdefault('queries',{}); self.cache.setdefault('movies',{})
        self.session=requests.Session()
        self.session.headers.update({'Authorization':'Bearer '+token,'User-Agent':'CineMadrid/0.3 (+https://github.com/IgnacioGarijo/cine-madrid)'})
        self.requests=0; self.budget=request_budget
    def fresh(self,record,days=7):
        if not record: return False
        return datetime.fromisoformat(record['fetched_at']) >= datetime.fromisoformat(now())-timedelta(days=days)
    def get(self,path,**params):
        if not self.token: raise TMDBError('not_configured')
        for attempt in range(3):
            if self.requests>=self.budget: raise TMDBError('request_budget')
            time.sleep(.12); self.requests+=1
            try:
                response=self.session.get('https://api.themoviedb.org/3/'+path,params=params,timeout=20,allow_redirects=False)
            except requests.RequestException: raise TMDBError('network_error') from None
            if response.status_code in (401,403): raise TMDBError('authentication_failed')
            if response.status_code==429 or response.status_code>=500:
                if attempt<2: time.sleep(2*(attempt+1)); continue
            if not response.ok: raise TMDBError('http_'+str(response.status_code))
            try:return response.json()
            except ValueError: raise TMDBError('invalid_response') from None
        raise TMDBError('unavailable')
    def search(self,title):
        key=normalize(title); cached=self.cache['queries'].get(key)
        if self.fresh(cached,days=1):return cached['results']
        payload=self.get('search/movie',query=title,language='es-ES',include_adult='false')
        results=[{'id':m['id'],'title':m.get('title',''),'original_title':m.get('original_title','')} for m in payload.get('results',[])[:6]]
        self.cache['queries'][key]={'results':results,'fetched_at':now()}
        return results
    def movie(self,id):
        cached=self.cache['movies'].get(str(id))
        if self.fresh(cached):return cached
        movie=slim_movie(self.get('movie/'+str(id),language='es-ES',append_to_response='credits,alternative_titles,release_dates'))
        self.cache['movies'][str(id)]=movie
        return movie
    def with_translations(self,movie):
        if movie.get('translations_checked'):return movie
        data=self.get('movie/'+str(movie['tmdb_id'])+'/translations')
        translated={t.get('data',{}).get('title') for t in data.get('translations',[]) if t.get('data',{}).get('title')}
        movie['aliases']=sorted(set(movie['aliases'])|translated)
        movie['translations_checked']=True
        self.cache['movies'][str(movie['tmdb_id'])]=movie
        return movie
    def resolve(self,source):
        if not source.get('director') and not source.get('source_year') and not re.search(r'\b(?:19|20)\d{2}\b',source['title']):
            return None,'missing_director',[]
        seen={}; searched=[]
        for query in title_variants(source['title']):
            searched.append(query)
            for result in self.search(query):
                if result['id'] not in seen:
                    candidate=self.movie(result['id'])
                    if (director_matches(source,candidate)
                            and not title_score(source,candidate)):
                        candidate=self.with_translations(candidate)
                    seen[result['id']]=candidate
            match,evidence=identity_match(source,list(seen.values()))
            if match: return match,evidence,[]
            if evidence=='ambiguous':break
        candidates=[{'id':m['id'],'title':m['title'],'year':m.get('year'),'director':m['director'],'source_url':m['source_url']} for m in seen.values()]
        return None, 'not_found' if not seen else identity_match(source,list(seen.values()))[1], candidates

def enrich(movies,sessions,cache,config,incidents,token=None):
    token=token if token is not None else os.getenv('TMDB_READ_TOKEN','')
    client=Client(token,cache,config.get('request_budget',300))
    errors=[]; matched=0
    for movie in movies:
        source_category=movie.get('category')
        try:
            identity,evidence,candidates=client.resolve(movie)
        except TMDBError as exc:
            code=str(exc); errors.append(code)
            movie.setdefault('identity_status','pending_tmdb')
            incidents.add('tmdb',code,'service','No se pudo consultar TMDB: '+code+'. Se conservan las identidades verificadas disponibles.','https://www.themoviedb.org/','error' if code=='authentication_failed' else 'warning')
            if code in ('not_configured','authentication_failed','request_budget'):break
            continue
        if not identity:
            for field in ['canonical_id','tmdb_id','identity_evidence','canonical_title','original_title','aliases','tmdb_url','year']:
                movie.pop(field,None)
            movie.update(identity_status='needs_review',identity_reason=evidence,identity_candidates=candidates[:6])
            incidents.add('tmdb','identity_'+evidence,movie['id'],'Identidad pendiente: '+movie['title']+' ('+evidence+').',movie['source_url'],'info')
            continue
        matched+=1
        movie.update(canonical_id=identity['id'],tmdb_id=identity['tmdb_id'],identity_status='verified',identity_evidence=evidence,
                     canonical_title=identity['title'],original_title=identity['original_title'],year=identity['year'],
                     aliases=identity['aliases'],tmdb_url=identity['source_url'],tmdb_runtime=identity.get('runtime'),tmdb_releases=identity['releases'])
        movie.pop('identity_candidates',None);movie.pop('identity_reason',None)
        for session in (s for s in sessions if s['movie_id']==movie['id']):
            source_label=source_category or session.get('source_category',session['category'])
            category,reason=classify(identity,date.fromisoformat(session['start'][:10]),source_label,config)
            session.update(category=category,classification_evidence=reason)
            if category=='unclassified':
                incidents.add('tmdb','classification_pending',movie['id'],'Película identificada; falta confirmar el contexto del estreno: '+movie['title'],movie['source_url'],'info')
        gap=evidence.get('duration_difference_minutes')
        if gap is not None and gap>20:
            incidents.add('tmdb','duration_mismatch',movie['id'],'La duración publicada por el cine difiere en '+str(gap)+' minutos de TMDB: '+movie['title']+'. Se conserva la duración de la fuente.',movie['source_url'])
    return {'status':'ok' if not errors else 'partial' if matched else 'error','matched_movies':matched,
            'total_movies':len(movies),'api_requests':client.requests,'checked_at':now(),'errors':sorted(set(errors))}
