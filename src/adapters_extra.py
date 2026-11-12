"""Official timetables for venues missing from the original inventory."""
import re
from datetime import datetime,timedelta
from urllib.parse import urljoin
from .adapters import text,minutes,spanish_day
from .sources import parse_day,event_tags


def callao(reader):
    url=reader.cinema['url'];soup=reader.soup(url);recognized=False;ambiguous=False
    for column in soup.select('.et_pb_column'):
        image=column.select_one('.et_pb_image a[href]')
        booking=column.select_one('a[href*="reservaentradas.com/sesiones/madrid/callao/"]')
        if not image or not booking:continue
        labels=[text(p) for p in column.select('.et_pb_text_inner p')]
        dated=[label for label in labels if re.search(r'\b\d{1,2}\s*/\s*\d{1,2}',label)]
        if not dated:continue # Advance trailers without a published timetable.
        recognized=True;title=''
        for p in column.select('.et_pb_text_inner p'):
            if p.find('strong') and not re.search(r'\d|[_—-]{2,}',text(p)):
                title=text(p);break
        if not title:
            title=image.img.get('alt','') if image.img else ''
        film_url=urljoin(url,image['href']);director='';duration=None
        try:
            detail=reader.soup(film_url)
            for p in detail.select('p'):
                label=text(p)
                if re.match(r'Director(?:a)?\s*:',label,re.I):director=label.split(':',1)[1].strip()
                if re.match(r'Duraci[oó]n\s*:',label,re.I):duration=minutes(label)
        except Exception:reader.partial(film_url,'No se pudo consultar la ficha oficial de la película.',film_url)
        description=text(column)
        version='Doblada' if re.search(r'versi[oó]n en castellano',description,re.I) else 'VOSE' if 'VOSE' in description.upper() else 'Sin especificar'
        for label in dated:
            try:
                raw=re.sub(r'\s*/\s*','/',label)
                day=parse_day(raw,reader.today)
                hours=re.findall(r'\b(\d{1,2}):(\d{2})\b',label)
                for hour,minute in hours:
                    if int(hour)>25 or int(minute)>59:raise ValueError('Hora no válida')
                    start=datetime.combine(day,datetime.min.time())+timedelta(hours=int(hour),minutes=int(minute))
                    reader.result.add(title,start,film_url,director,duration,urljoin(url,booking['href']),version,tags=event_tags(description))
            except ValueError:
                ambiguous=True;reader.partial(label,'No se reconoce una fecha u hora de Callao.',url)
    if not recognized:raise ValueError('No se reconoce la cartelera fechada de Callao')
    if not reader.result.sessions and not ambiguous:reader.result.empty_confirmed=True


def berlanga(reader):
    url=reader.cinema['url'];soup=reader.soup(url);cards=soup.select('.card:has(.card-title)')
    if not cards:raise ValueError('No se reconoce el programa de actividades de Sala Berlanga')
    ambiguous=False
    for card in cards:
        if text(card.select_one('.categoria-sala-berlanga')).casefold()!='cine':continue
        title_node=card.select_one('.card-title a[href]');label=text(card.select_one('.card-text-date'))
        if not title_node:ambiguous=True;reader.partial('title','Actividad de cine sin título enlazado.',url);continue
        film_url=urljoin(url,title_node['href']);meta=text(card.select_one('.card-text-time')).split('|')
        director=meta[0].strip() if len(meta)>=2 else ''
        if director.casefold()=='varios autores':director=''
        duration=minutes(meta[-1]) if meta else None
        try:
            # Each card announces a single explicit performance, never a cycle range.
            if re.search(r'\bal\b',label,re.I):raise ValueError('Rango de ciclo sin pases individuales')
            day=spanish_day(re.sub(r'\bde\s+','',label,flags=re.I),reader.today)
            hours=re.findall(r'\b(\d{1,2}):(\d{2})',label)
            if not hours:raise ValueError('Actividad sin hora')
            booking=card.select_one('.card-text-comprar a[href]')
            for hour,minute in hours:
                if int(hour)>25 or int(minute)>59:raise ValueError('Hora no válida')
                start=datetime.combine(day,datetime.min.time())+timedelta(hours=int(hour),minutes=int(minute))
                reader.result.add(text(title_node),start,film_url,director,duration,urljoin(url,booking['href']) if booking else film_url,tags=event_tags(text(card)))
        except ValueError:
            ambiguous=True;reader.partial(film_url,'Actividad de cine sin fecha y hora individuales reconocibles.',film_url)
    if not reader.result.sessions and not ambiguous:reader.result.empty_confirmed=True
