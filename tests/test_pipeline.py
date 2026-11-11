import unittest
from datetime import date
from src.core import Incidents,trusted_identity
from src.sources import parse_paz,parse_day,event_tags
from src.pipeline import calendar

def html(title='Deseando amar', director='Wong Kar-wai', hour='20:00', day='Lunes 16/11'):
    return f'''<div class="rotulo_dia" data-num="0">{day}</div><div class="cines-0"><div class="horarios"><div class="peli"><a href="/es/detalles/123_1_Z_1/test"><b>{title}</b></a><p>de {director}</p><p>98 minutos</p></div><div class="horas"><a data-ho="777" href="https://tickets.example/a"><span>VOSE</span>{hour}</a></div></div></div>'''

class PipelineTests(unittest.TestCase):
    def test_advance_dates_not_array_offsets(self):
        sessions,_=parse_paz(html(),date(2026,11,11),Incidents())
        self.assertEqual(sessions[0]['start'],'2026-11-16T20:00:00+01:00')
        self.assertEqual(sessions[0]['version'],'VOSE')

    def test_new_year(self):
        self.assertEqual(parse_day('Domingo 10/01',date(2026,11,11)),date(2027,1,10))

    def test_after_midnight(self):
        sessions,_=parse_paz(html(hour='25:15'),date(2026,11,11),Incidents())
        self.assertEqual(sessions[0]['start'],'2026-11-17T01:15:00+01:00')

    def test_unknown_structure_fails_instead_of_empty_success(self):
        with self.assertRaises(ValueError):parse_paz('<div>Nueva web</div>',date(2026,11,11),Incidents())

    def test_homonymous_movies_do_not_match_by_title(self):
        catalog=[dict(id='a',title='Crash',director='David Cronenberg'),dict(id='b',title='Crash',director='Paul Haggis')]
        self.assertIsNone(trusted_identity(dict(title='Crash'),catalog))
        self.assertEqual(trusted_identity(dict(title='Crash',director='Paul Haggis'),catalog)['id'],'b')

    def test_alias_requires_evidence(self):
        catalog=[dict(id='x',title='In the Mood for Love',aliases=['Deseando amar'],director='Wong Kar-wai')]
        self.assertEqual(trusted_identity(dict(title='Deseando amar (VOSE)',director='Wong Kar-wai'),catalog)['id'],'x')
        self.assertIsNone(trusted_identity(dict(title='Deseando amar',director='Otro'),catalog))

    def test_incident_lifecycle_only_resolves_checked_sources(self):
        initial=Incidents();initial.add('paz','read_failed','source','Error');initial.add('other','read_failed','source','Error')
        next_run=Incidents(initial.finish(set()))
        result=next_run.finish({'paz'})
        self.assertEqual(next(i['status'] for i in result if i['source_id']=='paz'),'resolved')
        self.assertEqual(next(i['status'] for i in result if i['source_id']=='other'),'open')

    def test_live_music_is_not_a_recorded_concert(self):
        self.assertEqual(event_tags('Proyección de concierto grabado'),[])
        self.assertIn('live_music',event_tags('Con acompañamiento de piano en directo'))

    def test_calendar_utc_and_escaping(self):
        data=dict(generated_at='2026-11-11T10:00:00+01:00',cinemas=[dict(id='paz',name='Cine',address='Calle, 1')],sessions=[dict(id='1',cinema_id='paz',title='Título; prueba',start='2026-11-16T20:00:00+01:00',status='confirmed',duration_minutes=120,source_url='https://example.org',booking_url='https://example.org')])
        result=calendar(data)
        self.assertIn('DTSTART:20261116T190000Z',result)
        self.assertIn('DTEND:20261116T210000Z',result)
        self.assertIn('Título\\; prueba',result)
        self.assertTrue(all(len(l.encode())<=75 for l in result.splitlines()))

if __name__=='__main__':unittest.main()
