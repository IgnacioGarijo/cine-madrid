from datetime import date
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from src.adapters import Result
from src.adapters_cultural import filmoteca

FIXTURE = Path(__file__).parent / 'fixtures' / 'cultural' / 'filmoteca.html'
URL = 'https://entradasfilmoteca.sacatuentrada.es/es'

class Reader:
    def __init__(self, today, html):
        self.cinema = {'id': 'cine-dore', 'url': URL}
        self.today = today
        self.result = Result(self.cinema, today)
        self.html = html
        self.problems = []
    def soup(self, url):
        return BeautifulSoup(self.html, 'html.parser')
    def partial(self, *args):
        self.problems.append(args)

class CulturalTests(unittest.TestCase):
    def test_filmoteca_exact_session_and_excludes_talk(self):
        reader = Reader(date(2026, 11, 12), FIXTURE.read_text(encoding='utf-8'))
        filmoteca(reader)
        sessions, _ = reader.result.finish()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]['title'], 'Fin de jornada (1939)')
        self.assertEqual(sessions[0]['start'], '2026-11-13T17:30:00+01:00')
        self.assertEqual(sessions[0]['room'], '1')
        self.assertEqual(sessions[0]['director'], 'Julie Duvivier')

    def test_past_sessions_legitimate_empty(self):
        reader = Reader(date(2026, 12, 1), FIXTURE.read_text(encoding='utf-8'))
        filmoteca(reader)
        self.assertTrue(reader.result.empty_confirmed)

    def test_changed_structure_fails(self):
        with self.assertRaises(ValueError):
            filmoteca(Reader(date(2026, 11, 12), '<html></html>'))

    def test_missing_time_is_partial_not_confirmed_empty(self):
        html = FIXTURE.read_text(encoding='utf-8').replace('17:30h', 'hora pendiente')
        reader = Reader(date(2026, 11, 12), html)
        filmoteca(reader)
        self.assertTrue(reader.problems)
        self.assertFalse(getattr(reader.result, 'empty_confirmed', False))

from src.adapters_cultural import casa_america, instituto_frances, academia_cine

class MappingReader(Reader):
    def __init__(self, url, fixture_names):
        super().__init__(date(2026, 11, 12), '')
        self.cinema['url'] = url
        self.result = Result(self.cinema, self.today)
        self.fixture_names = fixture_names
    def soup(self, url):
        name = self.fixture_names[url]
        return BeautifulSoup((FIXTURE.parent / name).read_text(encoding='utf8'), 'html.parser')

class CulturalAdditionalTests(unittest.TestCase):
    def test_casa_exact_film(self):
        base = 'https://www.casamerica.es/cine'
        r = MappingReader(base, {base: 'casa_agenda.html', base + '/chicogrande': 'casa_detalle.html'})
        casa_america(r)
        s = list(r.result.sessions.values())
        self.assertEqual([(x['title'], x['start'], x['room']) for x in s], [('Chicogrande', '2026-11-25T18:00:00+01:00', 'Iberia')])
    def test_frances_exact_film(self):
        base = 'https://www.institutfrancais.es/madrid/eventos/'
        detail = 'https://www.institutfrancais.es/madrid/evento/les-chansons/'
        r = MappingReader(base, {base:'frances_agenda.html',detail:'frances_detalle.html'})
        instituto_frances(r)
        s = list(r.result.sessions.values())
        self.assertEqual([(x['title'], x['start']) for x in s], [('Les chansons d’amour', '2026-11-13T20:00:00+01:00')])
    def test_academia_screening_with_film_metadata(self):
        base = 'https://entradas.apps.academiadecine.com/actividades'
        from bs4 import BeautifulSoup
        agenda = BeautifulSoup((FIXTURE.parent/'academia_agenda.html').read_text(encoding='utf8'),'html.parser')
        cards = agenda.select('.grid-wrapper')
        one = str(cards[0])
        r = MappingReader(base, {base:'academia_agenda.html'})
        detail = (FIXTURE.parent/'academia_detalle.html').read_text(encoding='utf8')
        r.soup = lambda u: BeautifulSoup(one if u == base else detail,'html.parser')
        academia_cine(r)
        s = list(r.result.sessions.values())
        self.assertEqual([(x['title'], x['start'], x['duration_minutes']) for x in s], [('Siempre soy tu animal materno', '2026-11-12T16:00:00+01:00', 105)])
    def test_frances_excludes_other_venue(self):
        base = 'https://www.institutfrancais.es/madrid/eventos/'
        detail = 'https://www.institutfrancais.es/madrid/evento/les-chansons/'
        r = MappingReader(base, {base:'frances_agenda.html', detail:'frances_detalle.html'})
        original = r.soup
        def soup(url):
            result = original(url)
            if url == detail:
                result.select_one('.location__name').string = 'Cineteca Madrid'
            return result
        r.soup = soup
        instituto_frances(r)
        self.assertFalse(r.result.sessions)
    def test_academia_excludes_podcast(self):
        base = 'https://entradas.apps.academiadecine.com/actividades'
        r = MappingReader(base, {base:'academia_agenda.html'})
        r.soup = lambda u: BeautifulSoup((FIXTURE.parent/'academia_agenda.html').read_text(encoding='utf8') if u == base else '<html><h1>Podcast</h1></html>', 'html.parser')
        academia_cine(r)
        self.assertFalse(r.result.sessions)

