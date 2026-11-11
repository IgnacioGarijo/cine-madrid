import argparse
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .core import ROOT,MADRID,Incidents,now,read_json,write_json,trusted_identity,normalize,clean_title
from .sources import Fetcher,PAZ_URL,CLASSIC_URL,SOURCE_ID,parse_paz,classic_members
from .tmdb import enrich
from .adapters import read_cinema

def run(refresh=True, newsletter=False):
    path=ROOT/'data/public.json'
    old=read_json(path,{})
    incidents=Incidents(old.get('incidents',[]))
    today=datetime.now(MADRID).date()
    cinemas=read_json(ROOT/'config/cinemas.json',[])
    catalog=read_json(ROOT/'config/catalog.json',[])
    sessions=old.get('sessions',[])
    movies=old.get('movies',[])
    checked=set()
    sources=old.get('sources',[])
    if refresh:
        sessions=[];movies=[];sources=[]
        for cinema in cinemas:
            cid=cinema['id']
            if not cinema.get('adapter'):continue
            checked.add(cid)
            previous=[x for x in old.get('sessions',[]) if x['cinema_id']==cid and x['start'][:10]>=today.isoformat()]
            prior_source=next((x for x in old.get('sources',[]) if x['id']==cid),{})
            try:
                fresh,films,pages=read_cinema(cinema,today,incidents)
                for session in fresh:session['last_seen']=now()
                partial=any(i['source_id']==cid and i['code']=='partial_read' for i in incidents.current.values())
                if previous and (len(fresh)<len(previous)*.5 or partial):
                    if len(fresh)<len(previous)*.5:incidents.add(cid,'unexpected_drop','sessions','La fuente devuelve menos de la mitad de las sesiones anteriores; verificar cobertura.',cinema['url'])
                    known={x['id'] for x in fresh}
                    missing=[dict(x,stale=True,status='unverified') for x in previous if x['id'] not in known]
                    fresh+=missing
                    film_ids={m['id'] for m in films}
                    films += [m for m in old.get('movies',[]) if m['id'] in {x['movie_id'] for x in missing} and m['id'] not in film_ids]
                sessions+=fresh;movies+=films
                partial=any(i['source_id']==cid and i['code']=='partial_read' for i in incidents.current.values())
                sources.append(dict(id=cid,status='partial' if partial else 'ok',last_attempt=now(),last_success=now(),url=cinema['url'],pages_read=len(pages),
                    first_session=min(x['start'] for x in fresh),last_session=max(x['start'] for x in fresh)))
                print(f"Fuente {cid}: {len(fresh)} sesiones / {len(pages)} páginas",flush=True)
            except Exception as exc:
                incidents.add(cid,'read_failed','source','No se pudo actualizar la cartelera ('+type(exc).__name__+'). Se conserva la última lectura válida.',cinema['url'],'error')
                sessions += [dict(x,stale=True,status='unverified') for x in previous]
                film_ids={x['movie_id'] for x in previous}
                movies += [m for m in old.get('movies',[]) if m['id'] in film_ids]
                sources.append(dict(id=cid,status='error',last_attempt=now(),last_success=prior_source.get('last_success'),url=cinema['url']))
                print(f"Fuente {cid}: error {type(exc).__name__}",flush=True)
    previous_movies={m['id']:m for m in old.get('movies',[])}
    unchanged_ids=set()
    for movie in movies:
        previous=previous_movies.get(movie['id'],{})
        unchanged=(normalize(clean_title(movie['title']))==normalize(clean_title(previous.get('title','')))
                   and normalize(movie.get('director',''))==normalize(previous.get('director','')))
        if unchanged:unchanged_ids.add(movie['id'])
        if refresh and unchanged and previous.get('identity_status')=='verified':
            for field in ['canonical_id','tmdb_id','identity_status','identity_evidence','canonical_title','original_title',
                          'year','aliases','tmdb_url','tmdb_runtime','tmdb_releases']:
                if field in previous: movie[field]=previous[field]
        identity=trusted_identity(movie,catalog)
        if identity and movie.get('identity_status')!='verified':
            movie.update(canonical_id=identity['id'],identity_status='verified')
        movie.setdefault('identity_status','pending_tmdb')
    tmdb_status=old.get('tmdb',{'status':'not_configured','matched_movies':0,'total_movies':len(movies)})
    if refresh:
        cache=read_json(ROOT/'data/tmdb_cache.json',{})
        rules=read_json(ROOT/'config/classification.json')
        tmdb_status=enrich(movies,sessions,cache,rules,incidents)
        write_json(ROOT/'data/tmdb_cache.json',cache)
        if tmdb_status['status']=='ok':checked.add('tmdb')
    movie_map={m['id']:m for m in movies}
    for s in sessions:
        m=movie_map.get(s['movie_id'],{})
        s['canonical_id']=m.get('canonical_id')
        s['identity_status']=m.get('identity_status','pending_agent')
        s['search_titles']=list(dict.fromkeys(t for t in [m.get('canonical_title'),m.get('original_title'),*m.get('aliases',[])] if t))
        s['tmdb_url']=m.get('tmdb_url')
        s['year']=m.get('year')
        # Explicit classic programmes remain independent classification evidence.
        if m.get('category'): s['category']=m['category']
        if refresh and m.get('identity_status')=='verified' and 'classification_evidence' not in s:
            previous_session=next((p for p in old.get('sessions',[]) if p['id']==s['id']),None)
            if previous_session and m['id'] in unchanged_ids:
                for field in ['category','classification_evidence']:
                    if field in previous_session:s[field]=previous_session[field]
    for cinema in cinemas:
        if not cinema.get('adapter'):
            incidents.add(cinema['id'],'source_pending',cinema['id'],cinema.get('reading_note','Fuente pendiente de integrar; no se incluyen sus sesiones.'),cinema.get('url',''),'info')
    inventory_ids={c['id'] for c in cinemas}
    checked.update(i['source_id'] for i in old.get('incidents',[]) if i['code']=='source_pending' and i['source_id'] not in inventory_ids)
    data=dict(version='0.4.1',generated_at=now(),coverage_complete=False,cinemas=cinemas,sources=sources,
              movies=movies,sessions=sessions,incidents=incidents.finish(checked),agent_status='waiting_for_copilot',tmdb=tmdb_status)
    write_json(path,data)
    build(data,newsletter)
    print(f"Sesiones: {len(sessions)} | películas: {len(movies)} | fuentes activas: {sum(s['status']=='ok' for s in sources)} | incidencias abiertas: {sum(i['status']=='open' for i in data['incidents'])}")
    if refresh:
        print(f"TMDB: {tmdb_status['status']} | identificadas: {tmdb_status['matched_movies']}/{tmdb_status['total_movies']} | consultas: {tmdb_status['api_requests']}")
        for movie in movies:
            categories=sorted({s['category'] for s in sessions if s['movie_id']==movie['id']})
            print(f"{movie['title']} | {movie.get('canonical_id','sin identificar')} | {movie['identity_status']} | {','.join(categories)}")

