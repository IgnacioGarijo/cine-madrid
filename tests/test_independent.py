import unittest
from pathlib import Path
from datetime import date
from src.adapters import Reader
from src.adapters_independent import publicine_embajadores
from src.core import Incidents

FIX = Path(__file__).parent / 'fixtures' / 'independent'
BASE = 'https://www.publicine.net/cartelera-cine/madrid/'

def make_reader(cid, fixture):
    r = Reader({'id':cid, 'url':'https://cinesembajadores.es/madrid/', 'schedule_url':BASE+('cines-embajadores-rio' if cid.endswith('-r-o') else 'cines-embajadores')}, date(2026,11,12), Incidents())
    html = (FIX / fixture).read_text(encoding='utf8')
    r.get = lambda url: html
    return r

class IndependentTests(unittest.TestCase):
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
