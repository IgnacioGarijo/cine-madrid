"""Explicit schedules from official Sala Equis and Pequeño Cine Estudio pages."""
import re
import json
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from .adapters import text, minutes, json_nodes
from .sources import parse_day, event_tags
from .core import normalize


def _equis_booking(url):
    parsed = urlparse(url)
    return (parsed.scheme == 'https' and parsed.netloc == 'kinetike.com:83'
            and parsed.path == '/views/sesionesFuturas.aspx'
            and parse_qs(parsed.query).get('cine') == ['EQUIS']
            and len(parse_qs(parsed.query).get('idPelicula', [])) == 1)


def sala_equis(reader):
    index = reader.cinema.get('schedule_url', 'https://salaequis.es/taquilla/')
    soup = reader.soup(index)
    links = sorted({urljoin(index, a['href']) for a in soup.select('a[href]')
                    if '/ciclos/' in a['href'] and text(a) not in ('Ciclos', '')
                    and urlparse(urljoin(index, a['href'])).netloc == 'salaequis.es'})
    if not links:
        raise ValueError('No se reconoce la taquilla de Sala Equis')
    for url in links:
        try:
            film = reader.soup(url)
            title = text(film.select_one('h1.product_title'))
            anchor = next((a for a in film.select('a[href]') if _equis_booking(a['href'])), None)
            if not title or anchor is None:
                raise ValueError('Ficha sin título o enlace oficial de sesiones Kinetike')
            booking = anchor['href']
            summary = film.select_one('.shortDescription')
            lines = summary.get_text('\n', strip=True).splitlines() if summary else []
            director = next((line.split('/')[0].strip() for line in lines if re.search(r'/.*?/.*?\d{4}', line)), '')
            detail = text(summary)
            duration = minutes(detail)
            version = 'VOSE' if re.search(r'\bVOSE\b', detail, re.I) else 'Sin especificar'
            schedule = reader.soup(booking)
            buttons = schedule.select('input[type=submit][value="SESIONES"]')
            if not buttons:
                raise ValueError('Kinetike no publica fechas verificables para esta ficha')
            form = schedule.select_one('form[method=post]')
            if form is None or urljoin(booking, form.get('action', '')) != booking:
                raise ValueError('Formulario de consulta Kinetike no reconocido')
            for button in buttons:
                row = button.find_parent(class_='row')
                dates = re.findall(r'\b\d{1,2}/\d{1,2}/\d{4}\b', text(row))
                if len(dates) != 1 or not re.fullmatch(r'\d{2}', button.get('name', '')):
                    reader.partial(title, 'Fecha de Kinetike ambigua.', booking); continue
                day = parse_day(dates[0], reader.today)
                if day < reader.today:
                    continue
                # Only the public date selector, never a session or checkout control.
                payload = {i['name']: i.get('value', '') for i in schedule.select('input[type=hidden][name]')}
                payload[button['name']] = 'SESIONES'
                response = BeautifulSoup(reader.fetcher.post(booking, payload), 'html.parser')
                reader.result.pages.append(booking)
                panel = response.select_one('#PanelSesiones' + button['name'])
                if panel is None:
                    reader.partial(title, 'No se reconoce el panel de horas de la fecha solicitada.', booking); continue
                hours = panel.select('input[type=submit][value]')
                if not hours:
                    reader.partial(title, 'Fecha publicada sin horas verificables.', booking); continue
                for hour in hours:
                    match = re.fullmatch(r'(\d{1,2}):(\d{2})', hour['value'])
                    if not match or int(match[1]) > 23 or int(match[2]) > 59:
                        reader.partial(title, 'Hora de Kinetike no reconocida.', booking); continue
                    start = datetime.combine(day, datetime.min.time()) + timedelta(hours=int(match[1]), minutes=int(match[2]))
                    reader.result.add(title, start, url, director, duration, booking, version=version,
                                      tags=event_tags(title), work_id='kinetike:' + parse_qs(urlparse(booking).query)['idPelicula'][0])
        except Exception as exc:
            reader.partial(url, str(exc), url)


def pequeno_cine(reader):
    url = reader.cinema.get('schedule_url', 'https://www.pcineestudio.es/en-cartel')
    soup = reader.soup(url)
    blocks = soup.select('.wixui-repeater__item')
    recognized = 0
    complete = True
    for block in blocks:
        rich = block.select('[data-testid="richTextElement"]')
        info = next((n for n in rich if re.match(r'Título original\s', text(n))), None)
        if info is None:
            continue
        lines = info.get_text('\n', strip=True).splitlines()
        title = re.sub(r'^Título original\s*', '', lines[0]).strip()
        director = next((re.sub(r'^Dirección\s*', '', x).strip() for x in lines if x.startswith('Dirección')), '')
        duration = minutes(text(info))
        schedule = next((n for n in rich if re.search(r'\d{2}/\d{2}\s*-', text(n))), None)
        if schedule is None or not title:
            complete = False
            reader.partial(title, 'Ficha sin horarios explícitos reconocibles.', url); continue
        recognized += 1
        booking = next((urljoin(url, a['href']) for a in block.select('a[href]') if text(a) == 'comprar entradas'), url)
        for line in schedule.get_text('\n', strip=True).splitlines():
            match = re.fullmatch(r'[LMXJVSD]?\s*(\d{1,2}/\d{1,2})\s*-\s*(\d{1,2})[.:](\d{2})h?', line)
            if not match or int(match[2]) > 23 or int(match[3]) > 59:
                complete = False
                reader.partial(title, 'Horario ambiguo: ' + line, url); continue
            day = parse_day(match[1], reader.today)
            start = datetime.combine(day, datetime.min.time()) + timedelta(hours=int(match[2]), minutes=int(match[3]))
            reader.result.add(title, start, url, director, duration, booking, tags=event_tags(title))
    if not recognized:
        raise ValueError('No se reconoce la programación de Pequeño Cine Estudio')
    if complete and not reader.result.sessions:
        reader.result.empty_confirmed = True


