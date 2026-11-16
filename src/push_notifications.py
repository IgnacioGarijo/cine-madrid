"""Send opt-in alerts from a published snapshot without logging user subscriptions."""
import json
import os
import re
from datetime import datetime, timezone

import requests
from pywebpush import WebPushException, webpush

from .core import ROOT, read_json

WORKER='https://cine-madrid-tmdb.garijo-io.workers.dev'
APP='https://ignaciogarijo.github.io/cine-madrid/#pendientes'


class PushError(RuntimeError):
    pass


def upcoming(data, now=None):
    now=now or datetime.now(timezone.utc)
    result={}
    movies={m['id']:m for m in data.get('movies',[])}
    for session in data.get('sessions',[]):
        identity=session.get('canonical_id','')
        if not isinstance(identity,str) or not re.fullmatch(r'tmdb:[1-9]\d{0,9}',identity):continue
        if session.get('identity_status')!='verified' or session.get('status')!='confirmed' or session.get('stale'):continue
        try:start=datetime.fromisoformat(session['start'])
        except (KeyError,TypeError,ValueError):continue
        if start.tzinfo is None or start<now:continue
        title=(movies.get(session.get('movie_id'),{}).get('canonical_title') or session.get('title') or '').strip()
        if not title:continue
        if identity not in result or start<result[identity][0]:result[identity]=(start,title)
    return result


def send_alerts(data, secret, private_key, *, http=requests, send=webpush, now=None):
    if not secret or not private_key:raise PushError('Faltan las credenciales del servicio de avisos.')
    snapshot_day=str(data.get('generated_at',''))[:10]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',snapshot_day):raise PushError('La cartelera no tiene fecha de actualización válida.')
    films=upcoming(data,now);headers={'Authorization':'Bearer '+secret};offset=0;delivered=0;failed=0;expired=[]
    while True:
        try:
            response=http.get(WORKER+'/internal/push-feed',params={'offset':offset},headers=headers,timeout=30)
            if not response.ok:raise PushError('No se pudo consultar el servicio de avisos.')
            batch=response.json();entries=batch['subscriptions']
            if not isinstance(entries,list):raise ValueError()
        except (requests.RequestException,ValueError,KeyError,TypeError):raise PushError('No se pudo consultar el servicio de avisos.') from None
        for entry in entries:
            current=sorted(set(entry.get('favorites') or []) & set(films))
            unseen=[key for key in current if key not in (entry.get('seen') or {})]
            if unseen:
                titles=[films[key][1] for key in unseen]
                text=', '.join(titles[:3]) + (f' y {len(titles)-3} más' if len(titles)>3 else '')
                payload=json.dumps({'title':'Una favorita está en cartelera','body':text[:220],
                    'url':APP},ensure_ascii=False)
                try:
                    send(entry['subscription'],data=payload,vapid_private_key=private_key,
                         vapid_claims={'sub':'https://ignaciogarijo.github.io'},ttl=86400,timeout=20)
                    delivered+=1
                except WebPushException as exc:
                    if getattr(exc,'response',None) is not None and exc.response.status_code in (404,410):
                        expired.append(entry['id'])
                    else:failed+=1
                    continue
                except Exception:
                    failed+=1;continue
            try:
                acknowledgement=http.post(WORKER+'/internal/push-ack',headers=headers,json={'id':entry['id'],'current':current,'day':snapshot_day},timeout=20)
                if not acknowledgement.ok:failed+=1
            except requests.RequestException:failed+=1
        next_offset=batch.get('next')
        if next_offset is None:break
        if not isinstance(next_offset,int) or next_offset<=offset:raise PushError('La paginación de avisos no es válida.')
        offset=next_offset
    for entry_id in expired:
        try:http.post(WORKER+'/internal/push-ack',headers=headers,json={'id':entry_id,'remove':True},timeout=20)
        except requests.RequestException:pass
    return delivered,failed


def main():
    secret=os.getenv('PUSH_SERVER_SECRET','');private=os.getenv('PUSH_PRIVATE_KEY','')
    if not secret or not private:
        print('Avisos móviles pendientes de configurar.');return
    try:sent,failed=send_alerts(read_json(ROOT/'data/public.json',{}),secret,private)
    except PushError as exc:raise SystemExit(str(exc)) from None
    print('Avisos móviles enviados:',sent,'· entregas pendientes:',failed)
    if failed:raise SystemExit('Algunas notificaciones no se han podido enviar; se reintentará en la siguiente actualización.')


if __name__=='__main__':main()
