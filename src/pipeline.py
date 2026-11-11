import argparse
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .core import ROOT,MADRID,Incidents,now,read_json,write_json,trusted_identity
from .sources import Fetcher,PAZ_URL,CLASSIC_URL,SOURCE_ID,parse_paz,classic_members

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
        checked.add(SOURCE_ID)
        try:
            fetcher=Fetcher()
            sessions,movies=parse_paz(fetcher.get(PAZ_URL),today,incidents)
            try:
                classic=classic_members(fetcher.get(CLASSIC_URL))
                if not classic:
                    incidents.add(SOURCE_ID,'cycle_unreadable','classic','La página del ciclo no ofrece fichas reconocibles; no se infieren fechas.',CLASSIC_URL)
                for movie in movies:
                    if movie['id'] in classic:
                        movie.update(category='repertory',category_evidence_url=CLASSIC_URL)
            except Exception:
                incidents.add(SOURCE_ID,'cycle_read_failed','classic','No se pudo leer el ciclo Classic. La cartelera se mantiene; su clasificación queda pendiente.',CLASSIC_URL)
            for s in sessions:s['last_seen']=now()
            previous=[x for x in old.get('sessions',[]) if x['start'][:10]>=today.isoformat()]
            if previous and len(sessions)<len(previous)*.5:
                incidents.add(SOURCE_ID,'unexpected_drop','sessions','La fuente devuelve menos de la mitad de las sesiones anteriores; verificar cobertura.',PAZ_URL)
                known={s['id'] for s in sessions}
                sessions += [dict(s,stale=True,status='unverified') for s in previous if s['id'] not in known]
            sources=[dict(id=SOURCE_ID,status='ok',last_attempt=now(),last_success=now(),url=PAZ_URL)]
        except Exception as exc:
            # Never log HTTP exception URLs: third-party URLs may contain secrets.
            incidents.add(SOURCE_ID,'read_failed','source','No se pudo actualizar la cartelera ('+type(exc).__name__+'). Se conserva la última lectura válida.',PAZ_URL,'error')
            sessions=[dict(s,stale=True) for s in sessions]
            sources=[dict(id=SOURCE_ID,status='error',last_attempt=now(),last_success=next((x.get('last_success') for x in old.get('sources',[]) if x['id']==SOURCE_ID),None),url=PAZ_URL)]
    for movie in movies:
        identity=trusted_identity(movie,catalog)
        if identity:
            movie.update(canonical_id=identity['id'],identity_status='verified')
        else:
            movie['identity_status']='pending_agent'
            if refresh:
                incidents.add(SOURCE_ID,'identity_pending',movie['id'],'Identidad pendiente de verificar: '+movie['title'],movie['source_url'],'info')
    movie_map={m['id']:m for m in movies}
    for s in sessions:
        m=movie_map.get(s['movie_id'],{})
        s['canonical_id']=m.get('canonical_id')
        s['identity_status']=m.get('identity_status','pending_agent')
        # Classification needs original release AND context; no age-only guess.
        if m.get('category'): s['category']=m['category']
    for cinema in cinemas:
        if cinema['id']!=SOURCE_ID:
            incidents.add(cinema['id'],'source_pending',cinema['id'],'Fuente pendiente de integrar; no se incluyen sus sesiones.',cinema.get('url',''),'info')
    inventory_ids={c['id'] for c in cinemas}
    checked.update(i['source_id'] for i in old.get('incidents',[]) if i['code']=='source_pending' and i['source_id'] not in inventory_ids)
    data=dict(version='0.1.1',generated_at=now(),coverage_complete=False,cinemas=cinemas,sources=sources,
              movies=movies,sessions=sessions,incidents=incidents.finish(checked),agent_status='waiting_for_copilot')
    write_json(path,data)
    build(data,newsletter)
    print(f"Sesiones: {len(sessions)} | películas: {len(movies)} | fuentes activas: {sum(s['status']=='ok' for s in sources)} | incidencias abiertas: {sum(i['status']=='open' for i in data['incidents'])}")

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
    shutil.copy2(ROOT/'config/catalog.json',dist/'catalog.json')
    write_json(dist/'data.json',data)
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
