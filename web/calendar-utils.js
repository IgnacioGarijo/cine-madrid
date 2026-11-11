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
      && (!filters.category || (filters.category === 'special' ? session.special_tags?.length > 0 : session.category === filters.category))
      && (!filters.version || session.version === filters.version)
      && (!filters.after || time >= filters.after)
      && (!filters.before || time <= filters.before);
  });
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
