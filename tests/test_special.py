import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch
from src.adapters import Reader
from src.adapters_special import sala_equis, pequeno_cine, ocine_caleido, palacio_prensa
from src.core import Incidents
from src.sources import Fetcher

FIX = Path(__file__).parent / 'fixtures' / 'special'
BOOKING = 'https://kinetike.com:83/views/sesionesFuturas.aspx?idPelicula=2969&cine=EQUIS'
FILM = 'https://salaequis.es/ciclos/la-bola-negra/'


def fixture(name):
    return (FIX / name).read_text(encoding='utf8')


def equis_reader():
    r = Reader({'id':'sala-equis','url':'https://salaequis.es/'}, date(2026,11,12), Incidents())
    pages = {'https://salaequis.es/taquilla/': '<a href="'+FILM+'">LA BOLA NEGRA</a>',
             FILM: fixture('equis_film.html'), BOOKING: fixture('equis_dates.html')}
    r.get = pages.__getitem__
    r.fetcher.post = Mock(return_value=fixture('equis_times.html'))
    return r


class SpecialTests(unittest.TestCase):
    def test_equis_date_query_only_and_panel_date_binding(self):
        r = equis_reader(); sala_equis(r)
        sessions = list(r.result.sessions.values())
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]['start'], '2026-11-13T19:15:00+01:00')
        self.assertEqual(sessions[0]['director'], 'Javier Calvo y Javier Ambrossi')
        self.assertEqual(sessions[0]['duration_minutes'], 155)
        self.assertEqual(sessions[0]['booking_url'], BOOKING)
        calls = r.fetcher.post.call_args_list
        self.assertEqual(len(calls), 5)
        for call in calls:
            payload = call.args[1]
            self.assertEqual([v for k,v in payload.items() if not k.startswith('_') and k != 'theScriptManager1_HiddenField'], ['SESIONES'])
            self.assertNotIn('ctl12', payload)
        # The 19:15 response for panel 01 must not create that time for dates 02..05.
        self.assertEqual(len(r.incidents.current), 1)

    def test_equis_dates_without_times_are_not_sessions(self):
        r = equis_reader(); r.fetcher.post.return_value = fixture('equis_dates.html')
        sala_equis(r)
        self.assertFalse(r.result.sessions)
        self.assertFalse(r.result.empty_confirmed)
        self.assertTrue(r.incidents.current)

    def test_pcine_individual_dates_and_metadata(self):
        r = Reader({'id':'peque-o-cine-estudio'}, date(2026,11,12), Incidents())
        r.get = lambda _: fixture('pcine.html')
        pequeno_cine(r)
        sessions = list(r.result.sessions.values())
        self.assertEqual(len(sessions), 2)
        self.assertEqual({s['start'] for s in sessions}, {'2026-11-12T17:30:00+01:00','2026-11-12T22:00:00+01:00'})
        self.assertEqual(sessions[0]['director'], 'Vanesa Benítez')
        self.assertEqual(sessions[0]['duration_minutes'], 95)
        self.assertTrue(all(s['version'] == 'Sin especificar' for s in sessions))

    def test_ocine_group_variants_and_explicit_vose(self):
        r = Reader({'id':'ocine-urban-caleido'}, date(2026,11,12), Incidents())
        r.fetcher.post = Mock(return_value=json.dumps({'nomCinema':'OCINE URBAN CALEIDO','pelicules':[{'id':10876}], 'estrenes':[], 'anticipades':[]}))
        r.get = lambda _: fixture('caleido_detail.json')
        ocine_caleido(r)
        sessions = list(r.result.sessions.values())
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0]['start'], '2026-11-12T15:45:00+01:00')
        self.assertEqual(sessions[0]['version'], 'VOSE')
        self.assertEqual(sessions[0]['director'], 'James Watkins')
        self.assertEqual(sessions[0]['id'], 'ocine-urban-caleido:session:37596')

    def test_ocine_wrong_venue_rejected(self):
        r = Reader({'id':'ocine-urban-caleido'}, date(2026,11,12), Incidents())
        r.fetcher.post = Mock(return_value='{"nomCinema":"OTRO CINE"}')
        with self.assertRaises(ValueError): ocine_caleido(r)

    def test_prensa_uses_explicit_iso_times_and_reports_unread_calendar(self):
        r = Reader({'id':'palacio-prensa'}, date(2026,11,12), Incidents())
        r.get = lambda _: fixture('prensa.html')
        palacio_prensa(r)
        sessions = list(r.result.sessions.values())
        self.assertEqual(len(sessions), 6)
        self.assertEqual(len(r.result.movies), 3)
        self.assertEqual(sessions[0]['start'], '2026-11-12T15:30:00+01:00')
        self.assertEqual(sessions[0]['director'], 'Daniel Monzón')
        self.assertEqual({s['version'] for s in sessions}, {'Doblada'})
        self.assertTrue(all(s['start'].startswith('2026-11-12') for s in sessions))
        self.assertIn('2026-12-04', next(iter(r.incidents.current.values()))['message'])

    def test_prensa_wrong_venue_rejected(self):
        r = Reader({'id':'palacio-prensa'}, date(2026,11,12), Incidents())
        r.get = lambda _: fixture('prensa.html').replace('Plaza del Callao, 4', 'Otra calle, 4')
        with self.assertRaises(ValueError): palacio_prensa(r)

    def test_pcine_recognized_past_schedule_is_confirmed_empty(self):
        r = Reader({'id':'peque-o-cine-estudio'}, date(2026,11,13), Incidents())
        r.get = lambda _: fixture('pcine.html')
        pequeno_cine(r)
        self.assertFalse(r.result.sessions)
        self.assertTrue(r.result.empty_confirmed)

    def test_ocine_version_belongs_to_variant_and_empty_errors_are_not_confirmed(self):
        r = Reader({'id':'ocine-urban-caleido'}, date(2026,11,12), Incidents())
        r.fetcher.post = Mock(return_value=json.dumps({'nomCinema':'OCINE URBAN CALEIDO','pelicules':[{'id':10876}], 'estrenes':[], 'anticipades':[]}))
        detail = json.loads(fixture('caleido_detail.json'))
        variant = detail['subPelicules'][-1]
        variant['titol'] = 'Clayface'; variant['propietatsDesc'] = ['2D']
        r.get = lambda _: json.dumps(detail)
        ocine_caleido(r)
        self.assertEqual({s['version'] for s in r.result.sessions.values()}, {'Sin especificar'})
        self.assertTrue(all('/#/DetallPelicula/' in s['source_url'] for s in r.result.sessions.values()))
        r.result.sessions.clear()
        r.get = Mock(side_effect=ValueError('read failed'))
        ocine_caleido(r)
        self.assertFalse(r.result.empty_confirmed)

    @patch('src.sources.time.sleep')
    def test_fetcher_post_checks_robots_and_preserves_session(self, sleep):
        f = Fetcher(); f.session = Mock()
        robot = Mock(status_code=200, text='User-agent: *\nDisallow: /private')
        response = Mock(content=b'ok')
        f.session.get.return_value = robot; f.session.request.return_value = response
        self.assertEqual(f.post('https://example.org/public', {'01':'SESIONES'}), 'ok')
        self.assertEqual(f.session.get.call_count, 1)
        f.session.request.assert_called_once_with('POST', 'https://example.org/public', timeout=35, data={'01':'SESIONES'}, json=None)
        sleep.assert_called_once_with(.3)
        with self.assertRaises(ValueError): f.post('https://example.org/private', {})
        self.assertEqual(f.session.request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
