"""Explicit screenings from Filmoteca Española's official ticketing channel."""
import re
from datetime import date, datetime, time
from urllib.parse import urljoin, urlparse, parse_qs

from .adapters import text


def filmoteca(reader):
    """Read every linked results page; never turn a cycle date range into screenings."""
    origin = reader.cinema['url']
    pending = [origin]
    seen = set()
    valid_structure = False
    uncertain = False
    while pending:
        url = pending.pop(0)
        if url in seen:
            continue
        if len(seen) >= 100:
            raise ValueError('La paginación de Filmoteca supera el límite de seguridad.')
        soup = reader.soup(url)
        seen.add(url)
        products = soup.select('.producto')
        dated = soup.select('[data-fecha] .producto')
        if not products or not dated:
            raise ValueError('No se reconoce la estructura fechada de Filmoteca.')
        valid_structure = True
        for link in soup.select('a[href*="pagina="]'):
            target = urljoin(url, link['href'].strip())
            if urlparse(target).netloc != urlparse(origin).netloc:
                raise ValueError('Paginación de Filmoteca fuera del dominio de origen.')
            if target not in seen and target not in pending:
                pending.append(target)
        for card in dated:
            title = text(card.select_one('h2.titulo'))
            director = text(card.select_one('h3.subtitulo'))
            # The seller also advertises talks, passes, and bundled events.
            # A year and an attributed director are conservative film evidence.
            day_node = card.find_parent(attrs={'data-fecha': True})
            if not title or not director or not re.search(r'\((?:18|19|20)\d{2}\)', title):
                try:
                    if date.fromisoformat(day_node['data-fecha']) >= reader.today:
                        uncertain = True
                        if title and not re.search(r'\b(?:charla|presentaci[oó]n de libro|coloquio|conferencia|bono)\b', title, re.I):
                            reader.partial(title, 'Posible programa de cine sin título y datos de película inequívocos.', url)
                except (TypeError, ValueError):
                    uncertain = True
                continue
            desc = text(card.select_one('.descripcion'))
            clock = re.search(r'\b(?:a\s+las\s+)(\d{1,2}):(\d{2})\s*h?', desc, re.I)
            link = card.select_one('a.mas-info[href]') or card.select_one('a[href*="/entradas/"]')
            try:
                day = date.fromisoformat(day_node['data-fecha'])
                if not clock or not link:
                    raise ValueError('Faltan hora o enlace de la sesión')
                start = datetime.combine(day, time(int(clock[1]), int(clock[2])))
            except (TypeError, ValueError) as exc:
                uncertain = True
                reader.partial(title, 'No se pudo identificar la fecha u hora: ' + str(exc), url)
                continue
            room = re.search(r'\bSala\s+([\w]+)', desc, re.I)
            detail = urljoin(url, link['href'].strip())
            booking_node = card.select_one('a[href*="/entradas/"]')
            booking = urljoin(url, booking_node['href'].strip()) if booking_node else detail
            reader.result.add(title, start, detail, director=director, booking=booking,
                              room=room[1] if room else '')
    if valid_structure and not reader.result.sessions and not uncertain:
        reader.result.empty_confirmed = True


def _spanish_date(raw):
    from .adapters import MONTHS
    from .core import normalize
    match = re.search(r'(\d{1,2})\s+(?:de\s+)?([A-Za-zÁÉÍÓÚáéíóú]+)\s+(?:de\s+)?(\d{4})', raw, re.I)
    if not match:
        raise ValueError('Fecha completa no reconocida: ' + raw[:100])
    month = MONTHS.get(normalize(match[2]))
    if not month:
        raise ValueError('Mes no reconocido: ' + match[2])
    return date(int(match[3]), month, int(match[1]))


