export function madridDay(date = new Date()) {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Madrid' }).format(date);
}

export function filterSessions(sessions, filters, {today = madridDay(), ignoreDay = false} = {}) {
  const normalize = value => (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const query = normalize(filters.query);
  return sessions.filter(session => {
    const day = session.start.slice(0, 10), time = session.start.slice(11, 16);
    return day >= today
      && (!query || [session.title,session.director,...(session.search_titles || [])].some(title => normalize(title).includes(query)))
      && (ignoreDay || !filters.day || day === filters.day)
      && (!filters.cinema || session.cinema_id === filters.cinema)
      && (!filters.cinemas?.length || filters.cinemas.includes(session.cinema_id))
      && (!filters.category || (filters.category === 'repertory_events' ? (session.category === 'repertory' || session.special_tags?.length > 0) : filters.category === 'special' ? session.special_tags?.length > 0 : session.category === filters.category))
      && (!filters.format || session.format === filters.format)
      && (!filters.version || session.version === filters.version)
      && (!filters.after || time >= filters.after)
      && (!filters.before || time <= filters.before);
  });
}

export function distanceKm(origin, cinema) {
  if (![origin?.lat,origin?.lon,cinema?.lat,cinema?.lon].every(Number.isFinite)) return null;
  const radians = value => value * Math.PI / 180;
  const a = radians(cinema.lat-origin.lat), b = radians(cinema.lon-origin.lon);
  const q = Math.sin(a/2)**2 + Math.cos(radians(origin.lat))*Math.cos(radians(cinema.lat))*Math.sin(b/2)**2;
  return 6371*2*Math.atan2(Math.sqrt(q),Math.sqrt(Math.max(0,1-q)));
}
export function rankCinemas(cinemas, origin) {
  return [...cinemas].sort((a,b) => (distanceKm(origin,a) ?? Infinity)-(distanceKm(origin,b) ?? Infinity) || a.name.localeCompare(b.name,'es'));
}
export function nearbyCinemas(cinemas, origin, radius=2) {
  return cinemas.filter(cinema => distanceKm(origin,cinema)!==null && distanceKm(origin,cinema)<=radius).map(cinema => cinema.id);
}
export function groupFilms(sessions, order='time', now=new Date()) {
  const groups=new Map();
  for (const session of sessions) {
    // A verified identity unites cinemas and title aliases. Unresolved homonyms remain separate.
    const key=session.canonical_id && session.identity_status==='verified' ? session.canonical_id : session.source_work_id || session.movie_id;
    if (!groups.has(key)) groups.set(key,{key,slots:new Map(),vote_count:null});
    const group=groups.get(key);
    const slot=[session.cinema_id,session.start,session.version,session.format,session.room || ''].join('|');
    const existing=group.slots.get(slot);
    if (!existing || (existing.stale && !session.stale)) group.slots.set(slot,session);
    if (Number.isFinite(session.vote_count)) group.vote_count=Math.max(group.vote_count ?? 0,session.vote_count);
  }
  const result=[...groups.values()].map(group => {
    const list=[...group.slots.values()].sort((a,b)=>a.start.localeCompare(b.start));
    return {key:group.key,sessions:list,vote_count:group.vote_count,next:Math.min(...list.map(s=>new Date(s.start).getTime()).filter(time=>time>=now.getTime())),first:list[0].start};
  });
  return result.sort((a,b) => (order==='votes' ? (b.vote_count ?? -1)-(a.vote_count ?? -1) : 0) || a.next-b.next || a.first.localeCompare(b.first));
}

export function filmDays(sessions) {
  return [...new Set(sessions.map(session=>session.start.slice(0,10)))].sort();
}
export function chooseFilmDay(sessions, calendarDay='', override='', now=new Date()) {
  const days=filmDays(sessions);
  if (days.includes(override)) return override;
  if (days.includes(calendarDay)) return calendarDay;
  const next=sessions.filter(session=>new Date(session.start)>=now).sort((a,b)=>a.start.localeCompare(b.start))[0];
  return next ? next.start.slice(0,10) : days[0] || '';
}

export function countByDay(sessions) {
  const counts = new Map();
  for (const session of sessions) {
    const day = session.start.slice(0, 10);
    counts.set(day, (counts.get(day) || 0) + 1);
  }
  return counts;
}

export function monthCells(year, month) {
  const first = new Date(Date.UTC(year, month, 1));
  const mondayOffset = (first.getUTCDay() + 6) % 7;
  return Array.from({length: 42}, (_, index) => {
    const date = new Date(Date.UTC(year, month, index - mondayOffset + 1));
    return {day: date.toISOString().slice(0, 10), number: date.getUTCDate(), inMonth: date.getUTCMonth() === month};
  });
}
