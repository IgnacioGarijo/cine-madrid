import gzip
import hashlib
import json
import unittest
from datetime import date
from unittest.mock import patch

from src.filmagenda import BASE, FilmAgendaError, audit, download


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


if __name__=='__main__':unittest.main()
