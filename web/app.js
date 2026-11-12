import {createAccount} from './account.js?v=0.11.1';
import {madridDay, filterSessions, countByDay, monthCells, distanceKm, rankCinemas, nearbyCinemas, groupFilms, filmDays, chooseFilmDay} from './calendar-utils.js?v=0.11.1';

import {addressCandidates, validOrigin} from './search-utils.js?v=0.11.1';
import {posterURL} from './poster-utils.js?v=0.11.1';

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
let filmDaySelections = new WeakMap();
let searchApi = '', liveFavoriteResults = null, favoriteTimer, favoriteController, favoriteSequence = 0, favoriteError = '';
let favoritesApi = '', favoriteSaving = false;
let accountClient=null, accountUser=null, accountEpoch=0, legacyFavorites=[], guestOrigin=origin, accountsEnabled=false;
let addressTimer, addressController, addressSequence = 0;
let selectedCinemas = new Set(), selectedCategories = new Set(['repertory_events','premiere','unclassified']), favoriteSearches = [], favoritePage = 1;
const categories = [['repertory_events','Repos. y eventos'],['premiere','Estrenos'],['unclassified','Por clasificar']];
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

function renderSessions(target, sessions, {contextSessions=sessions}={}) {
  target.replaceChildren();
  const order=values().sort || 'votes', proximity={origin,cinemas:data.cinemas};
  const groups = groupFilms(sessions,order,new Date(),proximity);
  const context=new Map(groupFilms(contextSessions,order,new Date(),proximity).map(group=>[group.key,group.sessions]));
  if (!filmDaySelections.has(target)) filmDaySelections.set(target,new Map());
  const selections=filmDaySelections.get(target);
  for (const group of groups) {
    const first = group.sessions[0], movie = data.movies.find(m => m.id === first.movie_id) || {};
    const article = el('article',undefined,'film movie-group'), heading = el('div',undefined,'movie-heading');
    const title = movie.canonical_title || first.title;
    const artwork=el('div',undefined,'film-poster');artwork.setAttribute('aria-hidden','true');
    const poster=posterURL(movie.identity_status==='verified' ? movie.poster_path : null);
    if(poster) {
      const img=el('img');img.src=poster;img.alt='';img.width=80;img.height=120;img.loading='lazy';img.decoding='async';
      img.onerror=()=>{artwork.replaceChildren(el('span','▧','poster-placeholder'));artwork.classList.add('missing-poster');};artwork.append(img);
    } else {artwork.append(el('span','▧','poster-placeholder'));artwork.classList.add('missing-poster');}
    const copy=el('div',undefined,'film-heading-copy');copy.append(el('h3',title));
    const year=movie.year || first.year, director=movie.director || first.director;
    const credits=el('div',undefined,'film-credits');
    if(year)credits.append(el('span',String(year),'film-year'));
    if(year && director){const separator=el('span','·','film-credit-separator');separator.setAttribute('aria-hidden','true');credits.append(separator);}
    if(director){const name=el('span',director,'film-director');name.title=director;credits.append(name);}
    if(credits.childNodes.length)copy.append(credits);
    heading.append(artwork,copy);
    article.append(heading);
    const available=context.get(group.key) || group.sessions;
    const dates=filmDays(available), dateControl=el('label',undefined,'movie-date-control'), dateSelect=el('select');
    dateSelect.setAttribute('aria-label','Fecha para '+title);
    for (const day of dates) {const option=el('option',fmt.format(dayDate(day)));option.value=day;dateSelect.append(option);}
    dateSelect.value=chooseFilmDay(available,values().day,selections.get(group.key));
    dateSelect.disabled=dates.length<2;dateControl.append(dateSelect);
    const screenings=el('div',undefined,'movie-screenings');article.append(dateControl,screenings);
    const renderDay=()=>{
      screenings.replaceChildren();
      const visibleSessions=available.filter(session=>session.start.slice(0,10)===dateSelect.value);
    const cinemaIds = new Set(visibleSessions.map(s => s.cinema_id));
    for (const cinema of rankCinemas(data.cinemas.filter(c => cinemaIds.has(c.id)),origin)) {
      const block = el('section',undefined,'cinema-program'), name = el('h4',cinema.name);
      if (nearLabel(cinema)) name.append(el('span',nearLabel(cinema),'cinema-distance'));
      block.append(name);
      const days = new Map();
      for (const session of visibleSessions.filter(s => s.cinema_id === cinema.id)) {
        const key = session.start.slice(0,10);
        if (!days.has(key)) days.set(key,[]);
        days.get(key).push(session);
      }
      for (const [day,list] of days) {
        const row = el('div',undefined,'screening-day');

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
      screenings.append(block);
    }
    };
    dateSelect.onchange=()=>{selections.set(group.key,dateSelect.value);renderDay();};renderDay();
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
      const button=el('button',name);button.type='button';button.setAttribute('aria-pressed',String(selectedCategories.has(key)));
      button.title=key==='repertory_events'?'Reposiciones y eventos':key==='unclassified'?'Pendiente de clasificar':'Estrenos';
      button.onclick=()=>{selectedCategories.has(key)?selectedCategories.delete(key):selectedCategories.add(key);render();};box.append(button);
    }
  }
  for (const button of all('[data-cinema-action]')) {
    const isAll=button.dataset.cinemaAction==='all';
    button.disabled=!isAll && !close.length;
    button.setAttribute('aria-pressed',String(isAll ? !selectedCinemas.size : close.length>0 && selectedCinemas.size===close.length && close.every(id=>selectedCinemas.has(id))));
  }
  const selectionLabel=selectedCinemas.size ? '· '+selectedCinemas.size+(selectedCinemas.size===1?' seleccionado':' seleccionados') : '· todos';
  $('#cinema-selection-summary').textContent=selectionLabel;$('#calendar-cinema-summary').textContent=selectionLabel;
  $('#cinema-order-note').textContent = origin ? 'Por cercanía a tu origen · distancias en línea recta.' : 'Guarda tu dirección en Mi origen para ordenar por cercanía y seleccionar los cercanos.';
}

