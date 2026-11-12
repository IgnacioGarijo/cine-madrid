import unittest
from datetime import date
from bs4 import BeautifulSoup
from src.adapters import Result
from src.adapters_commercial import odeon

class Reader:
    cinema={'id':'odeon','schedule_url':'https://odeonmulticines.com/odeon-alcala-norte/peliculas'}
    def __init__(self):self.today=date(2026,11,12);self.result=Result(self.cinema,self.today);self.incidents=[]
    def soup(self,url):
        with open('tests/fixtures/commercial_odeon.html',encoding='utf8') as f:return BeautifulSoup(f.read(),'html.parser')
    def partial(self,*args):self.incidents.append(args)

class OdeonTest(unittest.TestCase):
    def test_explicit_date_version_format_and_booking(self):
        reader=Reader();odeon(reader);sessions,_=reader.result.finish()
        self.assertEqual(len(sessions),2)
        self.assertEqual([s['start'][:16] for s in sessions],['2026-11-12T17:30','2026-11-13T20:30'])
        self.assertEqual([s['version'] for s in sessions],['VOSE','Sin especificar'])
        self.assertEqual(sessions[0]['format'],'IMAX')
        self.assertEqual(sessions[0]['duration_minutes'],120)
        self.assertTrue(sessions[0]['booking_url'].endswith('sesion=1'))

class GolemTest(unittest.TestCase):
    def test_golem_explicit_date_and_version(self):
        from src.adapters_commercial import golem
        class GolemReader(Reader):
            cinema={'id':'golem','schedule_url':'https://golem.es/golem/golem-madrid/'}
            def soup(self,url):
                with open('tests/fixtures/commercial_golem.html',encoding='utf8') as f:return BeautifulSoup(f.read(),'html.parser')
        reader=GolemReader();golem(reader);sessions,_=reader.result.finish()
        self.assertEqual(len(sessions),1)
        self.assertEqual(sessions[0]['title'],'Una prueba')
        self.assertEqual(sessions[0]['version'],'VOSE')
        self.assertEqual(sessions[0]['start'][:16],'2026-11-12T19:00')
        self.assertIn('perfCode=4',sessions[0]['booking_url'])


class DetailTest(unittest.TestCase):
    def test_official_director_duration_and_year(self):
        from src.adapters_commercial import _detail
        class Fake:
            def soup(self,url):return BeautifulSoup('<table><tr><td class="txtLectura">Dirigida por:</td><td>Javier Calvo y Javier Ambrossi</td></tr><tr><td class="txtLectura">Duración:</td><td>159 min</td></tr><tr><td class="txtLectura">Año de producción:</td><td>2026</td></tr></table>','html.parser')
        self.assertEqual(_detail(Fake(),'https://golem.es/golem/pelicula/x','golem'),('Javier Calvo y Javier Ambrossi',159,2026))
    def test_detail_failure_is_partial(self):
        from src.adapters_commercial import _detail
        class Fake:
            def __init__(self):self.errors=[]
            def soup(self,url):raise ValueError('fallo')
            def partial(self,*args):self.errors.append(args)
        fake=Fake();self.assertEqual(_detail(fake,'https://example.org/film','golem'),('',None,None));self.assertEqual(len(fake.errors),1)

    def test_golem_retains_sessions_when_film_detail_fails(self):
        from src.adapters_commercial import golem
        class FailingReader(Reader):
            cinema={'id':'golem','schedule_url':'https://golem.es/golem/golem-madrid/'}
            def soup(self,url):
                if '/pelicula/' in url:raise ValueError('ficha no disponible')
                with open('tests/fixtures/commercial_golem.html',encoding='utf8') as f:return BeautifulSoup(f.read(),'html.parser')
        reader=FailingReader();golem(reader)
        self.assertEqual(len(reader.result.finish()[0]),1)
        self.assertEqual(len(reader.incidents),1)
