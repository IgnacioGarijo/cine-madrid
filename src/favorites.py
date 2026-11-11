"""Owner-managed public favourites. No write credential is shipped to the browser."""
import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
import requests
from .core import ROOT,read_json,write_json
from .tmdb import Client,title_variants

def sync_shared_favorites(url):
    response=requests.get(url,timeout=15);response.raise_for_status();movies=response.json()
    if not isinstance(movies,list) or not all(isinstance(m,dict) and isinstance(m.get('tmdb_id'),int) and m.get('id')=='tmdb:'+str(m['tmdb_id']) and isinstance(m.get('title'),str) for m in movies):
        raise ValueError('Lista compartida no válida')
    write_json(ROOT/'config/favorites.json',movies)
    return movies

def field(body,label):
    match=re.search(r'^### '+re.escape(label)+r'\s*\n(.*?)(?=\n### |\Z)',body,re.M|re.S)
    return match[1].strip() if match else ''

def request_url(movie,operation='Añadir',page=1):
    return 'https://github.com/IgnacioGarijo/cine-madrid/issues/new?'+urlencode({'template':'favorita.yml','operation':operation,'movie':movie,'page':page})

def apply_request(event,owner,favorites,client,searches=None):
    issue=event.get('issue',{})
    if issue.get('user',{}).get('login')!=owner or not issue.get('title','').startswith('Favoritas:'):
        return favorites,None,False
    operation=field(issue.get('body',''),'Operación');query=field(issue.get('body',''),'Película')
    if operation not in ('Añadir','Quitar','Buscar') or not query or len(query)>300:return favorites,'Solicitud incompleta.',False
    if operation=='Buscar':
        raw_page=field(issue.get('body',''),'Página') or '1'
        if not raw_page.isdigit() or not 1<=int(raw_page)<=500:return favorites,'Página no válida.',False
        result=client.search_catalog(query,int(raw_page))
        if searches is not None:
            searches[:]=[result,*[s for s in searches if (s['query'].casefold(),s['page'])!=(query.casefold(),int(raw_page))]][:30]
        url='https://ignaciogarijo.github.io/cine-madrid/?'+urlencode({'favorite_search':query,'favorite_page':raw_page})+'#pendientes'
        return favorites,'Búsqueda completada en todo TMDB. [Volver a la web y elegir una película]('+url+'). La lista de favoritas no cambia hasta que confirmes Añadir.',True
    explicit=re.fullmatch(r'(?:https://www\.themoviedb\.org/movie/|tmdb:)(\d+)(?:-[^/?#]*)?/?',query)
    if operation=='Quitar':
        matches=[m for m in favorites if m['id']==query or m['title']==query or (explicit and m['id']=='tmdb:'+explicit[1])]
        if len(matches)!=1:return favorites,'No hay una coincidencia única para quitar.',False
        return [m for m in favorites if m['id']!=matches[0]['id']],'Quitada de la lista pública: '+matches[0]['title'],True
    if explicit:
        movie=client.movie(int(explicit[1]))
    else:
        year=re.search(r'\b((?:19|20)\d{2})\b',query)
        title=next((t for t in reversed(title_variants(query)) if not re.fullmatch(r'\d{4}',t)),query)
        candidates=[client.movie(m['id']) for m in client.search(title)]
        if year:candidates=[m for m in candidates if m.get('year')==int(year[1])]
        if len(candidates)!=1:
            reply='Confirma la película abriendo una de estas solicitudes y pulsando **Create** en GitHub. La lista todavía no ha cambiado.\n\n'
            reply+='\n'.join('- ['+m['title']+' ('+str(m.get('year') or 'sin año')+') · '+m.get('director','')+']('+request_url(m['id'])+')' for m in candidates)
            if not candidates:reply='No he encontrado una película inequívoca. Prueba con título y año o con un enlace de TMDB.'
            return favorites,reply,False
        movie=candidates[0]
    record={k:movie[k] for k in ['id','tmdb_id','title','original_title','year','director','aliases','source_url'] if k in movie}
    updated=[*favorites] if any(m['id']==record['id'] for m in favorites) else [*favorites,record]
    return updated,'Guardada en la lista pública: '+record['title']+' ('+str(record.get('year') or '')+').',True

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--respond',action='store_true');args=parser.parse_args()
    reply_path=Path(os.environ.get('RUNNER_TEMP','.'))/'favorite-reply.json'
    repo=os.environ['GITHUB_REPOSITORY'];owner=repo.split('/')[0]
    if not args.respond:
        event=read_json(os.environ['GITHUB_EVENT_PATH']);path=ROOT/'config/favorites.json'
        if os.getenv('FAVORITE_SEARCH'):
            event={'issue':{'user':{'login':owner},'title':'Favoritas: búsqueda','body':'### Operación\n\nBuscar\n\n### Película\n\n'+os.environ['FAVORITE_SEARCH']+'\n\n### Página\n\n'+os.getenv('FAVORITE_PAGE','1'),'number':0}}
        cache=read_json(ROOT/'data/tmdb_cache.json',{})
        searches=read_json(ROOT/'data/favorite-searches.json',[])
        updated,reply,success=apply_request(event,owner,read_json(path,[]),Client(os.getenv('TMDB_READ_TOKEN',''),cache),searches)
        if reply is not None:
            write_json(path,updated);write_json(ROOT/'data/tmdb_cache.json',cache)
            write_json(ROOT/'data/favorite-searches.json',searches)
            write_json(reply_path,dict(number=event['issue']['number'],body=reply,success=success))
    elif reply_path.exists():
        reply=read_json(reply_path)
        headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'}
        base='https://api.github.com/repos/'+repo+'/issues/'+str(reply['number'])
        requests.post(base+'/comments',json={'body':reply['body']},headers=headers,timeout=25).raise_for_status()
        if reply['success']:requests.patch(base,json={'state':'closed'},headers=headers,timeout=25).raise_for_status()

if __name__=='__main__':main()
