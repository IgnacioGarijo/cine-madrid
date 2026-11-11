import {madridDay, filterSessions, countByDay, monthCells, distanceKm, rankCinemas, nearbyCinemas, groupFilms} from './calendar-utils.js?v=0.5.0';

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
let data, catalog = [], watch = [], origin = stored('cm-origin', null);
let offlineData = false, installPrompt = null;
let selectedCinemas = new Set(), selectedCategory = '', favoriteSearches = [], favoritePage = 1;
const categories = [['','Toda la cartelera'],['repertory_events','Reposiciones y eventos'],['premiere','Estrenos'],['unclassified','Pendiente de clasificar']];
const eventName = tag => ({live_music:'Música en directo',discussion:'Coloquio',guests:'Con invitados',marathon:'Maratón o programa doble'}[tag] || tag);
if (!Array.isArray(watch)) watch = [];
const initialDay = madridDay();
let calendarYear = Number(initialDay.slice(0,4)), calendarMonth = Number(initialDay.slice(5,7)) - 1;

function distance(cinema) { return distanceKm(origin,cinema); }
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
  const groups = groupFilms(sessions,values().sort || 'time');
  for (const group of groups) {
    const first = group.sessions[0], movie = data.movies.find(m => m.id === first.movie_id) || {};
    const article = el('article',undefined,'film movie-group'), heading = el('div',undefined,'movie-heading');
    const title = movie.canonical_title || first.title;
    heading.append(el('h3',title));
    const meta = [movie.year || first.year, movie.director || first.director].filter(Boolean).join(' · ');
    if (meta) heading.append(el('p',meta,'meta'));
    const badges = el('div',undefined,'badges');
    if (group.sessions.some(s => s.category === 'repertory')) badges.append(el('span','Reposición','badge'));
    if (group.sessions.some(s => s.special_tags?.length)) badges.append(el('span','Incluye eventos','badge event-badge'));
    if (group.vote_count !== null) badges.append(el('span',new Intl.NumberFormat('es-ES').format(group.vote_count)+' valoraciones TMDB','badge'));
    heading.append(badges);
    if (first.tmdb_url) heading.append(link('Ficha TMDB ↗',first.tmdb_url,'tmdb-film-link'));
    article.append(heading);
    const cinemaIds = new Set(group.sessions.map(s => s.cinema_id));
    for (const cinema of rankCinemas(data.cinemas.filter(c => cinemaIds.has(c.id)),origin)) {
      const block = el('section',undefined,'cinema-program'), name = el('h4',cinema.name);
      if (nearLabel(cinema)) name.append(el('span',nearLabel(cinema),'cinema-distance'));
      block.append(name);
      const days = new Map();
      for (const session of group.sessions.filter(s => s.cinema_id === cinema.id)) {
        const key = session.start.slice(0,10);
        if (!days.has(key)) days.set(key,[]);
        days.get(key).push(session);
      }
      for (const [day,list] of days) {
        const row = el('div',undefined,'screening-day');
        row.append(el('h5',fmt.format(dayDate(day))));
        const slots = el('div',undefined,'times');
        for (const item of list) {
          const special = item.special_tags?.length > 0;
          const slot = el('div',undefined,'slot'+(special?' event-slot':''));
          slot.append(link(clock.format(new Date(item.start)),item.booking_url));
          const version = [item.version !== 'Sin especificar' ? item.version : '',item.format,item.room ? 'Sala '+item.room : ''].filter(Boolean).join(' · ');
          if (version) slot.append(el('small',version));
          if (special) slot.append(el('span',item.special_tags.map(eventName).join(' · '),'event-label'));
          if (item.stale || offlineData) slot.append(el('small','Consultar cambios ↗'));
          if (!item.stale && item.duration_minutes) slot.append(link('+ Calendario',gcal(item,cinema),'add-calendar'));
          else slot.append(link('Consultar ficha',item.source_url,'add-calendar'));
          slots.append(slot);
        }
        row.append(slots);block.append(row);
      }
      article.append(block);
    }
    target.append(article);
  }
  if (!groups.length) target.append(el('p','No hay películas con estos filtros.','empty'));
  return groups.length;
}
function renderFilterChoices() {
  if (!data) return;
  const cinemas = rankCinemas(data.cinemas.filter(c => c.status === 'active'),origin);
  const close = nearbyCinemas(cinemas,origin);
  for (const id of ['cinema-options','calendar-cinema-options']) {
    const box = $('#'+id), scroll = box.scrollLeft;
    const focusId = box.contains(document.activeElement) ? document.activeElement?.dataset.cinemaId : null;
    box.replaceChildren();
    for (const cinema of cinemas) {
      const d = distance(cinema), label = el('label',undefined,'cinema-chip'+(selectedCinemas.has(cinema.id)?' selected':''));
      label.dataset.distance = d===null ? 'unknown' : d<=1 ? 'near' : d<=2 ? 'walk' : d<=4 ? 'medium' : 'far';
      const input = el('input');input.type='checkbox';input.checked=selectedCinemas.has(cinema.id);input.dataset.cinemaId=cinema.id;
      input.oninput = event => {event.stopPropagation();input.checked ? selectedCinemas.add(cinema.id) : selectedCinemas.delete(cinema.id);render();};
      const name = el('span',cinema.name);
      const dot = el('span',d===null ? (origin ? 'Distancia sin datos' : 'Sin origen') : d.toFixed(1)+' km','chip-distance');
      label.append(input,name,dot);box.append(label);
    }
    box.scrollLeft=scroll;
    if (focusId) box.querySelector('[data-cinema-id="'+focusId+'"]').focus({preventScroll:true});
  }
  for (const id of ['category-options','calendar-category-options']) {
    const box=$('#'+id);box.replaceChildren();
    for (const [key,name] of categories) {
      const button=el('button',name);button.type='button';button.setAttribute('aria-pressed',String(selectedCategory===key));
      button.onclick=()=>{selectedCategory=key;render();};box.append(button);
    }
  }
  for (const button of all('[data-cinema-action]')) {
    const isAll=button.dataset.cinemaAction==='all';
    button.disabled=!isAll && !close.length;
    button.setAttribute('aria-pressed',String(isAll ? !selectedCinemas.size : close.length>0 && selectedCinemas.size===close.length && close.every(id=>selectedCinemas.has(id))));
  }
  $('#cinema-selection-summary').textContent = selectedCinemas.size ? '· '+selectedCinemas.size+' seleccionados' : '· todos';
  $('#cinema-order-note').textContent = origin ? 'Por cercanía a tu origen · distancias en línea recta. Desliza para ver todos.' : 'Guarda tu dirección en Mi origen para ordenar por cercanía y seleccionar los cercanos. Desliza para ver todos.';
}