def casa_america(reader):
    index = reader.soup(reader.cinema['url'])
    cards = index.select('article.node--view-mode-card')
    if not cards:
        raise ValueError('No se reconocen las fichas de la agenda de cine.')
    uncertain = False
    for card in cards:
        link = card.select_one('h3 a[href]')
        if not link:
            uncertain = True
            continue
        url = urljoin(reader.cinema['url'], link['href'])
        try:
            soup = reader.soup(url)
        except Exception:
            uncertain = True
            reader.partial(text(link), 'No se pudo leer la ficha de cine.', url)
            continue
        article = soup.select_one('article.node--view-mode-full')
        if not article:
            uncertain = True
            reader.partial(text(link), 'No se reconoce la ficha de cine.', url)
            continue
        body = article.select_one('.field--name-field-cuerpo')
        title = text(article.select_one('h1.titulo'))
        content = text(body)
        # Restrict to individual film fichas with a screening and film synopsis.
        if not re.search(r'proyecci[oó]n', content, re.I):
            continue
        if not re.search(r'\bsinopsis\b', content, re.I):
            uncertain = True
            reader.partial(title, 'Proyección sin ficha cinematográfica inequívoca; no se desglosa.', url)
            continue
        match = re.search(r'fecha\s+y\s+hora\s*:\s*(.{0,220})', content, re.I)
        if not match:
            uncertain = True
            reader.partial(title, 'Ficha sin fecha y hora explícitas reconocibles.', url)
            continue
        section = match[1]
        try:
            day = _spanish_date(section)
            clock = re.search(r'\b(\d{1,2}):(\d{2})\b', section)
            if not clock: raise ValueError('Hora ausente')
            start = datetime.combine(day, time(int(clock[1]), int(clock[2])))
        except ValueError as exc:
            uncertain = True
            reader.partial(title, str(exc), url)
            continue
        if not re.search(r'casa\s+de\s+am[eé]rica', section, re.I):
            uncertain = True
            continue
        director = re.search(r'\bDirector(?:a)?\s*:\s*([^:]{1,100}?)(?:\s+Guion\b|\s+Int[eé]rpretes\b|\s+Sinopsis\b)', content, re.I)
        room = re.search(r'\bSala\s+([\wÁÉÍÓÚáéíóú]+)', section, re.I)
        reader.result.add(title, start, url, director=director[1].strip() if director else '', room=room[1] if room else '')
    if not reader.result.sessions and not uncertain:
        reader.result.empty_confirmed = True


def instituto_frances(reader):
    soup = reader.soup(reader.cinema['url'])
    links = {urljoin(reader.cinema['url'], a['href']) for a in soup.select('a[href]') if a.select_one('.category_event-cine') and '/madrid/evento/' in a['href']}
    if not soup.select('.item__categories'):
        raise ValueError('No se reconoce la agenda del Instituto Francés.')
    uncertain = False
    for url in sorted(links):
        try:
            detail = reader.soup(url)
        except Exception:
            uncertain = True
            reader.partial(url, 'No se pudo leer la ficha del evento.', url)
            continue
        title = text(detail.select_one('.intro__title h1'))
        venue = text(detail.select_one('.location__name'))
        sessions = detail.select('.intro__sessions .session')
        if not title or not venue or not sessions:
            uncertain = True
            reader.partial(url, 'Ficha sin título, sede o sesiones reconocibles.', url)
            continue
        if not re.search(r'institut\s+fran[çc]ais\s+de\s+madrid', venue, re.I):
            continue
        # A named individual projection, excluding generic cycles and short-film programmes.
        match = re.search(r'proyecci[oó]n\s*[«“\"]([^»”\"]+)[»”\"](?:\s+de\s+(.+))?', title, re.I)
        if not match:
            uncertain = True
            if re.search(r'proyecci[oó]n|cortometraje|\bcine\b', title, re.I):
                reader.partial(title, 'Programa de cine sin película individual inequívoca; no se desglosa.', url)
            continue
        film = match[1].strip(); director = (match[2] or '').strip()
        for session in sessions:
            try:
                day = _spanish_date(text(session.select_one('.date')))
                clock = re.fullmatch(r'(\d{1,2}):(\d{2})', text(session.select_one('.time')))
                if not clock: raise ValueError('Hora ausente o ambigua')
                start = datetime.combine(day, time(int(clock[1]), int(clock[2])))
            except ValueError as exc:
                uncertain = True
                reader.partial(film, str(exc), url)
                continue
            reader.result.add(film, start, url, director=director, room=venue)
    if not reader.result.sessions and not uncertain:
        reader.result.empty_confirmed = True