function values() {
  return {...Object.fromEntries(all('#filters [data-filter], #sort').map(input => [input.dataset.filter,input.value])),cinemas:[...selectedCinemas],categories:[...selectedCategories]};
}
function syncFilters() {
  const hasOrigin=validOrigin(origin);
  for(const option of all('#sort option[value="distance"], #calendar-sort option[value="distance"]')){
    option.disabled=!hasOrigin;option.title=hasOrigin ? 'Cine más cercano con sesiones que cumplen los filtros' : 'Guarda una dirección en Cuenta para ordenar por proximidad';
  }
  if(!hasOrigin && $('#sort').value==='distance')$('#sort').value='votes';
  const filters = values();
  for (const input of all('#calendar-filters [data-filter]')) input.value = filters[input.dataset.filter] || '';
  const count = ['version','format','after','before'].filter(key => filters[key]).length;
  $('#filter-count').textContent = count || '';
}
function sorted(sessions) { return [...sessions].sort((a,b)=>a.start.localeCompare(b.start)); }
function setDay(day, {focus = false} = {}) {
  filmDaySelections=new WeakMap();
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
  const mini = $('#mini-calendar'); mini.replaceChildren();
  for (const day of ['L','M','X','J','V','S','D']) mini.append(el('span', day, 'mini-weekday'));
  const grid = $('#calendar-grid'); grid.replaceChildren();
  for (const cell of cells) {
    const count = counts.get(cell.day) || 0;
    const classes = `${count ? ' has-sessions' : ''}${cell.day === selected ? ' selected' : ''}${cell.inMonth ? '' : ' outside'}${cell.day === today ? ' today' : ''}`;
    const miniDay=el('button',cell.number,'mini-day'+classes);miniDay.type='button';miniDay.dataset.day=cell.day;
    miniDay.setAttribute('aria-label',`${fmt.format(dayDate(cell.day))}, ${count} ${count===1?'sesión':'sesiones'}`);
    miniDay.setAttribute('aria-pressed',String(cell.day===selected));miniDay.disabled=cell.day<today;
    if(cell.day===today)miniDay.setAttribute('aria-current','date');
    miniDay.onclick=()=>{setDay(cell.day);$('#mini-calendar').querySelector(`[data-day="${cell.day}"]`)?.focus({preventScroll:true});};
    mini.append(miniDay);
    const button = el('button', undefined, 'calendar-day' + classes);
    button.type = 'button'; button.dataset.day = cell.day;
    button.setAttribute('aria-label', `${fmt.format(dayDate(cell.day))}, ${count} ${count === 1 ? 'sesión' : 'sesiones'}`);
    button.setAttribute('aria-pressed', String(cell.day === selected));
    if (cell.day === today) button.setAttribute('aria-current', 'date');
    button.disabled = cell.day < today;
    button.append(el('span', cell.number, 'day-number'));
    if (count) button.append(el('span', `${count} ${count === 1 ? 'sesión' : 'sesiones'}`, 'day-count'));
    button.onclick = () => {
      setDay(cell.day);
      $('#calendar-dialog').close();
      $('#mini-calendar').querySelector(`[data-day="${cell.day}"]`)?.focus({preventScroll:true});
    };
    grid.append(button);
  }
  $('#show-day-in-list').hidden = !selected;
  $('#calendar-day-title').textContent = selected ? fmt.format(dayDate(selected)) : '';
  if (selected) renderSessions($('#calendar-day-sessions'), sorted(filterSessions(data.sessions, filters)),{contextSessions:matching});
  else $('#calendar-day-sessions').replaceChildren();
}
function render() {
  if (!data) return;
  renderFilterChoices(); syncFilters();
  const list = sorted(filterSessions(data.sessions, values()));
  renderSessions($('#results'),list,{contextSessions:filterSessions(data.sessions,values(),{ignoreDay:true})});
  renderCalendar();
}
function setView(name, updateHash = true) {
  if (!['cartelera','pendientes','boletin','cuenta','estado'].includes(name)) name = 'cartelera';
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
async function accountRequest(path,options={}) {
  const epoch=accountEpoch;
  const {data:{session},error}=await accountClient.auth.getSession();
  if(error || !session || epoch!==accountEpoch)throw Error('signed_out');
  const response=await fetch(new URL('/me/'+path,favoritesApi),{...options,cache:'no-store',
    headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.access_token}});
  if(epoch!==accountEpoch)throw Error('account_changed');
  if(!response.ok)throw Error(response.status===401 ? 'signed_out' : 'request_failed');
  const value=await response.json();
  if(epoch!==accountEpoch)throw Error('account_changed');
  return value;
}
async function loadFavorites() {
  if(accountsEnabled){
    if(!accountUser)return;
    const movies=await accountRequest('favorites');
    if(!Array.isArray(movies))throw Error('invalid_favorites');
    watch=movies;renderWatch();renderCatalog();return;
  }
  const response=await fetch(favoritesApi || 'favorites.json',{cache:'no-store'});
  if(!response.ok)throw Error('favorites_unavailable');
  const movies=await response.json();if(!Array.isArray(movies))throw Error('invalid_favorites');
  watch=movies;renderWatch();renderCatalog();
}
function renderAccount(){
  $('#origin-summary').textContent=origin ? 'Mi origen · '+origin.label : 'Mi origen';
  $('#account-label').textContent=accountUser ? 'Tu cuenta · '+(accountUser.user_metadata?.full_name || accountUser.email || 'Sesión iniciada') : 'Entra para sincronizar tus favoritas y tu origen.';
  $('#google-login').hidden=!!accountUser;$('#google-login').disabled=!accountClient;
  $('#account-logout').hidden=!accountUser;
  $('#import-favorites').hidden=!accountUser || !legacyFavorites.some(movie=>!watch.some(item=>item.id===movie.id));
  $('#import-origin').hidden=!accountUser || !!origin || !validOrigin(guestOrigin);
  $('#add-favorite').disabled=accountsEnabled && !accountUser;

}
async function applyAccount(user){
  if(user?.id===accountUser?.id){renderAccount();return;}
  ++accountEpoch;accountUser=user;watch=[];origin=null;favoriteSaving=false;
  addressController?.abort();++addressSequence;$('#address-suggestions').replaceChildren();$('#origin').value='';
  $('#watch-status').textContent='';$('#origin-status').textContent='';
  renderAccount();renderWatch();renderCatalog();if(data)render();
  if(!user)return;
  const epoch=accountEpoch;
  try{
    await loadFavorites();const profile=await accountRequest('profile');
    if(epoch!==accountEpoch)return;
    origin=validOrigin(profile.origin) ? profile.origin : null;$('#origin').value=origin?.label || '';
    renderAccount();if(data)render();
  }catch{if(epoch===accountEpoch)$('#watch-status').textContent='No se pudo sincronizar tu cuenta. Comprueba la conexión y vuelve a abrir la página.';}
}
async function changeFavorite(movie,remove=false) {
  if(favoriteSaving)return;
  if(!accountUser){$('#watch-status').textContent='Entra con Google para guardar películas.';return;}
  const epoch=accountEpoch;favoriteSaving=true;renderCatalog();renderWatch();
  $('#watch-status').textContent=remove ? 'Quitando película…' : 'Guardando película…';
  try{
    const movies=await accountRequest('favorites'+(remove ? '/'+movie.tmdb_id : ''),{
      method:remove?'DELETE':'POST',...(remove ? {} : {body:JSON.stringify({tmdb_id:movie.tmdb_id})})});
    if(!Array.isArray(movies))throw Error('save_failed');
    watch=movies;$('#watch-status').textContent=(remove ? 'Quitada: ' : 'Guardada: ')+movie.title+'.';
    if(!remove)$('#favorite-dialog').close();
  }catch{if(epoch===accountEpoch)$('#watch-status').textContent='No se pudo guardar el cambio. Vuelve a intentarlo.';}
  finally{if(epoch===accountEpoch){favoriteSaving=false;renderWatch();renderCatalog();renderAccount();}}
}
function renderWatch() {
  const box = $('#watchlist'); box.replaceChildren();
  for (const movie of watch) {
    const row = el('li', undefined, 'favorite-row'), name = el('span');
    name.append(el('strong',movie.title));
    if (movie.year) name.append(el('small',String(movie.year)));
    if(favoritesApi) {
      const button=el('button','Quitar','favorite-remove');button.type='button';button.disabled=favoriteSaving;
      button.onclick=()=>changeFavorite(movie,true);row.append(name,button);
    } else row.append(name,link('Quitar ↗',favoriteRequest(movie.id,'Quitar'),'favorite-remove'));
    box.append(row);
  }
  if (!watch.length) box.append(el('li',accountsEnabled && !accountUser ? 'Tu lista aparecerá al iniciar sesión.' : 'Todavía no hay películas guardadas.','empty'));
  if(accountsEnabled)renderAccount();
}
function renderCatalog() {
  const box = $('#catalog'); box.replaceChildren();$('#favorite-pagination').replaceChildren();
  const raw = $('#catalog-query').value.trim(), query = norm(raw), request = $('#request-favorite');
  request.hidden=query.length<2 || (!!searchApi && !favoriteError);request.href=favoriteRequest(raw,'Buscar',favoritePage);
  const status=$('#favorite-search-status');
  if (query.length<2) {status.textContent='Escribe un título para buscar en todo TMDB.';return;}
  const results=liveFavoriteResults && norm(liveFavoriteResults.query)===query && liveFavoriteResults.page===favoritePage ? liveFavoriteResults : favoriteSearches.find(s=>norm(s.query)===query && s.page===favoritePage);
  if (!results) {status.textContent=favoriteError || (searchApi ? 'Buscando sugerencias en TMDB…' : 'Las sugerencias instantáneas están pendientes de conectar Cloudflare. Puedes utilizar Buscar en TMDB mediante GitHub mientras tanto.');return;}
  status.textContent=`${results.total_results} resultados en TMDB · página ${results.page} de ${results.total_pages || 1} · ${new Date(results.searched_at).toLocaleString('es-ES')}`;
  for (const movie of results.movies) {
    const row=el('div',undefined,'favorite-row'), name=el('span');
    name.append(el('strong',movie.title),el('small',`${movie.year || 'Sin año'} · ${movie.director || movie.original_title || ''}`));
    name.append(link('Ver ficha TMDB ↗',movie.source_url,'fine'));
    const added=watch.some(m=>m.id===movie.id);
    let action=added ? el('span','Guardada','fine') : link('Añadir ↗',favoriteRequest(movie.id),'button');
    if(!added && favoritesApi) {
      action=el('button','Añadir','button');action.type='button';action.disabled=favoriteSaving;
      action.onclick=()=>changeFavorite(movie);
    }
    row.append(name,action);box.append(row);
  }
  if (!results.movies.length) box.append(el('p','No hay resultados para ese título.','fine'));
  for (const [page,label] of [[favoritePage-1,'Página anterior'],[favoritePage+1,'Página siguiente']]) {
    if (page<1 || page>results.total_pages) continue;
    if (searchApi) {
      const button=el('button',label);button.type='button';button.onclick=()=>{favoritePage=page;queryFavoriteSuggestions();};$('#favorite-pagination').append(button);
    } else {
      const button=link(label+' ↗',favoriteRequest(raw,'Buscar',page),'button');button.onclick=()=>{favoritePage=page;renderCatalog();};$('#favorite-pagination').append(button);
    }
  }
}
async function queryFavoriteSuggestions() {
  if (!searchApi) {renderCatalog();return;}
  favoriteController?.abort();const controller=new AbortController();favoriteController=controller;
  const sequence=++favoriteSequence, query=$('#catalog-query').value.trim(), page=favoritePage;
  liveFavoriteResults=null;favoriteError='';$('.favorite-results-panel').scrollTop=0;
  if (query.length<2) {renderCatalog();return;}
  renderCatalog();
  try {
    const url=new URL(searchApi);url.searchParams.set('q',query);url.searchParams.set('page',String(page));
    const response=await fetch(url,{signal:controller.signal});if (!response.ok) throw new Error();
    const payload=await response.json();
    if (sequence!==favoriteSequence || $('#catalog-query').value.trim()!==query) return;
    liveFavoriteResults={...payload,query,page,searched_at:new Date().toISOString()};renderCatalog();
  } catch(error) {
    if (controller.signal.aborted || sequence!==favoriteSequence) return;
    favoriteError='No se pudieron cargar las sugerencias. Puedes reintentar o utilizar la búsqueda de GitHub.';renderCatalog();
  }
}
async function refreshFavoriteSearches() {
  if(favoriteSaving)return;
  if (!$('#favorite-dialog').open && $('#pendientes').hidden) return;
  try {
    const response=await fetch('favorite-searches.json',{cache:'no-cache'});
    if (response.ok) {favoriteSearches=await response.json();renderCatalog();}
    await loadFavorites();
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
    const responses = await Promise.all([fetch('data.json',{cache:'no-cache'}), fetch('catalog.json',{cache:'no-cache'}), fetch('newsletters.json',{cache:'no-cache'}), fetch('favorites.json',{cache:'no-cache'}),fetch('favorite-searches.json',{cache:'no-cache'}),fetch('search-config.json',{cache:'no-cache'})]);
    if (!responses[0].ok) throw new Error('Datos no disponibles');
    offlineData = responses[0].headers.get('X-Cine-Madrid-Cache') === 'offline';
    data = await responses[0].json();
    catalog = responses[1].ok ? await responses[1].json() : [];
    watch = responses[3].ok ? await responses[3].json() : [];
    favoriteSearches=responses[4].ok ? await responses[4].json() : [];
    const searchConfig=responses[5].ok ? await responses[5].json() : {};
    searchApi=searchConfig.tmdb_api_url || '';
    favoritesApi=searchConfig.favorites_api_url || '';

    accountsEnabled=!!searchConfig.supabase_url;
    legacyFavorites=watch;watch=[];
    $('#favorite-help').textContent='Busca una película de TMDB y pulsa Añadir para guardarla en tu cuenta.';
    if(accountsEnabled){
      try{
        accountClient=await createAccount(searchConfig);
        const {data:{session},error}=await accountClient.auth.getSession();
        if(error)throw error;
        if(session?.user)await applyAccount(session.user);
        accountClient.auth.onAuthStateChange((_event,session)=>{
          // Avoid awaiting other auth calls inside Supabase's session lock.
          setTimeout(()=>applyAccount(session?.user || null),0);
        });
      }catch{$('#account-status').textContent='No se pudo iniciar el acceso a las cuentas. Recarga con conexión.';}
    }
    renderAccount();
    const posts = responses[2].ok ? await responses[2].json() : [];
    $('#updated').textContent = 'Último intento: ' + new Date(data.generated_at).toLocaleString('es-ES');
    const active = data.sources.filter(s => ['ok','empty'].includes(s.status)).length;
    $('#coverage').textContent = `Cobertura parcial · ${active} fuente${active === 1 ? '' : 's'} leída${active === 1 ? '' : 's'} correctamente · ${data.cinemas.length} recintos en inventario. Consulta el detalle de lecturas parciales y fuentes pendientes debajo.`;
    $('#inventory-count').textContent = `${data.cinemas.length} espacios`;
    const tmdb = data.tmdb || {};
    $('#agent-status').textContent = `TMDB: ${tmdb.status === 'ok' ? 'conectado' : tmdb.status === 'partial' ? 'lectura parcial' : 'pendiente o no disponible'} · ${tmdb.matched_movies || 0}/${tmdb.total_movies || data.movies.length} películas identificadas en la última consulta. Copilot sigue pendiente para las ambigüedades. Las identidades sin verificar no generan avisos de coincidencia.`;
    for (const cinema of data.cinemas) {
      const row = el('div',undefined,'source-row');
      const reading = data.sources.find(s => s.id === cinema.id);
      const state = reading?.status === 'ok' ? 'Lectura correcta' : reading?.status === 'partial' ? 'Lectura parcial' : reading?.status === 'error' ? 'Error de lectura' : reading?.status === 'empty' ? 'Sin sesiones anunciadas' : 'Pendiente';
      row.append(cinema.url ? link(cinema.name,cinema.url) : el('strong',cinema.name),el('span',`${state}${cinema.municipality && cinema.municipality !== 'Madrid' ? ' · ' + cinema.municipality : ''}${cinema.formats?.includes('IMAX') ? ' · Tiene sala IMAX' : ''}${reading?.last_session ? ' · Pases hasta ' + reading.last_session.slice(0,10) : ''}`));
      if (cinema.reading_note) row.append(el('small',cinema.reading_note,'fine'));
      if (cinema.schedule_url) row.append(link('Horarios · '+(cinema.schedule_label || 'fuente alternativa'),cinema.schedule_url));
      $('#sources').append(row);
    }
    for (const key of ['version','format','sort']) {
      const source = $('#' + key), target = $('#calendar-' + key); target.replaceChildren();
      for (const option of source.options) target.append(option.cloneNode(true));
    }
    render(); renderWatch(); renderIncidents(); connectionState();
    $('#calendar-expand').disabled = false;
    if (!posts.length) $('#newsletters').append(el('p','Todavía no hay ediciones publicadas.','empty'));
    for (const post of posts) {
      const article = el('article',undefined,'card'); article.append(el('h3',post.id),el('p',post.note));
      const list = el('div'); renderSessions(list,post.sessions); article.append(list); $('#newsletters').append(article);
    }
    const route = location.hash.slice(1);
    setView(route === 'calendario' ? 'cartelera' : route || 'cartelera', false);
    if (route === 'calendario') $('#calendar-dialog').showModal();
    const search=new URLSearchParams(location.search).get('favorite_search');
    if (search) {setView('pendientes');$('#catalog-query').value=search;favoritePage=Math.max(1,Number(new URLSearchParams(location.search).get('favorite_page')) || 1);renderCatalog();syncFavoriteViewport();$('#favorite-dialog').showModal();if(searchApi) queryFavoriteSuggestions();}
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
  if (key) { $('[data-filter="' + key + '"]').value = event.target.value; render(); }
};
$('#toggle-filters').onclick = () => {
  const expanded = $('#toggle-filters').getAttribute('aria-expanded') === 'true';
  $('#toggle-filters').setAttribute('aria-expanded', String(!expanded)); $('#advanced-filters').hidden = expanded;
};
$('#reset-filters').onclick = () => { all('#filters [data-filter], #sort').forEach(input => {input.value = input.id==='sort' ? 'votes' : '';});selectedCinemas.clear();selectedCategories=new Set(categories.map(([key])=>key));filmDaySelections=new WeakMap();render(); };
$('#sort').onchange=render;
all('[data-cinema-action]').forEach(button => {button.onclick=()=>{selectedCinemas=new Set(button.dataset.cinemaAction==='nearby' ? nearbyCinemas(data.cinemas.filter(c=>c.status==='active'),origin) : []);render();};});
$('#calendar-clear-day').onclick = () => setDay('');
$('#calendar-expand').onclick = () => { renderCalendar(); $('#calendar-dialog').showModal(); };
$('#show-day-in-list').onclick = () => { $('#calendar-dialog').close(); $('#results').scrollIntoView({block:'start'}); };
function shiftMonth(amount) {
  const next = new Date(Date.UTC(calendarYear, calendarMonth + amount, 1));
  calendarYear = next.getUTCFullYear(); calendarMonth = next.getUTCMonth(); renderCalendar();
}
$('#previous-month').onclick = () => shiftMonth(-1);
$('#next-month').onclick = () => shiftMonth(1);
$('#mini-previous-month').onclick=()=>shiftMonth(-1);
$('#mini-next-month').onclick=()=>shiftMonth(1);
all('[data-close]').forEach(button => {button.onclick = () => $('#' + button.dataset.close).close();});
all('dialog').forEach(dialog => {dialog.onclick = event => {if (event.target === dialog && (event.clientX < dialog.getBoundingClientRect().left || event.clientX > dialog.getBoundingClientRect().right || event.clientY < dialog.getBoundingClientRect().top || event.clientY > dialog.getBoundingClientRect().bottom)) dialog.close();};});
$('#show-location').onclick = () => { setView('cuenta'); $('#location-settings').open = true; $('#origin').focus(); };
$('#issue-filter').onchange = renderIncidents;
function syncFavoriteViewport(){
  const viewport=window.visualViewport, dialog=$('#favorite-dialog');
  dialog.style.setProperty('--favorite-viewport-height',(viewport?.height || window.innerHeight)+'px');
  dialog.style.setProperty('--favorite-viewport-top',(viewport?.offsetTop || 0)+'px');
}
function refreshFavoriteViewport(){if($('#favorite-dialog').open)syncFavoriteViewport();}
window.visualViewport?.addEventListener('resize',refreshFavoriteViewport);
window.visualViewport?.addEventListener('scroll',refreshFavoriteViewport);
window.addEventListener('resize',refreshFavoriteViewport);
$('#catalog-query').oninput = () => {clearTimeout(favoriteTimer);favoriteController?.abort();favoriteSequence++;favoritePage=1;favoriteError='';liveFavoriteResults=null;renderCatalog();if(searchApi) favoriteTimer=setTimeout(queryFavoriteSuggestions,450);};
setInterval(refreshFavoriteSearches,15000);window.addEventListener('focus',refreshFavoriteSearches);
$('#add-favorite').onclick = () => { $('#catalog-query').value = '';favoritePage=1;favoriteError='';liveFavoriteResults=null;renderCatalog(); syncFavoriteViewport();$('#favorite-dialog').showModal(); $('#catalog-query').focus({preventScroll:true}); };
async function selectOrigin(candidate) {
  const epoch=accountEpoch;
  try {
    if (!validOrigin(candidate)) {
      $('#origin-status').textContent='Comprobando dirección…';
      const url='https://www.cartociudad.es/geocoder/api/geocoder/find?'+new URLSearchParams({q:candidate.label});
      const response=await fetch(url);if (!response.ok) throw new Error();
      const value=await response.json(), point=Array.isArray(value) ? value[0] : value;
      candidate={...candidate,lat:Number(point.lat),lon:Number(point.lng)};
    }
    if (!validOrigin(candidate)) throw new Error();
    const point={lat:candidate.lat,lon:candidate.lon,label:candidate.label};
    if(epoch!==accountEpoch)return;
    if(accountUser){await accountRequest('profile',{method:'PUT',body:JSON.stringify({origin:point})});}
    else{guestOrigin=point;store('cm-origin',point);}
    if(epoch!==accountEpoch)return;origin=point;
    $('#origin').value=candidate.label;renderAccount();
    $('#origin-status').textContent=accountUser ? 'Origen guardado en tu cuenta.' : 'Origen guardado en este navegador. Entra para sincronizarlo.';
    $('#address-suggestions').replaceChildren();$('#location-settings').open=false;render();
    $('#origin-summary').focus();
  } catch {if(epoch===accountEpoch)$('#origin-status').textContent='No se pudo comprobar o guardar esa dirección. Vuelve a intentarlo.';}
}
async function lookupAddresses() {
  addressController?.abort();const controller=new AbortController();addressController=controller;
  const sequence=++addressSequence, query=$('#origin').value.trim();
  $('#address-suggestions').replaceChildren();if(query.length<4) return;
  $('#origin-status').textContent='Buscando direcciones reconocidas…';
  try {
    const q=/madrid/i.test(query) ? query : query+', Madrid';
    const url='https://www.cartociudad.es/geocoder/api/geocoder/candidates?'+new URLSearchParams({q,limit:'5',no_process:'municipio,poblacion,toponimo'});
    const response=await fetch(url,{signal:controller.signal});if(!response.ok) throw new Error();
    const candidates=addressCandidates(await response.json());
    if(sequence!==addressSequence || $('#origin').value.trim()!==query) return;
    for(const candidate of candidates) {
      const button=el('button',candidate.label,'address-option');button.type='button';button.onclick=()=>selectOrigin(candidate);$('#address-suggestions').append(button);
    }
    $('#origin-status').textContent=candidates.length ? 'Selecciona una dirección para guardarla.' : 'No se encontraron direcciones. Prueba con calle y número.';
  } catch(error) {if(!controller.signal.aborted && sequence===addressSequence) $('#origin-status').textContent='No se pudieron consultar las direcciones. Vuelve a pulsar Buscar dirección.';}
}
$('#origin').oninput=()=>{clearTimeout(addressTimer);addressController?.abort();addressSequence++;$('#address-suggestions').replaceChildren();$('#origin-status').textContent='';if($('#origin').value.trim().length>=4) addressTimer=setTimeout(lookupAddresses,650);};
$('#origin-form').onsubmit=event=>{event.preventDefault();clearTimeout(addressTimer);lookupAddresses();};
$('#clear-origin').onclick=async()=>{
  const epoch=accountEpoch;
  try{
    if(accountUser)await accountRequest('profile',{method:'PUT',body:JSON.stringify({origin:null})});
    else{guestOrigin=null;try{localStorage.removeItem('cm-origin');}catch{}}
    if(epoch!==accountEpoch)return;
    clearTimeout(addressTimer);addressController?.abort();addressSequence++;origin=null;
    $('#origin').value='';$('#address-suggestions').replaceChildren();$('#origin-status').textContent='Origen eliminado.';renderAccount();render();
  }catch{if(epoch===accountEpoch)$('#origin-status').textContent='No se pudo borrar el origen. Vuelve a intentarlo.';}
};
$('#google-login').onclick=async()=>{
  $('#google-login').disabled=true;
  try{
    const {error}=await accountClient.auth.signInWithOAuth({provider:'google',options:{redirectTo:new URL('./',location.href).href,queryParams:{prompt:'select_account'}}});
    if(error)throw error;
  }catch{$('#account-status').textContent='No se pudo abrir Google. Comprueba la configuración de acceso.';$('#google-login').disabled=false;}
};
$('#account-logout').onclick=async()=>{
  try{
    const {error}=await accountClient.auth.signOut({scope:'local'});if(error)throw error;
    await applyAccount(null);$('#favorite-dialog').close();
  }catch{$('#account-status').textContent='No se pudo cerrar la sesión. Vuelve a intentarlo.';}
};
$('#import-favorites').onclick=async()=>{
  const epoch=accountEpoch;$('#import-favorites').disabled=true;
  try{watch=await accountRequest('import',{method:'POST'});renderWatch();renderAccount();$('#watch-status').textContent='Favoritas anteriores importadas a tu cuenta.';}
  catch{if(epoch===accountEpoch)$('#watch-status').textContent='No se pudieron importar las favoritas. Vuelve a intentarlo.';}
  finally{$('#import-favorites').disabled=false;}
};
$('#import-origin').onclick=()=>selectOrigin(guestOrigin);


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