def ocine_caleido(reader):
    """Read the official public ticketing API, without selecting any session."""
    origin = 'https://tickets.ocineurbancaleido.es/'
    api = origin + 'api/v1/sessions'
    data = json.loads(reader.fetcher.post(api, json={'token': '', 'idioma': 'es', 'urlWeb': origin + '?nocap=1'}))
    reader.result.pages.append(api)
    if normalize(data.get('nomCinema', '')) != 'ocineurbancaleido':
        raise ValueError('La taquilla no identifica OCINE Urban Caleido')
    if not all(isinstance(data.get(key), list) for key in ('pelicules', 'estrenes', 'anticipades')):
        raise ValueError('Estructura de cartelera OCINE no reconocida')
    films = {str(f['id']): f for key in ('pelicules', 'estrenes', 'anticipades') for f in data[key]}
    complete = True
    for ident in films:
        url = origin + 'api/v1/pelicula/' + ident + '?lang=es'
        try:
            detail = json.loads(reader.get(url))
            if str(detail.get('id')) != ident or not detail.get('titol'):
                raise ValueError('Ficha OCINE no corresponde a la película solicitada')
            variants = detail.get('subPelicules') if detail.get('esGrup') else [detail]
            if not isinstance(variants, list):
                raise ValueError('Variantes de película OCINE no reconocidas')
            for variant in variants:
                sessions = variant.get('sessions')
                if not isinstance(sessions, list):
                    raise ValueError('Sesiones OCINE no reconocidas')
                props = ' '.join(variant.get('propietatsDesc', [])) + ' ' + variant.get('titol', '')
                # Version is variant-level; the group can include both VOSE and other versions.
                version = 'VOSE' if re.search(r'VOSE|Versión VOSE', props, re.I) else 'Sin especificar'
                formats = [v for v in ('ATMOS', '3D', '4D', 'Screen X', 'Sala ICE', 'Infinity Vision') if v.casefold() in props.casefold()]
                for session in sessions:
                    day = datetime.strptime(session['data'], '%Y-%m-%d').date()
                    hour = datetime.strptime(session['hora'], '%H:%M:%S').time()
                    duration = int(detail.get('durada') or 0) or None
                    human_url = origin + '#/DetallPelicula/' + ident
                    reader.result.add(detail['titol'], datetime.combine(day, hour), human_url,
                        detail.get('director') or '', duration, human_url,
                        version=version, room=session.get('nomSala') or str(session.get('sala') or ''),
                        native=session['planificacio'], format=', '.join(formats) or None,
                        tags=event_tags(detail['titol']), work_id='ocine:' + ident)
        except Exception as exc:
            complete = False
            reader.partial(ident, str(exc), url)
    if complete and not reader.result.sessions:
        reader.result.empty_confirmed = True


def palacio_prensa(reader):
    """SensaCine's explicit HTML sessions; calendar-only days remain partial."""
    url = reader.cinema.get('schedule_url', 'https://www.sensacine.com/cines/cine/E0559/')
    soup = reader.soup(url)
    venues = [n for n in json_nodes(soup) if n.get('@type') == 'MovieTheater']
    if len(venues) != 1:
        raise ValueError('No se reconoce la identidad del cine en SensaCine')
    venue = venues[0]; address = venue.get('address', {})
    if (normalize(venue.get('name', '')) != 'cinespalaciodelaprensa'
            or normalize(address.get('streetAddress', '')) != 'plazadelcallao4'
            or normalize(address.get('addressLocality', '')) != 'madrid'
            or str(venue.get('screenCount')) != '3'):
        raise ValueError('La fuente no identifica las tres salas de Palacio de la Prensa en Madrid')
    cards = soup.select('.movie-card-theater')
    state = soup.select_one('#theaterpage-showtimes-index-ui')
    if not cards or state is None:
        raise ValueError('No se reconoce la programación de SensaCine')
    published = set(json.loads(state.get('data-showtimes-dates', '[]')))
    read_dates = set()
    for card in cards:
        title = text(card.select_one('.meta-title-link'))
        director = re.sub(r'^Dirigida por\s*', '', text(card.select_one('.meta-body-direction')))
        if not title:
            continue
        for group in card.select('.showtimes-version'):
            label = text(group.select_one('.text'))
            version = 'Doblada' if re.search(r'versión doblada', label, re.I) else 'VOSE' if re.search(r'VOSE|subtitulad[ao].*espa[ñn]ol', label, re.I) else 'Sin especificar'
            for session in group.select('[data-showtime-time]'):
                raw = session['data-showtime-time']
                try:
                    start = datetime.fromisoformat(raw)
                    if start.tzinfo is None:
                        raise ValueError('Hora sin zona')
                    read_dates.add(start.date().isoformat())
                except ValueError:
                    reader.partial(title, 'Fecha/hora ISO no reconocida: ' + raw, url); continue
                reader.result.add(title, start, url, director, minutes(text(card.select_one('.meta-body-info'))),
                    booking=url, version=version, native=session.get('data-showtime-id'), tags=event_tags(title))
    unread = sorted(day for day in published - read_dates if day >= reader.today.isoformat())
    if unread:
        reader.partial('calendar', 'SensaCine anuncia otras fechas sin horas leídas en el HTML: ' + ', '.join(unread)
            + '. Su ruta de configuración del lector de fechas está prohibida por robots; cobertura parcial.', url)