def academia_cine(reader):
    index = reader.soup(reader.cinema['url'])
    cards = index.select('.grid-wrapper')
    if not cards:
        raise ValueError('No se reconoce la agenda de la Academia de Cine.')
    uncertain = False
    for card in cards:
        link = card.select_one('a[href*="/sesion/"]')
        if not link:
            uncertain = True
            continue
        url = urljoin(reader.cinema['url'], link['href'])
        try:
            detail = reader.soup(url)
        except Exception:
            uncertain = True
            reader.partial(url, 'No se pudo leer la sesión de la Academia.', url)
            continue
        rows = {text(row.select_one('th')): text(row.select_one('td')) for row in detail.select('table tr') if row.select_one('th') and row.select_one('td')}
        # Movie table exists for films, not podcasts and general activities.
        if not all(k in rows for k in ('Duración', 'Nacionalidad')) or not detail.find(string=re.compile(r'^\s*Sinopsis\s*$', re.I)):
            uncertain = True
            continue
        heading = card.select_one('.text-light > p')
        title = text(heading)
        body = text(card)
        try:
            day = _spanish_date(body)
            clock = re.search(r'\ba\s+las\s+(\d{1,2}):(\d{2})', body, re.I)
            if not clock or not title: raise ValueError('Sesión sin título u hora reconocible')
            start = datetime.combine(day, time(int(clock[1]), int(clock[2])))
        except ValueError as exc:
            uncertain = True
            reader.partial(title or url, str(exc), url)
            continue
        if 'Sala de proyecciones de la Academia de Cine' not in body:
            uncertain = True
            continue
        duration_match = re.search(r'\d+', rows['Duración'])
        reader.result.add(title, start, url, duration=int(duration_match[0]) if duration_match else None, room='Sala de proyecciones', native=url.rstrip('/').split('/')[-1])
    if not reader.result.sessions and not uncertain:
        reader.result.empty_confirmed = True


def reina_sofia(reader):
    """Museum screening agenda; multi-film programmes remain unreported."""
    index = reader.soup(reader.cinema['url'])
    anchors = index.select('a[href^="/actividad/"] [class*="SnippetMedium-module--dates--"]')
    if not anchors:
        raise ValueError('No se reconoce la programación de cine del Reina Sofía.')
    urls = set(); uncertain = False
    for label in anchors:
        raw = text(label)
        dates = re.findall(r'\d{1,2}\s+[A-Za-zÁÉÍÓÚáéíóú]+\s+\d{4}', raw)
        try:
            if not dates: raise ValueError('Fecha sin año')
            last = _spanish_date(dates[-1])
        except ValueError:
            uncertain = True
            continue
        if last >= reader.today:
            urls.add(urljoin(reader.cinema['url'], label.find_parent('a')['href']))
    for url in sorted(urls):
        try:
            page = reader.soup(url)
        except Exception:
            uncertain = True
            reader.partial(url, 'No se pudo leer la ficha de programación.', url)
            continue
        details = page.select_one('#stickyAside')
        items = page.select('[class*="ScheduleItem-module--scheduleItem--"]')
        if not details or not items:
            uncertain = True
            reader.partial(url, 'No se reconocen los datos o la agenda de esta ficha.', url)
            continue
        location = next((text(x.select_one('dd')) for x in details.select('dl > div') if 'Localización' in text(x.select_one('dt'))), '')
        if location != 'Edificio Sabatini, Cine':
            continue
        for item in items:
            title_node = item.select_one('[class*="ScheduleItem-module--scheduleTitle--"]')
            date_node = item.select_one('[class*="ScheduleItem-module--scheduleDate--"]')
            description = text(item.select_one('[class*="ScheduleItem-module--scheduleDescription--"]'))
            # Multiple italicised works in one session have no separate start times.
            films = title_node.select('em') if title_node else []
            if len(films) != 1 or not re.search(r'\b(?:18|19|20)\d{2}\b', description):
                uncertain = True
                if films:
                    reader.partial(url, 'Programa de cine sin desglose inequívoco de películas y horas individuales.', url)
                continue
            title = text(films[0])
            director = text(title_node).split(title, 1)[0].rstrip(' .,')
            raw = text(date_node)
            try:
                day = _spanish_date(raw)
                clock = re.search(r'\ba\s+las\s+(\d{1,2}):(\d{2})', raw, re.I)
                if not clock: raise ValueError('Hora de sesión no reconocible')
                start = datetime.combine(day, time(int(clock[1]), int(clock[2])))
            except ValueError as exc:
                uncertain = True
                reader.partial(title, str(exc), url)
                continue
            duration = re.search(r'\b(\d{1,3})\s*[’\']', description)
            booking = details.select_one('a[href*="entradas.museoreinasofia.es"]')
            reader.result.add(title, start, url, director=director, duration=int(duration[1]) if duration else None,
                              booking=booking['href'] if booking else url, room=location)
    if not reader.result.sessions and not uncertain:
        reader.result.empty_confirmed = True


