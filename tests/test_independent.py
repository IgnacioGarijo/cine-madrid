import unittest
from pathlib import Path
from datetime import date
from src.adapters import Reader
from src.adapters_independent import publicine_embajadores, reserva_embajadores
from src.core import Incidents

FIX = Path(__file__).parent / 'fixtures' / 'independent'
BASE = 'https://www.publicine.net/cartelera-cine/madrid/'

def make_reader(cid, fixture):
    r = Reader({'id':cid, 'url':'https://cinesembajadores.es/madrid/', 'schedule_url':BASE+('cines-embajadores-rio' if cid.endswith('-r-o') else 'cines-embajadores')}, date(2026,11,12), Incidents())
    html = (FIX / fixture).read_text(encoding='utf8')
    r.get = lambda url: html
    return r

class IndependentTests(unittest.TestCase):
    def test_ticket_schedules_include_future_dates_and_reject_other_venues(self):
        import json
        index='https://www.reservaentradas.com/cine/madrid/cineembajadores'
        detail='https://www.reservaentradas.com/sesiones/madrid/cineembajadores/akira/123/'
        metadata=BASE+'cines-embajadores'
        r=Reader({'id':'cines-embajadores','schedule_url':index,'metadata_url':metadata},date(2026,11,16),Incidents())
        listings='<h1>CINE EMBAJADORES</h1><a href="http://www.reservaentradas.com:443/reservaentradas/sesiones/madrid/cineembajadores/akira/123/">Akira</a>'
        records={'884':{'location_id':'cineembajadores','item_name':'Akira (VOSE)','item_category4':'VOSE','item_category5':'Sala 1','session_datetime':'2026-12-21T19:30'}}
        page='<script>window.reAnalyticsSesiones = '+json.dumps(records)+';</script><a class="sesion" href="http://www.reservaentradas.com:443/reservaentradas/entrada/madrid/cineembajadores/akira/884/?step=2">19:30</a>'
        extra='<div id="adreca"><strong>Cines Embajadores</strong>Glorieta Santa María de la Cabeza 5</div><div class="sessions"><a href="/a"><h2>Akira</h2></a><span class="up">Director</span>Katsuhiro Otomo</div>'
        r.get=lambda url:{index:listings,detail:page,metadata:extra}[url]
        reserva_embajadores(r);sessions,movies=r.result.finish()
        self.assertEqual(len(sessions),1);self.assertEqual(sessions[0]['start'],'2026-12-21T19:30:00+01:00')
        self.assertEqual(sessions[0]['version'],'VOSE');self.assertEqual(movies[0]['director'],'Katsuhiro Otomo')
        self.assertTrue(sessions[0]['booking_url'].startswith('https://www.reservaentradas.com/entrada/madrid/cineembajadores/'))
        records['884']['location_id']='cineembajadoresrio';page='<script>window.reAnalyticsSesiones = '+json.dumps(records)+';</script>'
        r=Reader({'id':'cines-embajadores','schedule_url':index,'metadata_url':metadata},date(2026,11,16),Incidents())
        r.get=lambda url:{index:listings,detail:page,metadata:extra}[url]
        reserva_embajadores(r);self.assertFalse(r.result.sessions);self.assertTrue(r.incidents.current)
    def test_distinct_venues_and_explicit_times(self):
        a = make_reader('cines-embajadores','pub1.html'); b = make_reader('cines-embajadores-r-o','pub2.html')
        publicine_embajadores(a); publicine_embajadores(b)
        sa, _ = a.result.finish(); sb, _ = b.result.finish()
        self.assertTrue(sa); self.assertTrue(sb)
        self.assertTrue(all(x['cinema_id']=='cines-embajadores' for x in sa))
        self.assertTrue(all(x['cinema_id']=='cines-embajadores-r-o' for x in sb))
        self.assertIn('2026-11-12T16:00:00+01:00', [x['start'] for x in sa])
        self.assertEqual(sa[0]['director'], 'Alessandro Carloni, Erica Rivinoja')
        self.assertEqual(sa[0]['duration_minutes'], 107)
        self.assertTrue(sa[0]['booking_url'].startswith(BASE.replace('/cartelera-cine/madrid/','/venda/')))
    def test_wrong_venue_fails_closed(self):
        r=make_reader('cines-embajadores-r-o','pub1.html')
        with self.assertRaises(ValueError): publicine_embajadores(r)
    def test_ambiguous_time_is_omitted(self):
        r=make_reader('cines-embajadores','pub1.html')
        old=r.get; r.get=lambda u:old(u).replace('16.00','sin hora')
        publicine_embajadores(r)
        self.assertNotIn('2026-11-12T16:00:00+01:00', [x['start'] for x in r.result.sessions.values()])

if __name__=='__main__': unittest.main()