function values() {
  return {...Object.fromEntries(all('#filters [data-filter]').map(input => [input.dataset.filter,input.value])),cinemas:[...selectedCinemas],category:selectedCategory};
}
function syncFilters() {
  const filters = values();
  for (const input of all('#calendar-filters [data-filter]')) input.value = filters[input.dataset.filter] || '';
  const count = ['version','format','after','before'].filter(key => filters[key]).length;
  $('#filter-count').textContent = count || '';
}
function sorted(sessions) { return [...sessions].sort((a,b)=>a.start.localeCompare(b.start)); }
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
  renderFilterChoices(); syncFilters();
  const list = sorted(filterSessions(data.sessions, values()));
  const films=renderSessions($('#results'),list);
  $('#result-count').textContent = `${films} ${films===1?'película':'películas'} · ${list.length} ${list.length===1?'pase':'pases'}`;
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

function favoriteRequest(movie, operation = 'Añadir', page = 1) {
  return 'https://github.com/IgnacioGarijo/cine-madrid/issues/new?' + new URLSearchParams({template:'favorita.yml',operation,movie,page:String(page)});
}
function renderWatch() {
  const box = $('#watchlist'); box.replaceChildren();
  for (const movie of watch) {
    const row = el('li', undefined, 'favorite-row'), name = el('span');
    name.append(el('strong',movie.title));
    if (movie.year) name.append(el('small',String(movie.year)));
    row.append(name,link('Quitar ↗',favoriteRequest(movie.id,'Quitar'),'favorite-remove'));box.append(row);
  }
  if (!watch.length) box.append(el('li','Todavía no hay películas guardadas.','empty'));
}
function renderCatalog() {
  const box = $('#catalog'); box.replaceChildren();$('#favorite-pagination').replaceChildren();
  const raw = $('#catalog-query').value.trim(), query = norm(raw), request = $('#request-favorite');
  request.hidden=query.length<2;request.href=favoriteRequest(raw,'Buscar',favoritePage);
  const status=$('#favorite-search-status');
  if (query.length<2) {status.textContent='Escribe un título para buscar en todo TMDB.';return;}
  const results=favoriteSearches.find(s=>norm(s.query)===query && s.page===favoritePage);
  if (!results) {status.textContent='Confirma Buscar en TMDB en GitHub y vuelve a esta ventana. Los resultados se cargarán automáticamente; la búsqueda no añade películas a la lista.';return;}
  status.textContent=`${results.total_results} resultados en TMDB · página ${results.page} de ${results.total_pages || 1} · ${new Date(results.searched_at).toLocaleString('es-ES')}`;
  for (const movie of results.movies) {
    const row=el('div',undefined,'favorite-row'), name=el('span');
    name.append(el('strong',movie.title),el('small',`${movie.year || 'Sin año'} · ${movie.director || movie.original_title || ''}`));
    name.append(link('Ver ficha TMDB ↗',movie.source_url,'fine'));
    const added=watch.some(m=>m.id===movie.id);
    row.append(name,added ? el('span','Guardada','fine') : link('Añadir ↗',favoriteRequest(movie.id),'button'));box.append(row);
  }
  if (!results.movies.length) box.append(el('p','No hay resultados para ese título.','fine'));
  for (const [page,label] of [[favoritePage-1,'Página anterior'],[favoritePage+1,'Página siguiente']]) {
    if (page<1 || page>results.total_pages) continue;
    const button=link(label+' ↗',favoriteRequest(raw,'Buscar',page),'button');
    button.onclick=()=>{favoritePage=page;renderCatalog();};$('#favorite-pagination').append(button);
  }
}
async function refreshFavoriteSearches() {
  if (!$('#favorite-dialog').open) return;
  try {
    const response=await fetch('favorite-searches.json',{cache:'no-cache'});
    if (response.ok) {favoriteSearches=await response.json();renderCatalog();}
    const favorites=await fetch('favorites.json',{cache:'no-cache'});
    if (favorites.ok) {watch=await favorites.json();renderWatch();}
  } catch { /* Preserve the last public results when offline. */ }
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
    const responses = await Promise.all([fetch('data.json',{cache:'no-cache'}), fetch('catalog.json',{cache:'no-cache'}), fetch('newsletters.json',{cache:'no-cache'}), fetch('favorites.json',{cache:'no-cache'}),fetch('favorite-searches.json',{cache:'no-cache'})]);
    if (!responses[0].ok) throw new Error('Datos no disponibles');
    offlineData = responses[0].headers.get('X-Cine-Madrid-Cache') === 'offline';
    data = await responses[0].json();
    catalog = responses[1].ok ? await responses[1].json() : [];
    watch = responses[3].ok ? await responses[3].json() : [];
    favoriteSearches=responses[4].ok ? await responses[4].json() : [];
    const posts = responses[2].ok ? await responses[2].json() : [];
    $('#updated').textContent = 'Último intento: ' + new Date(data.generated_at).toLocaleString('es-ES');
    const active = data.sources.filter(s => s.status === 'ok').length;
    $('#coverage').textContent = `Cobertura parcial · ${active} fuente${active === 1 ? '' : 's'} leída${active === 1 ? '' : 's'} correctamente · ${data.cinemas.length} espacios en inventario provisional. Las demás carteleras están pendientes de integrar.`;
    $('#inventory-count').textContent = `${data.cinemas.length} espacios`;
    const tmdb = data.tmdb || {};
    $('#agent-status').textContent = `TMDB: ${tmdb.status === 'ok' ? 'conectado' : tmdb.status === 'partial' ? 'lectura parcial' : 'pendiente o no disponible'} · ${tmdb.matched_movies || 0}/${tmdb.total_movies || data.movies.length} películas identificadas en la última consulta. Copilot sigue pendiente para las ambigüedades. Las identidades sin verificar no generan avisos de coincidencia.`;
    for (const cinema of data.cinemas) {
      const row = el('div',undefined,'source-row');
      const reading = data.sources.find(s => s.id === cinema.id);
      const state = reading?.status === 'ok' ? 'Lectura correcta' : reading?.status === 'partial' ? 'Lectura parcial' : reading?.status === 'error' ? 'Error de lectura' : 'Pendiente';
      row.append(cinema.url ? link(cinema.name,cinema.url) : el('strong',cinema.name),el('span',`${state}${cinema.municipality && cinema.municipality !== 'Madrid' ? ' · ' + cinema.municipality : ''}${cinema.formats?.includes('IMAX') ? ' · Tiene sala IMAX' : ''}${reading?.last_session ? ' · Pases hasta ' + reading.last_session.slice(0,10) : ''}`));
      if (cinema.schedule_url) row.append(link('Horarios · '+(cinema.schedule_label || 'fuente alternativa'),cinema.schedule_url));
      $('#sources').append(row);
    }
    for (const key of ['version','format','sort']) {
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
    const search=new URLSearchParams(location.search).get('favorite_search');
    if (search) {setView('pendientes');$('#catalog-query').value=search;favoritePage=Math.max(1,Number(new URLSearchParams(location.search).get('favorite_page')) || 1);renderCatalog();$('#favorite-dialog').showModal();}
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
$('#reset-filters').onclick = () => { all('#filters [data-filter]').forEach(input => {input.value = input.id==='sort' ? 'time' : '';});selectedCinemas.clear();selectedCategory='';render(); };
all('[data-cinema-action]').forEach(button => {button.onclick=()=>{selectedCinemas=new Set(button.dataset.cinemaAction==='nearby' ? nearbyCinemas(data.cinemas.filter(c=>c.status==='active'),origin) : []);render();};});
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
$('#catalog-query').oninput = () => {favoritePage=1;renderCatalog();};
setInterval(refreshFavoriteSearches,15000);window.addEventListener('focus',refreshFavoriteSearches);
$('#add-favorite').onclick = () => { $('#catalog-query').value = '';favoritePage=1;renderCatalog(); $('#favorite-dialog').showModal(); $('#catalog-query').focus(); };
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