def casa_mexico(reader):
    """Published film programmes with explicit per-film dates and times."""
    from .adapters import MONTHS
    from .core import normalize
    index = reader.soup(reader.cinema['url'])
    cards = index.select('.actividades')
    if not cards:
        raise ValueError('No se reconoce la agenda de cine de Casa de México.')
    uncertain = False
    for card in cards:
        anchor = card.select_one('h3.info-nombre')
        anchor = anchor.find_parent('a') if anchor else None
        label = text(card.select_one('.info-fecha .fecha'))
        if not anchor or not label:
            uncertain = True
            reader.partial('agenda', 'Ficha de la agenda sin enlace o fechas reconocibles.', reader.cinema['url'])
            continue
        url = urljoin(reader.cinema['url'], anchor['href'])
        try:
            end = _spanish_date(label)
        except ValueError as exc:
            uncertain = True
            reader.partial(text(anchor), str(exc), url)
            continue
        if end < reader.today:
            continue
        # An undated first year in a cross-year range cannot safely inherit the end year.
        months = re.findall(r'\d{1,2}\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)', label, re.I)
        if len(months) >= 2 and MONTHS.get(normalize(months[0]), 0) > MONTHS.get(normalize(months[-1]), 0):
            uncertain = True
            reader.partial(text(anchor), 'Ciclo entre años sin fechas individuales con año inequívoco.', url)
            continue
        try:
            page = reader.soup(url)
        except Exception:
            uncertain = True
            reader.partial(text(anchor), 'No se pudo leer el ciclo.', url)
            continue
        headings = [text(n) for n in page.select('.elementor-heading-title')]
        if not any(re.fullmatch(r'(?:Cine\s*-\s*Auditorio(?: de Fundaci[oó]n Casa de M[eé]xico en Espa[ñn]a)?|Fundaci[oó]n Casa de M[eé]xico en Espa[ñn]a)', h, re.I) for h in headings):
            uncertain = True
            reader.partial(text(anchor), 'Sede de proyección no reconocible en la ficha.', url)
            continue
        marker = next((p for p in page.select('.elementor-widget-container p') if re.fullmatch(r'\s*Programa\s*:\s*', text(p), re.I)), None)
        if not marker:
            uncertain = True
            reader.partial(text(anchor), 'No se reconoce un programa con películas y pases individuales.', url)
            continue
        container = marker.parent
        count = 0
        for paragraph in marker.find_next_siblings('p'):
            if paragraph.parent is not container:
                break
            raw = text(paragraph).replace('\u200b', '').strip()
            links = paragraph.select('a[href]')
            # Multiple linked titles in a single paragraph cannot be safely mapped to dates.
            matches = list(re.finditer(r'(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s*\|\s*(\d{1,2}):(\d{2})\s*h?', raw, re.I))
            if len(links) != 1 or not matches:
                if links or re.search(r'\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóú]+', raw, re.I):
                    uncertain = True
                    reader.partial(text(anchor), 'Programa de cine con títulos u horarios no desglosables.', url)
                continue
            title = text(links[0]).replace('\u200b','').strip()
            director = re.search(r'\bDir\.\s*(.*?)(?=\d{1,2}\s+de\s+|$)', raw, re.I)
            for m in matches:
                try:
                    month = MONTHS.get(normalize(m[2]))
                    if not month or not title: raise ValueError('Título o mes no reconocido')
                    day = date(end.year, month, int(m[1]))
                    start = datetime.combine(day, time(int(m[3]), int(m[4])))
                except ValueError as exc:
                    uncertain = True
                    reader.partial(title or text(anchor), str(exc), url)
                    continue
                detail = urljoin(url, links[0]['href'])
                reader.result.add(title, start, detail, director=(director[1].strip() if director else ''), room='Auditorio')
                count += 1
        if not count:
            uncertain = True
            reader.partial(text(anchor), 'El programa no ofrece pases individuales reconocibles.', url)
    if not reader.result.sessions and not uncertain:
        reader.result.empty_confirmed = True
