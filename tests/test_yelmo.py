import json
import unittest
from datetime import date
from unittest.mock import patch

from src.adapters import Reader
from src.adapters_yelmo import yelmo, read_official
from src.core import Incidents


def reader():
    c = {'id':'cine-yelmo-palafox', 'yelmo_id':'palafox-luxury-madrid',
         'url':'https://cineyelmo.com/es?cinema=palafox-luxury-madrid',
         'fallback_url':'https://cinerama.es/cartelera/cine/yelmo-cines-luxury-palafox/'}
    r = Reader(c,date(2026,11,16),Incidents())
    r.get = lambda url: ('<script src="/_next/static/chunks/pages/_app-ab12.js"></script>'
                         if url == 'https://cineyelmo.com/' else 'API_KEY:"public-test-key"')
    return r


def api_responses(r, wrong_cinema=False):
    schedules = {'dates':['2026-12-21'], 'schedules':[{
        'cinemaId':'another-cinema' if wrong_cinema else 'palafox-luxury-madrid',
        'movieId':'akira','dates':[{'date':'2026-12-21','languages':[
            {'language':'SUB ESP','showtimes':[{'sessionId':'123','datetime':'2026-12-21T19:30:00',
                'screen':'2','format':{'name':'2D'},'experience':{'name':'LUX'}}]}]}]}]}
    movie = {'id':'akira','name':'Akira','length':'124 min','cast':{'directors':[{'name':'Katsuhiro Otomo'}]}}
    films = {'pageInfo':{'hasNextPage':False},'edges':[{'node':movie}],'totalCount':1}
    def post(url, *, json, headers):
        return __import__('json').dumps({'data':{'billboardByCinema':schedules} if 'Billboard' in json['query'] else {'movies':films}})
    r.fetcher.post = post


class YelmoTests(unittest.TestCase):
    def test_official_future_show_and_identity(self):
        r=reader(); api_responses(r); read_official(r)
        sessions,movies=r.result.finish()
        self.assertEqual(len(sessions),1)
        self.assertEqual(sessions[0]['start'],'2026-12-21T19:30:00+01:00')
        self.assertEqual(sessions[0]['version'],'VOSE')
        self.assertIn('cinema=palafox-luxury-madrid',sessions[0]['booking_url'])
        self.assertIn('session=123',sessions[0]['booking_url'])
        self.assertEqual(movies[0]['director'],'Katsuhiro Otomo')
        self.assertEqual(movies[0]['source_work_id'],'yelmo:akira')

    def test_other_venue_rejected_and_fallback_identified(self):
        r=reader(); api_responses(r,wrong_cinema=True)
        with patch('src.adapters_yelmo.cinerama') as fallback:
            yelmo(r)
        fallback.assert_called_once()
        self.assertFalse(r.result.sessions)
        self.assertEqual(len(r.incidents.current),1)
        self.assertEqual(r.cinema['id'],'cine-yelmo-palafox')

    def test_conflicting_date_is_not_invented(self):
        r=reader();api_responses(r)
        original=r.fetcher.post
        def post(url,**kwargs):
            return original(url,**kwargs).replace('2026-12-21T19:30:00','2026-12-22T19:30:00')
        r.fetcher.post=post
        with self.assertRaises(ValueError): read_official(r)
        self.assertFalse(r.result.sessions)
        self.assertTrue(r.incidents.current)


if __name__=='__main__': unittest.main()
