import gzip
import hashlib
import json
import unittest
from datetime import date
from unittest.mock import patch

from src.filmagenda import BASE, FilmAgendaError, audit, download
from src.filmagenda_merge import convert, merge
from src.core import Incidents


class Response:
    def __init__(self, status=200, content=b'', headers=None):
        self.status_code=status;self.content=content;self.headers=headers or {}
    def json(self): return json.loads(self.content)
    def iter_content(self, size): yield self.content


def encoded(value): return json.dumps(value,ensure_ascii=False).encode('utf8')


class FilmAgendaTests(unittest.TestCase):
    def setUp(self):
        self.token='test-private-credential'
        self.record={'film':{'id':1,'title':{'original':'Akira'}},'screenings':[{'id':1,'showtime_local':'2027-06-15T20:00:00','theater':{'id':'paz','name':'Cine Paz'}}]}
        self.payload=gzip.compress(encoded(self.record)+b'\n')
        self.manifest={'api_version':'v1','snapshot_version':'test-1','generated_at':'2026-11-16T06:00:00Z',
            'license':{'attribution':'FilmAgenda CC BY 4.0'},'datasets':{'upcoming_films':{'record_count':1,'screening_count':1}},
            'files':[{'path':'upcoming-films.ndjson.gz','sha256':hashlib.sha256(self.payload).hexdigest()}]}
        self.manifest_bytes=encoded(self.manifest)
        self.pointer={'api_version':'v1','snapshot_version':'test-1','published_at':'2026-11-16T07:00:00Z',
            'manifest_url':BASE+'/v1/snapshots/test-1/manifest.json','manifest_sha256':hashlib.sha256(self.manifest_bytes).hexdigest()}
        class Session:
            def __init__(inner):inner.calls=[]
            def get(inner,url,**kwargs):
                inner.calls.append((url,kwargs))
                if url.endswith('current.json'):return Response(content=encoded(self.pointer))
                if url.endswith('manifest.json'):return Response(content=self.manifest_bytes)
                return Response(status=307,headers={'Location':'https://example.r2.dev/signed?temporary=yes'})
        self.session=Session()

    def test_checksums_and_cross_host_credential_isolation(self):
        with patch('src.filmagenda.requests.get',return_value=Response(content=self.payload)) as signed:
            pointer,manifest,records=download(self.token,self.session)
        self.assertEqual(records,[self.record])
        self.assertEqual(len(self.session.calls),3)
        for url,kwargs in self.session.calls:self.assertEqual(kwargs['headers']['Authorization'],'Bearer '+self.token)
        self.assertNotIn('headers',signed.call_args.kwargs)
        self.assertIn('Mes 2027-06: 1',audit(pointer,manifest,records,date(2026,11,16)))

    def test_rejects_untrusted_manifest_before_sending_credential(self):
        self.pointer['manifest_url']='https://example.com/steal'
        with self.assertRaises(FilmAgendaError):download(self.token,self.session)
        self.assertEqual(len(self.session.calls),1)

    def test_rejects_tampered_download(self):
        with patch('src.filmagenda.requests.get',return_value=Response(content=b'corrupt')):
            with self.assertRaisesRegex(FilmAgendaError,'integridad'):download(self.token,self.session)

    def test_rejects_tampered_manifest(self):
        self.pointer['manifest_sha256']='0'*64
        with self.assertRaisesRegex(FilmAgendaError,'integridad'):download(self.token,self.session)
        self.assertEqual(len(self.session.calls),2)

    def test_convert_explicit_venue_and_original_language_without_assuming_subtitles(self):
        record={'film':{'id':42,'film_url':'https://www.filmagenda.es/pelicula/42-akira?x=1',
            'title':{'original':'Akira','display':'Akira'},'year':1988,'runtime_minutes':124,
            'research':{'credits':[{'department':'directing','role':'director','name':'Katsuhiro Otomo'}]}},
            'screenings':[{'id':11,'film_id':42,'theater':{'id':'palafox','name':'Palafox'},
                'showtime_local':'2027-01-20T19:30:00','timezone':'Europe/Madrid','version':'vose',
                'screening_url':'https://www.filmagenda.es/s/11?destination=film&utm_source=partner_api',
                'annotations':[{'tag':'notice','label_es':'Datos sin confirmar'},{'tag':'live_music','label_es':'Música'}]},
                {'id':12,'film_id':42,'theater':{'id':'different'},'showtime_local':'2027-01-20T19:30:00',
                 'timezone':'Europe/Madrid','version':None,'screening_url':'https://www.filmagenda.es/s/12?destination=film'}]}
        sessions,movies=convert([record],{'palafox':'our-palafox'},{'our-palafox'},date(2026,11,16),Incidents())
        self.assertEqual(len(sessions),1);self.assertEqual(sessions[0]['cinema_id'],'our-palafox')
        self.assertEqual(sessions[0]['version'],'VO');self.assertEqual(sessions[0]['start'],'2027-01-20T19:30:00+01:00')
        self.assertTrue(sessions[0]['source_warning']);self.assertIn('live_music',sessions[0]['special_tags'])
        self.assertEqual(movies[0]['source_year'],1988);self.assertEqual(movies[0]['director'],'Katsuhiro Otomo')

    def test_merge_preserves_source_priority_and_distinct_films_or_versions(self):
        films=[{'id':'p','title':'Akira','director':'Katsuhiro Otomo'},
               {'id':'f','title':'Akira','director':'Katsuhiro Otomo'},
               {'id':'another','title':'Otra película','director':'Otro'}]
        base={'cinema_id':'paz','start':'2026-11-20T20:00:00+01:00','version':'VOSE','stale':False}
        primary=[dict(base,id='primary',movie_id='p')]
        extra=[dict(base,id='same',movie_id='f',version='VO',special_tags=['discussion']),dict(base,id='different-version',movie_id='f',version='Doblada'),
               dict(base,id='different-film',movie_id='another')]
        result,count=merge(primary,extra,films)
        self.assertEqual(count,1);self.assertEqual([x['id'] for x in result],['primary','different-version','different-film'])
        self.assertIn('discussion',result[0]['special_tags']);self.assertEqual(result[0]['annotation_source'],'filmagenda')
        result,count=merge([dict(primary[0],stale=True)],extra[:1],films)
        self.assertEqual(count,0);self.assertEqual([x['id'] for x in result],['same'])

    def test_merge_does_not_combine_verified_homonyms(self):
        a={'id':'a','title':'Akira','canonical_id':'tmdb:1','identity_status':'verified'}
        b={'id':'b','title':'Akira','canonical_id':'tmdb:2','identity_status':'verified'}
        row={'cinema_id':'paz','start':'2026-11-20T20:00:00+01:00','version':'VO'}
        result,count=merge([dict(row,id='1',movie_id='a')],[dict(row,id='2',movie_id='b')],[a,b])
        self.assertEqual(count,0);self.assertEqual(len(result),2)


if __name__=='__main__':unittest.main()
