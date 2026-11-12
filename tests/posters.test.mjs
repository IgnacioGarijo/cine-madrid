import test from 'node:test';
import assert from 'node:assert/strict';
import {posterURL} from '../web/poster-utils.js';

test('posters accept canonical TMDB paths and reject arbitrary URLs and malformed paths',()=>{
  assert.equal(posterURL('/example_185-abc.jpg'),'https://image.tmdb.org/t/p/w185/example_185-abc.jpg');
  for(const path of [undefined,null,'','https://other.test/poster.jpg','//other.test/a.jpg','/../../x.jpg','/a.jpg?token=secret','javascript:bad'])assert.equal(posterURL(path),null);
});
