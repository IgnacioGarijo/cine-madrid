import unittest
from datetime import date
from src.adapters import Reader,read_cinema,ADAPTERS
from src.adapters_extra import callao,berlanga
from src.core import Incidents
from unittest.mock import patch


class ExtraAdaptersTests(unittest.TestCase):
    def reader(self,html):
        r=Reader({'id':'test','url':'https://official.example/'},date(2026,11,12),Incidents())
        r.get=lambda url:html
        return r

    def test_callao_explicit_dates_not_closed_days_or_undated_trailers(self):
        html='''<div class="et_pb_column"><div class="et_pb_image"><a href="/akira/"><img alt="Akira"></a></div>
        <div class="et_pb_text_inner"><p><strong>Akira</strong></p><p>Jueves 12/11 ---</p><p>Viernes 13/11 <strong>20:10, 22:40</strong></p><p>Lunes 16 /11 18:00</p><p>SÓLO VERSIÓN EN CASTELLANO</p></div>
        <a href="https://www.reservaentradas.com/sesiones/madrid/callao/akira/1">Comprar</a></div><p>Director: Katsuhiro Otomo</p><p>Duración: 124 min</p>'''
        r=self.reader(html);callao(r);sessions,movies=r.result.finish()
        self.assertEqual(len(sessions),3);self.assertEqual(sessions[0]['start'],'2026-11-13T20:10:00+01:00')
        self.assertEqual(movies[0]['director'],'Katsuhiro Otomo');self.assertEqual(sessions[-1]['version'],'Doblada')

    def test_berlanga_filters_theatre_and_does_not_expand_cycle_ranges(self):
        def card(category,label,title='Akira'):
            return f'<div class="card"><div class="categoria-sala-berlanga">{category}</div><h5 class="card-title"><a href="/{title}/">{title}</a></h5><p class="card-text-date">{label}</p><p class="card-text-time">Katsuhiro Otomo | 1988 | 124\u2019</p></div>'
        r=self.reader(card('Música','12 de Noviembre - 19:00h')+card('Cine','13 de Noviembre - 18:15h')+card('Cine','14 de Noviembre al 18 de Noviembre - 20:00h','Ciclo'))
        berlanga(r);sessions,movies=r.result.finish();self.assertEqual(len(sessions),1)
        self.assertEqual(sessions[0]['start'],'2026-11-13T18:15:00+01:00');self.assertEqual(movies[0]['duration_minutes'],124)
        self.assertTrue(any(i['code']=='partial_read' for i in r.incidents.current.values()))

    def test_empty_requires_a_recognized_structure_and_explicit_confirmation(self):
        def empty(reader):reader.result.empty_confirmed=True
        with patch.dict(ADAPTERS,{'test-empty':empty,'test-broken':lambda reader:None}):
            config={'id':'empty','url':'https://official.example/','adapter':'test-empty'}
            self.assertEqual(read_cinema(config,date(2026,11,12),Incidents())[0],[])
            with self.assertRaises(ValueError):read_cinema({**config,'adapter':'test-broken'},date(2026,11,12),Incidents())
        with self.assertRaises(ValueError):berlanga(self.reader('<p>Nueva web</p>'))