from src.adapters_cultural import reina_sofia

class ReinaTests(unittest.TestCase):
    def setup_reader(self):
        base = 'https://www.museoreinasofia.es/cine-nuevos-medios/'
        url = 'https://www.museoreinasofia.es/actividad/raul-perrone-presente-escena-cine'
        return MappingReader(base, {base:'reina_agenda.html',url:'reina_detalle.html'})
    def test_film_and_exact_start(self):
        r = self.setup_reader(); reina_sofia(r)
        s = list(r.result.sessions.values())
        self.assertEqual([(x['title'], x['start'], x['room']) for x in s], [('Sean eternxs', '2026-11-13T19:00:00+01:00', 'Edificio Sabatini, Cine')])
    def test_multiple_films_not_given_same_start(self):
        r = self.setup_reader(); original = r.soup
        def soup(url):
            page = original(url)
            title = page.select_one('[class*="ScheduleItem-module--scheduleTitle--"]')
            if title:
                new = page.new_tag('em'); new.string = 'Otra película'; title.append(new)
            return page
        r.soup = soup; reina_sofia(r)
        self.assertFalse(r.result.sessions)
        self.assertFalse(getattr(r.result, 'empty_confirmed', False))
    def test_structure_change_is_failure(self):
        r = self.setup_reader(); r.soup = lambda _: BeautifulSoup('<html></html>', 'html.parser')
        with self.assertRaises(ValueError): reina_sofia(r)

from src.adapters_cultural import casa_mexico

class MexicoTests(unittest.TestCase):
    def setup_reader(self):
        base='https://www.casademexico.es/cine-en-casa-de-mexico/'
        detail=base+'ciclo-de-cine-cuando-cae-la-noche/'
        return MappingReader(base,{base:'mexico_agenda.html',detail:'mexico_ciclo.html'})
    def test_individual_sessions_and_two_dates(self):
        r=self.setup_reader();casa_mexico(r)
        sessions=list(r.result.sessions.values())
        starts=sorted(s['start'] for s in sessions if s['title']=='Estela')
        self.assertEqual(starts,['2026-11-19T19:00:00+01:00','2026-11-28T19:00:00+01:00'])
        self.assertEqual(len(sessions),7)
    def test_venue_is_not_inferred(self):
        r=self.setup_reader();original=r.soup
        def soup(url):
            page=original(url); node=page.select_one('.elementor-heading-title')
            if node: node.string='Cine - Auditorio de otro lugar'
            return page
        r.soup=soup;casa_mexico(r)
        self.assertFalse(r.result.sessions)
        self.assertTrue(r.problems)
    def test_cycle_range_is_not_daily_schedule(self):
        r=self.setup_reader();original=r.soup
        def soup(url):
            page=original(url)
            if 'ciclo-de-cine' in url:
                for p in page.select('.elementor-widget-container p'):
                    if p.select_one('a[href]'): p.string='Del 13 de noviembre al 28 de noviembre | 19:00'
            return page
        r.soup=soup;casa_mexico(r)
        self.assertFalse(r.result.sessions)
        self.assertTrue(r.problems)