def ics_escape(value):
    return str(value).replace('\\','\\\\').replace('\n','\\n').replace(',','\\,').replace(';','\\;')

def calendar(data):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Cine Madrid//ES','CALSCALE:GREGORIAN','X-WR-CALNAME:Cine Madrid']
    for s in data['sessions']:
        if s.get('stale') or s['status']!='confirmed':continue
        start=datetime.fromisoformat(s['start']).astimezone(timezone.utc)
        cinema=next((c for c in data['cinemas'] if c['id']==s['cinema_id']),{})
        lines+=['BEGIN:VEVENT','UID:'+s['id']+'@cine-madrid','DTSTAMP:'+datetime.fromisoformat(data['generated_at']).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                'DTSTART:'+start.strftime('%Y%m%dT%H%M%SZ'),'SUMMARY:'+ics_escape(s['title']),
                'LOCATION:'+ics_escape(cinema.get('name','')+' · '+cinema.get('address','')),'URL:'+s['source_url'],
                'DESCRIPTION:'+ics_escape('Consulta y entradas: '+s['booking_url'])]
        if s.get('duration_minutes'):lines.append('DTEND:'+(start+timedelta(minutes=s['duration_minutes'])).strftime('%Y%m%dT%H%M%SZ'))
        lines+=['END:VEVENT']
    lines+=['END:VCALENDAR']
    # RFC 5545 line folding, measured in UTF-8 bytes.
    folded=[]
    for line in lines:
        chunk=''
        for char in line:
            if len((chunk+char).encode())>73:folded.append(chunk);chunk=' '+char
            else:chunk+=char
        folded.append(chunk)
    return '\r\n'.join(folded)+'\r\n'

def build(data,newsletter=False):
    dist=ROOT/'dist'
    dist.mkdir(exist_ok=True)
    shutil.copytree(ROOT/'web',dist,dirs_exist_ok=True)
    catalog={m['id']:m for m in read_json(ROOT/'config/catalog.json',[])}
    for movie in data['movies']:
        if movie.get('identity_status')=='verified' and movie.get('tmdb_id'):
            catalog[movie['canonical_id']]={
                'id':movie['canonical_id'],'tmdb_id':movie['tmdb_id'],'title':movie['canonical_title'],
                'original_title':movie.get('original_title',''),'aliases':movie.get('aliases',[]),
                'year':movie.get('year'),'director':movie.get('director',''),'source_url':movie['tmdb_url']}
    write_json(dist/'catalog.json',sorted(catalog.values(),key=lambda m:m['title'].casefold()))
    write_json(dist/'data.json',data)
    write_json(dist/'favorites.json',read_json(ROOT/'config/favorites.json',[]))
    (dist/'calendario.ics').write_text(calendar(data),encoding='utf-8',newline='')
    (dist/'.nojekyll').touch()
    posts=ROOT/'data/newsletters'
    posts.mkdir(exist_ok=True)
    if newsletter:
        today=datetime.now(MADRID).date()
        selected=[s for s in data['sessions'] if s['category']=='repertory' and today.isoformat()<=s['start'][:10]<(today+timedelta(days=7)).isoformat() and not s.get('stale')]
        post={'id':today.isoformat(),'published_at':now(),'sessions':selected,'coverage_complete':False,
              'note':'Selección de reposiciones respaldadas por la fuente. Cobertura parcial; la identidad entre distintas fuentes puede seguir pendiente.'}
        write_json(posts/(today.isoformat()+'.json'),post)
    write_json(dist/'newsletters.json',[read_json(p) for p in sorted(posts.glob('*.json'),reverse=True)])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--build-only',action='store_true');parser.add_argument('--newsletter',action='store_true')
    args=parser.parse_args();run(not args.build_only,args.newsletter)
