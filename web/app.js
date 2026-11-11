import {madridDay, filterSessions, countByDay, monthCells} from './calendar-utils.js?v=0.3.0';

const $ = selector => document.querySelector(selector);
const all = selector => [...document.querySelectorAll(selector)];
const el = (tag, text, className) => {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
};
const fmt = new Intl.DateTimeFormat('es-ES', {dateStyle:'full', timeZone:'Europe/Madrid'});
const clock = new Intl.DateTimeFormat('es-ES', {hour:'2-digit', minute:'2-digit', timeZone:'Europe/Madrid'});
const monthName = new Intl.DateTimeFormat('es-ES', {month:'long', year:'numeric', timeZone:'UTC'});
const shortDay = new Intl.DateTimeFormat('es-ES', {day:'numeric', month:'long', timeZone:'UTC'});
const norm = text => (text || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
const dayDate = key => new Date(key + 'T12:00:00Z');
const safeURL = value => {
  try { const url = new URL(value); return ['https:','http:'].includes(url.protocol) ? url.href : '#'; }
  catch { return '#'; }
};
const link = (text, url, className) => {
  const node = el('a', text, className);
  node.href = safeURL(url); node.target = '_blank'; node.rel = 'noopener';
  return node;
};
function stored(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function store(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
}
let data, catalog = [], watch = stored('cm-watch', []), origin = stored('cm-origin', null);
let offlineData = false, installPrompt = null;
if (!Array.isArray(watch)) watch = [];
const initialDay = madridDay();
let calendarYear = Number(initialDay.slice(0,4)), calendarMonth = Number(initialDay.slice(5,7)) - 1;

function distance(cinema) {
  if (!origin || !Number.isFinite(cinema?.lat) || !Number.isFinite(cinema?.lon)) return null;
  const radians = x => x * Math.PI / 180;
  const a = radians(cinema.lat - origin.lat), b = radians(cinema.lon - origin.lon);
  const q = Math.sin(a / 2) ** 2 + Math.cos(radians(origin.lat)) * Math.cos(radians(cinema.lat)) * Math.sin(b / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(q), Math.sqrt(Math.max(0, 1 - q)));
}
function nearLabel(cinema) {
  const d = distance(cinema);
  return d === null ? '' : `${d <= 1 ? '🟢' : d <= 2 ? '🟡' : d <= 4 ? '🟠' : '🟣'} ${d.toFixed(1)} km en línea recta`;
}
function gcal(session, cinema) {
  const stamp = value => new Date(value).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z/,'Z');
  const params = new URLSearchParams({action:'TEMPLATE', text:session.title,
    dates:stamp(session.start) + '/' + stamp(new Date(new Date(session.start).getTime() + session.duration_minutes * 60000)),
    location:cinema.name + ' · ' + cinema.address,
    details:'Fuente: ' + session.source_url + '\nEntradas: ' + session.booking_url, ctz:'Europe/Madrid'});
  return 'https://calendar.google.com/calendar/render?' + params;
}

function renderSessions(target, sessions) {
  target.replaceChildren();
  const groups = new Map();
  for (const session of sessions) {
    const key = [session.start.slice(0,10), session.movie_id, session.cinema_id, session.version, session.format].join('|');
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(session);
  }
  let number = 0;
  for (const list of groups.values()) {
    const session = list[0], cinema = data.cinemas.find(c => c.id === session.cinema_id) || {name:session.cinema_id, address:''};
    const row = el('article', undefined, 'film'), body = el('div');
    row.append(el('div', String(++number).padStart(2, '0'), 'film-number'));
    body.append(el('h3', session.title), el('p', `${fmt.format(new Date(session.start))} · ${cinema.name}${session.director ? ' · ' + session.director : ''}`, 'meta'));
    const badges = el('div', undefined, 'badges');
    const tags = [session.version, session.format, nearLabel(cinema),
      session.category === 'repertory' ? 'Reposición verificada' : null,
      session.stale || offlineData ? 'Última lectura guardada' : null, ...(session.special_tags || [])].filter(Boolean);
    for (const tag of tags) badges.append(el('span', tag, 'badge'));
    body.append(badges);
    if (session.tmdb_url) body.append(link(`Ficha TMDB${session.year ? ' · ' + session.year : ''} ↗`,session.tmdb_url,'tmdb-film-link'));
    const slots = el('div', undefined, 'times');
    for (const item of list) {
      const slot = el('div', undefined, 'slot');
      slot.append(link(clock.format(new Date(item.start)), item.booking_url), el('small', item.stale || offlineData ? 'Consultar cambios ↗' : 'Entradas ↗'));
      if (!item.stale && item.duration_minutes) slot.append(link('+ Calendario', gcal(item, cinema), 'add-calendar'));
      else slot.append(link('Consultar ficha', item.source_url, 'add-calendar'));
      slots.append(slot);
    }
    row.append(body, slots); target.append(row);
  }
  if (!groups.size) target.append(el('p', 'No hay sesiones con estos filtros.', 'empty'));
}

function values() {
  return Object.fromEntries(all('#filters [data-filter]').map(input => [input.dataset.filter, input.value]));
}
function syncFilters() {
  const filters = values();
  for (const input of all('#calendar-filters [data-filter]')) input.value = filters[input.dataset.filter] || '';
  const count = ['cinema','category','version','after','before'].filter(key => filters[key]).length;
  $('#filter-count').textContent = count || '';
}
function sorted(sessions) {
  return sessions.sort((a,b) => {
    if (origin) {
      const da = distance(data.cinemas.find(c => c.id === a.cinema_id));
      const db = distance(data.cinemas.find(c => c.id === b.cinema_id));
      if (da !== db) return (da ?? Infinity) - (db ?? Infinity);
    }
    return a.start.localeCompare(b.start);
  });
}
function setDay(day, {focus = false} = {}) {
  $('#day').value = day;
  if (day) { calendarYear = Number(day.slice(0,4)); calendarMonth = Number(day.slice(5,7)) - 1; }
  render();
  if (focus) $('#calendar-grid').querySelector(`[data-day="${day}"]`)?.focus({preventScroll:true});
}
function renderCalendar() {
  if (!data) return;
  const filters = values(), selected = filters.day, today = madridDay();
  const matching = filterSessions(data.sessions, filters, {ignoreDay:true});
  const counts = countByDay(matching), cells = monthCells(calendarYear, calendarMonth);
  const title = monthName.format(new Date(Date.UTC(calendarYear, calendarMonth, 1)));
  $('#mini-month').textContent = title;
  $('#calendar-month').textContent = title;
  $('#selected-day-label').textContent = selected ? shortDay.format(dayDate(selected)) : 'Elige un día';
  $('#calendar-summary').textContent = selected ? 'Toca el calendario para cambiar de día.' : 'Sesiones por fecha, con tus filtros.';
  const mini = $('#mini-calendar'); mini.replaceChildren();
  for (const day of ['L','M','X','J','V','S','D']) mini.append(el('span', day, 'mini-weekday'));
  const grid = $('#calendar-grid'); grid.replaceChildren();
  for (const cell of cells) {
    const count = counts.get(cell.day) || 0;
    const classes = `${count ? ' has-sessions' : ''}${cell.day === selected ? ' selected' : ''}${cell.inMonth ? '' : ' outside'}${cell.day === today ? ' today' : ''}`;
    mini.append(el('span', cell.number, classes.trim()));
    const button = el('button', undefined, 'calendar-day' + classes);
    button.type = 'button'; button.dataset.day = cell.day;
    button.setAttribute('aria-label', `${fmt.format(dayDate(cell.day))}, ${count} ${count === 1 ? 'sesión' : 'sesiones'}`);
    button.setAttribute('aria-pressed', String(cell.day === selected));
    if (cell.day === today) button.setAttribute('aria-current', 'date');
    button.disabled = cell.day < today;
    button.append(el('span', cell.number, 'day-number'));
    if (count) button.append(el('span', `${count} ${count === 1 ? 'sesión' : 'sesiones'}`, 'day-count'));
    button.onclick = () => setDay(cell.day, {focus:true});
    grid.append(button);
  }
  $('#show-day-in-list').hidden = !selected;
  $('#calendar-day-title').textContent = selected ? fmt.format(dayDate(selected)) : 'Selecciona un día';
  if (selected) renderSessions($('#calendar-day-sessions'), sorted(filterSessions(data.sessions, filters)));
  else $('#calendar-day-sessions').replaceChildren(el('p', 'Elige una fecha para ver sus películas y horarios.', 'fine'));
}
function render() {
  if (!data) return;
  syncFilters();
  const list = sorted(filterSessions(data.sessions, values()));
  renderSessions($('#results'), list);
  $('#result-count').textContent = `${list.length} ${list.length === 1 ? 'sesión' : 'sesiones'}`;
  renderCalendar();
}
function setView(name, updateHash = true) {
  if (!['cartelera','pendientes','boletin','estado'].includes(name)) name = 'cartelera';
  all('.view').forEach(view => { view.hidden = view.id !== name; });
  all('nav [data-view]').forEach(button => {
    const active = button.dataset.view === name;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');
  });
  if (updateHash && location.hash !== '#' + name) history.pushState(null,'','#' + name);
  if (name === 'estado') $('#estado').focus({preventScroll:true});
  window.scrollTo({top:0, behavior:'instant'});
}

function saveWatch() {
  const saved = store('cm-watch', watch);
  $('#watch-status').textContent = saved ? '' : 'Este navegador no permite guardar la selección. Puedes exportarla.';
  renderWatch();
}
function renderWatch() {
  const box = $('#watchlist'); box.replaceChildren();
  for (const movie of watch) {
    const card = el('article', undefined, 'card');
    card.append(el('h3', movie.title), el('p', `${movie.year || ''} · ${movie.director || ''}`));
    const matches = data?.sessions.filter(s => s.canonical_id === movie.id && !s.stale && s.start.slice(0,10) >= madridDay()) || [];
    card.append(el('p', matches.length ? `${matches.length} sesiones identificadas` : 'Sin sesiones identificadas en las fuentes integradas.'));
    const button = el('button', 'Quitar de favoritas');
    button.onclick = () => { watch = watch.filter(m => m.id !== movie.id); saveWatch(); };
    card.append(button); box.append(card);
  }
  if (!watch.length) box.append(el('p', 'Todavía no has guardado favoritas en este navegador.', 'empty'));
  renderCatalog();
}
function renderCatalog() {
  const box = $('#catalog'); box.replaceChildren();
    const query = norm($('#catalog-query').value);
  for (const movie of catalog.filter(m => !query || [m.title,m.original_title,m.director,String(m.year),...(m.aliases || [])].some(title => norm(title).includes(query)))) {
    const card = el('article', undefined, 'card'), added = watch.some(m => m.id === movie.id);
    card.append(el('h3',movie.title), el('p', `${movie.year} · ${movie.director}`));
    const button = el('button', added ? 'En tus favoritas' : '+ Añadir a favoritas');
    button.disabled = added; button.onclick = () => { watch.push(movie); saveWatch(); };
    card.append(button, link('Ver ficha ↗', movie.source_url)); box.append(card);
  }
}
function renderIncidents() {
  if (!data) return;
  const box = $('#incidents'), filter = $('#issue-filter').value; box.replaceChildren();
  for (const issue of data.incidents.filter(i => !filter || i.status === filter)) {
    const row = el('article', undefined, 'incident ' + issue.severity);
    row.append(el('code', issue.code + ' · ' + issue.source_id + ' · ' + (issue.status === 'open' ? 'Abierta' : 'Resuelta')),
      el('p', issue.message), el('small', 'Primera detección: ' + new Date(issue.first_seen).toLocaleString('es-ES') + ' · Última: ' + new Date(issue.last_seen).toLocaleString('es-ES')));
    if (issue.url) row.append(document.createTextNode(' · '), link('Fuente ↗',issue.url));
    box.append(row);
  }
  if (!box.children.length) box.append(el('p','No hay incidencias con este filtro.','empty'));
}
function connectionState() {
  const offline = !navigator.onLine || offlineData;
  $('#offline-label').hidden = !offline;
  $('#connection-status').textContent = offline ? 'Mostrando datos guardados; consulta la fecha de la última lectura antes de planificar.' : 'Datos obtenidos con conexión.';
}
async function boot() {
  try {
    const responses = await Promise.all([fetch('data.json',{cache:'no-cache'}), fetch('catalog.json',{cache:'no-cache'}), fetch('newsletters.json',{cache:'no-cache'})]);
    if (!responses[0].ok) throw new Error('Datos no disponibles');
    offlineData = responses[0].headers.get('X-Cine-Madrid-Cache') === 'offline';
    data = await responses[0].json();
    catalog = responses[1].ok ? await responses[1].json() : [];
    const posts = responses[2].ok ? await responses[2].json() : [];
    $('#updated').textContent = 'Último intento: ' + new Date(data.generated_at).toLocaleString('es-ES');
    const active = data.sources.filter(s => s.status === 'ok').length;
    $('#coverage').textContent = `Cobertura parcial · ${active} fuente${active === 1 ? '' : 's'} leída${active === 1 ? '' : 's'} correctamente · ${data.cinemas.length} espacios en inventario provisional. Las demás carteleras están pendientes de integrar.`;
    $('#inventory-count').textContent = `${data.cinemas.length} espacios`;
    const tmdb = data.tmdb || {};
    $('#agent-status').textContent = `TMDB: ${tmdb.status === 'ok' ? 'conectado' : tmdb.status === 'partial' ? 'lectura parcial' : 'pendiente o no disponible'} · ${tmdb.matched_movies || 0}/${tmdb.total_movies || data.movies.length} películas identificadas en la última consulta. Copilot sigue pendiente para las ambigüedades. Las identidades sin verificar no generan avisos de coincidencia.`;
    for (const cinema of data.cinemas) {
      if (cinema.status === 'active') {
        const option = el('option',cinema.name); option.value = cinema.id; $('#cinema').append(option);
      }
      const row = el('div',undefined,'source-row');
      row.append(cinema.url ? link(cinema.name,cinema.url) : el('strong',cinema.name),el('span',cinema.status === 'active' ? 'Conector integrado' : 'Pendiente'));
      $('#sources').append(row);
    }
    for (const key of ['cinema','category','version']) {
      const source = $('#' + key), target = $('#calendar-' + key); target.replaceChildren();
      for (const option of source.options) target.append(option.cloneNode(true));
    }
    render(); renderWatch(); renderIncidents(); connectionState();
    $('#calendar-preview').disabled = false;
    if (!posts.length) $('#newsletters').append(el('p','Todavía no hay ediciones publicadas.','empty'));
    for (const post of posts) {
      const article = el('article',undefined,'card'); article.append(el('h3',post.id),el('p',post.note));
      const list = el('div'); renderSessions(list,post.sessions); article.append(list); $('#newsletters').append(article);
    }
    const route = location.hash.slice(1);
    setView(route === 'calendario' ? 'cartelera' : route || 'cartelera', false);
    if (route === 'calendario') $('#calendar-dialog').showModal();
  } catch {
    $('#fatal').hidden = false; $('#fatal').textContent = 'No se pudo cargar la cartelera. Conéctate a Internet y vuelve a abrir la página.';
    $('#updated').textContent = 'Datos no disponibles';
  }
}

all('nav [data-view]').forEach(button => { button.onclick = () => setView(button.dataset.view); });
all('[data-go]').forEach(button => { button.onclick = () => setView(button.dataset.go); });
$('#open-status').onclick = () => setView('estado');
window.addEventListener('popstate', () => setView(location.hash.slice(1) || 'cartelera', false));
window.addEventListener('hashchange', () => setView(location.hash.slice(1) || 'cartelera', false));
$('#filters').onsubmit = event => event.preventDefault();
$('#filters').oninput = event => {
  if (event.target.id === 'day' && event.target.value) {
    calendarYear = Number(event.target.value.slice(0,4)); calendarMonth = Number(event.target.value.slice(5,7)) - 1;
  }
  render();
};
$('#calendar-filters').onsubmit = event => event.preventDefault();
$('#calendar-filters').oninput = event => {
  const key = event.target.dataset.filter;
  if (key) { $('#filters [data-filter="' + key + '"]').value = event.target.value; render(); }
};
$('#toggle-filters').onclick = () => {
  const expanded = $('#toggle-filters').getAttribute('aria-expanded') === 'true';
  $('#toggle-filters').setAttribute('aria-expanded', String(!expanded)); $('#advanced-filters').hidden = expanded;
};
$('#reset-filters').onclick = () => { all('#filters [data-filter]').forEach(input => {input.value = '';}); render(); };
$('#today-button').onclick = () => setDay(madridDay());
$('#all-days-button').onclick = () => setDay('');
$('#calendar-clear-day').onclick = () => setDay('');
$('#calendar-preview').onclick = () => { renderCalendar(); $('#calendar-dialog').showModal(); };
$('#show-day-in-list').onclick = () => { $('#calendar-dialog').close(); $('#results').scrollIntoView({block:'start'}); };
function shiftMonth(amount) {
  const next = new Date(Date.UTC(calendarYear, calendarMonth + amount, 1));
  calendarYear = next.getUTCFullYear(); calendarMonth = next.getUTCMonth(); renderCalendar();
}
$('#previous-month').onclick = () => shiftMonth(-1);
$('#next-month').onclick = () => shiftMonth(1);
all('[data-close]').forEach(button => {button.onclick = () => $('#' + button.dataset.close).close();});
all('dialog').forEach(dialog => {dialog.onclick = event => {if (event.target === dialog && (event.clientX < dialog.getBoundingClientRect().left || event.clientX > dialog.getBoundingClientRect().right || event.clientY < dialog.getBoundingClientRect().top || event.clientY > dialog.getBoundingClientRect().bottom)) dialog.close();};});
$('#show-location').onclick = () => { $('#location-settings').open = true; $('#origin').focus(); };
$('#issue-filter').onchange = renderIncidents;
$('#catalog-query').oninput = renderCatalog;
$('#export-watchlist').onclick = () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(watch,null,2)],{type:'application/json'})), anchor = el('a');
  anchor.href = url; anchor.download = 'cine-madrid-pendientes.json'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
};
$('#import-watchlist').onchange = async event => {
  try {
    const incoming = JSON.parse(await event.target.files[0].text());
    if (!Array.isArray(incoming) || !incoming.every(m => typeof m.id === 'string' && typeof m.title === 'string')) throw new Error();
    watch = incoming.map(m => ({id:m.id,title:m.title,year:m.year,director:m.director})); saveWatch();
    $('#watch-status').textContent = 'Selección local importada. Los avisos utilizan la lista privada.';
  } catch { $('#watch-status').textContent = 'Archivo no válido. Usa una exportación de favoritas.'; }
};
$('#origin-form').onsubmit = async event => {
  event.preventDefault(); const address = $('#origin').value.trim(); if (!address) return;
  $('#origin-status').textContent = 'Buscando dirección…';
  try {
    const url = 'https://nominatim.openstreetmap.org/search?' + new URLSearchParams({q:address + ', Madrid, España',format:'json',limit:'1'});
    const response = await fetch(url); if (!response.ok) throw new Error();
    const places = await response.json(); if (!places.length) throw new Error();
    origin = {lat:Number(places[0].lat),lon:Number(places[0].lon)};
    const saved = store('cm-origin',origin);
    $('#origin-status').textContent = saved ? 'Origen guardado en este navegador. Distancias en línea recta.' : 'Origen aplicado. Este navegador no permite guardarlo.'; render();
  } catch { $('#origin-status').textContent = 'No se pudo localizar la dirección. Prueba con calle y número.'; }
};
$('#clear-origin').onclick = () => {
  origin = null; try {localStorage.removeItem('cm-origin');} catch { /* Private browsing may block storage. */ }
  $('#origin').value = ''; $('#origin-status').textContent = 'Origen eliminado.'; render();
};

window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); installPrompt = event; });
async function install() {
  if (installPrompt) {
    const prompt = installPrompt; installPrompt = null; await prompt.prompt();
  } else $('#install-dialog').showModal();
}
$('#install-button').onclick = install;
$('#install-help').onclick = () => $('#install-dialog').showModal();
const standalone = window.matchMedia('(display-mode: standalone)');
const reflectInstalled = () => { $('#install-button').hidden = standalone.matches || navigator.standalone === true; };
reflectInstalled(); standalone.addEventListener('change', reflectInstalled);
window.addEventListener('appinstalled', () => {installPrompt = null; $('#install-button').hidden = true;});
window.addEventListener('offline', connectionState);
window.addEventListener('online', () => {
  connectionState();
  // Reload only when returning from a cached offline snapshot, preserving the route and local favourites.
  if (offlineData) location.reload();
});
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js', {scope:'./', updateViaCache:'none'}).catch(() => {
      $('#connection-status').textContent += ' No se pudo preparar el acceso sin conexión.';
    });
  });
}
boot();
