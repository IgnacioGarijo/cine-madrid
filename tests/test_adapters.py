import json
import unittest
from datetime import date
from src.adapters import Reader,renoir,verdi,cba,artistic,cineteca,capitol,morasol
from src.core import Incidents
from src.sources import parse_paz
from src.tmdb import identity_match

TODAY=date(2026,11,11)

def reader(adapter,page,extra=None):
    value=Reader({'id':'test-cinema','url':'https://cinema.example/programacion','adapter':adapter},TODAY,Incidents())
    value.get=lambda url:(extra or {}).get(url,page)
    return value

class AdapterTests(unittest.TestCase):
    def test_mk2_same_native_ids_in_different_cinemas_cannot_collide(self):
        from test_pipeline import html
        a,_=parse_paz(html(),TODAY,Incidents())
        b,_=parse_paz(html(),TODAY,Incidents(),source_id='hielo',source_url='https://hielo.example/',id_prefix='hielo')
        self.assertNotEqual(a[0]['id'],b[0]['id']);self.assertEqual(b[0]['cinema_id'],'hielo')
        self.assertTrue(b[0]['source_url'].startswith('https://hielo.example/'))

    def test_renoir_responsive_duplicates_and_dated_pages(self):
        card='<div class="row"><a href="/pelicula/akira/">Akira</a><small><b>de Katsuhiro Otomo</b></small><small>Duración 124 minutos</small><div class="pase-cartelera">sala 2<a href="https://www.pillalas.com/pase/madrid/test/akira/777/">20:00</a></div></div>'
        r=reader('renoir','<select id="elige-dia"><option disabled value="?fecha=2026-11-13">13</option></select>'+card*3)
        renoir(r);sessions,movies=r.result.finish()
        self.assertEqual(len(sessions),1);self.assertEqual(sessions[0]['start'],'2026-11-13T20:00:00+01:00')
        self.assertEqual(movies[0]['director'],'Katsuhiro Otomo')

    def test_verdi_filters_to_madrid_and_native_sessions(self):
        theater={'result':[dict(id=45,location='Madrid',shop_url='https://tickets.example/seats/%s/')]}
        events={'result':[dict(locale_title='Akira (VOSE)',directors=[['1','Katsuhiro Otomo']],runtime='124',performances=[dict(code='123',time='202611151830')])]}
        r=reader('verdi','',{'https://cinema.example/api/get-theaters':json.dumps(theater),'https://cinema.example/api/get-events':json.dumps(events)})
        verdi(r);session=next(iter(r.result.sessions.values()))
        self.assertEqual(session['booking_url'],'https://tickets.example/seats/123/');self.assertEqual(session['duration_minutes'],124)

    def test_artistic_hidden_events_are_read_and_private_events_excluded(self):
        events=[dict(**{'@type':'Event'},name=title,startDate='2026-11-21T19:00:00+01:00',url='https://cine.example/sesion/'+str(i)) for i,title in enumerate(['SALA 2: AKIRA (1988) Doblada al español','Pase PRIVADO','ESTUDIOS DE CINE'])]
        r=reader('artistic','<script type="application/ld+json">'+json.dumps({'@graph':events})+'</script><footer>Piano en directo</footer>')
        artistic(r);sessions,movies=r.result.finish();self.assertEqual(len(sessions),1)
        self.assertEqual(sessions[0]['title'],'AKIRA (1988)');self.assertEqual(sessions[0]['special_tags'],[])

    def test_cineteca_explicit_pases_not_first_and_last_date_range(self):
        programme='<article class="node--type-activity"><div class="field-name-node-title"><a href="/programacion/cobijo">Cobijo</a></div></article>'
        detail='<div class="field-name-node-title"><h2>Cobijo</h2></div><div class="field--name-field-director">Adrián Silvestre</div><div class="field-name-field-duration">(92\')</div><div class="sb-sessions"><h2 class="sb-sessions__date-month">Noviembre</h2><h4 class="sb-sessions__date-day">Miércoles 11</h4><ul class="sb-sessions__date-hours"><li class="sb-sessions__date-hours-hour">20:00 h</li><li class="sb-sessions__date-hours-space">Sala Azcona</li></ul><h4 class="sb-sessions__date-day">Viernes 13</h4><ul class="sb-sessions__date-hours"><li class="sb-sessions__date-hours-hour">18:00 h</li></ul></div>'
        r=reader('cineteca',programme,{'https://cinema.example/programacion/cobijo':detail});cineteca(r)
        sessions,movies=r.result.finish();self.assertEqual(len(sessions),2);self.assertEqual(len(movies),1)
        self.assertEqual({s['start'][:10] for s in sessions},{'2026-11-11','2026-11-13'})

    def test_explicit_year_can_resolve_akira_without_director_but_not_a_remake(self):
        from test_tmdb import movie
        self.assertEqual(identity_match({'title':'Akira (1988)'},[movie()])[0]['tmdb_id'],149)
        self.assertIsNone(identity_match({'title':'Akira'},[movie()])[0])
        self.assertIsNone(identity_match({'title':'Akira (1988)'},[movie(),movie(id=2)])[0])
        self.assertIsNone(identity_match({'title':'Akira (2016)'},[movie()])[0])

    def test_director_inverted_and_multiple_credits(self):
        from test_tmdb import movie
        self.assertIsNotNone(identity_match({'title':'Akira','director':'Otomo, Katsuhiro'},[movie()])[0])
        self.assertIsNone(identity_match({'title':'Akira','director':'Otomo'},[movie()])[0])
        joint=movie();joint['directors'].append('Otra directora')
        self.assertIsNotNone(identity_match({'title':'Akira','director':'Katsuhiro Otomo'},[joint])[0])
        self.assertIsNotNone(identity_match({'title':'Akira','director':'Otra directora, Otomo Katsuhiro'},[joint])[0])

    def test_capitol_uses_session_tabs_instead_of_inventing_every_date_in_range(self):
        page='<a href="/es/cartelera/akira/">Akira</a>'
        detail='<h1>Akira</h1><div class="item"><small>Director</small><span>Katsuhiro Otomo</span></div><p>124 MIN</p><div class="m-section" data-tabs="20261119"><a href="https://tickets.example/?perfCode=123">16:30 (2D)</a></div>'
        r=reader('capitol',page,{'https://cinema.example/es/cartelera/akira/':detail});capitol(r)
        session=next(iter(r.result.sessions.values()));self.assertEqual(session['start'],'2026-11-19T16:30:00+01:00')
        self.assertEqual(session['director'],'Katsuhiro Otomo');self.assertEqual(len(r.result.sessions),1)

    def test_morasol_reads_explicit_advance_dates_and_excludes_private_passes(self):
        session=dict(Id=1,NombreEvento='Concierto',FechaSesion='01/01/2027 (*6)',Hora=' 18:30',Sala='1')
        page="<script>addToJSON('s', "+json.dumps({'1':session,'2':dict(session,Id=2,PasePrivado=1)})+")</script>"
        r=reader('morasol',page);morasol(r)
        self.assertEqual(len(r.result.sessions),1)
        self.assertEqual(next(iter(r.result.sessions.values()))['start'],'2027-01-01T18:30:00+01:00')

if __name__=='__main__':unittest.main()
