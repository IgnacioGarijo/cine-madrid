import test from 'node:test';
import assert from 'node:assert/strict';
import {monthCells, countByDay, filterSessions, madridDay,groupFilms,rankCinemas,nearbyCinemas} from '../web/calendar-utils.js';

test('month uses Monday-first layout and includes the leap day', () => {
  const cells = monthCells(2028, 1);
  assert.equal(cells.length, 42);
  assert.equal(new Date(cells[0].day + 'T12:00:00Z').getUTCDay(), 1);
  assert.equal(cells.filter(cell => cell.inMonth).length, 29);
  assert.ok(cells.some(cell => cell.day === '2028-02-29' && cell.inMonth));
});
test('month correctly crosses December to January', () => {
  assert.ok(monthCells(2026, 11).some(cell => cell.day === '2027-01-01'));
});
test('calendar and list share all filters, while calendar exposes other matching dates', () => {
  const sessions = [
    {id:'1',title:'Película',director:'Dirección',cinema_id:'a',start:'2026-11-16T20:00:00+01:00',category:'repertory',version:'VOSE'},
    {id:'2',title:'Película',director:'Dirección',cinema_id:'a',start:'2026-11-23T21:00:00+01:00',category:'repertory',version:'VOSE'},
    {id:'3',title:'Película',director:'Dirección',cinema_id:'b',start:'2026-11-23T21:00:00+01:00',category:'repertory',version:'VOSE'},
    {id:'4',title:'Película',director:'Dirección',cinema_id:'a',start:'2026-11-23T17:00:00+01:00',category:'repertory',version:'VOSE'},
    {id:'5',title:'Otra',cinema_id:'a',start:'2026-11-23T20:00:00+01:00',category:'premiere',version:'VOSE'}
  ];
  const filters = {query:'pelicula',day:'2026-11-16',cinema:'a',category:'repertory',version:'VOSE',after:'19:00',before:'22:00'};
  assert.deepEqual(filterSessions(sessions, filters, {today:'2026-11-11'}).map(s=>s.id), ['1']);
  const calendar = filterSessions(sessions, filters, {today:'2026-11-11',ignoreDay:true});
  assert.deepEqual(calendar.map(s=>s.id), ['1','2']);
  assert.equal(countByDay(calendar).get('2026-11-23'),1);
});
test('only special events survive the event filter and past days are excluded', () => {
  const sessions = [{id:1,title:'A',start:'2026-11-10T20:00:00+01:00',special_tags:['live_music']},
    {id:2,title:'A',start:'2026-11-12T20:00:00+01:00',special_tags:[]},
    {id:3,title:'A',start:'2026-11-12T20:00:00+01:00',special_tags:['live_music']}];
  assert.deepEqual(filterSessions(sessions, {category:'special'}, {today:'2026-11-11'}).map(s=>s.id), [3]);
});
test('today follows Madrid even before midnight UTC', () => {
  assert.equal(madridDay(new Date('2026-11-11T23:30:00Z')), '2026-11-12');
});

test('IMAX filter uses the individual session format, not the cinema facilities', () => {
  const sessions = [{id:1,title:'A',cinema_id:'same',start:'2026-11-12T18:00:00+01:00',format:'IMAX'},
    {id:2,title:'A',cinema_id:'same',start:'2026-11-12T20:00:00+01:00',format:null}];
  assert.deepEqual(filterSessions(sessions,{format:'IMAX'},{today:'2026-11-11'}).map(s=>s.id),[1]);
});

test('multiple cinemas and the combined repertory/events filter preserve their union', () => {
  const source=[{id:1,cinema_id:'a',category:'repertory'},{id:2,cinema_id:'b',category:'premiere',special_tags:['live_music']},{id:3,cinema_id:'c',category:'repertory'},{id:4,cinema_id:'a',category:'premiere'}].map(s=>({...s,start:'2026-11-12T20:00:00+01:00'}));
  assert.deepEqual(filterSessions(source,{cinemas:['a','b'],category:'repertory_events'},{today:'2026-11-11'}).map(s=>s.id),[1,2]);
});
test('one film unites cinemas, days and aliases without conflating unverified homonyms', () => {
  const base={canonical_id:'tmdb:149',identity_status:'verified',version:'VOSE'};
  const sessions=[{...base,movie_id:'a:1',title:'Akira',cinema_id:'a',start:'2026-11-12T20:00:00+01:00'},{...base,movie_id:'b:2',title:'AKIRA (1988)',cinema_id:'b',start:'2026-11-13T21:00:00+01:00'},
    {movie_id:'other:akira',title:'Akira',cinema_id:'c',start:'2026-11-13T21:00:00+01:00',identity_status:'needs_review'}];
  const groups=groupFilms(sessions,'time',new Date('2026-11-11T12:00:00Z'));
  assert.equal(groups.length,2);assert.equal(groups[0].sessions.length,2);
  assert.equal(groupFilms([...sessions,sessions[0]],'time',new Date('2026-11-11T12:00:00Z'))[0].sessions.length,2);
});
test('vote count orders films by recognisability, leaving missing values last', () => {
  const sessions=[{movie_id:'a',vote_count:10,start:'2026-11-12T20:00:00+01:00'},{movie_id:'b',vote_count:5000,start:'2026-11-13T20:00:00+01:00'},{movie_id:'c',start:'2026-11-11T20:00:00+01:00'}];
  assert.deepEqual(groupFilms(sessions,'votes',new Date('2026-11-11T12:00:00Z')).map(g=>g.key),['b','a','c']);
  assert.deepEqual(groupFilms(sessions,'time',new Date('2026-11-11T12:00:00Z')).map(g=>g.key),['c','a','b']);
});
test('cinemas rank by distance with unknown coordinates last and near selection excludes them', () => {
  const origin={lat:40,lon:-3}, cinemas=[{id:'far',name:'Far',lat:40.1,lon:-3},{id:'unknown',name:'Unknown'},{id:'near',name:'Near',lat:40.005,lon:-3}];
  assert.deepEqual(rankCinemas(cinemas,origin).map(c=>c.id),['near','far','unknown']);
  assert.deepEqual(nearbyCinemas(cinemas,origin),['near']);
});
