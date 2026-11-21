// padlink.js: who drives the virtual Navs, as the Mega bridge says on /mega/pads
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ownerState } from '../www/padlogic.js';   // padlink.js re-exports it (it needs a page)

test('ownerState: free, mine or another page', () => {
  assert.equal(ownerState({ owner: null }, 'a'), 'free');
  assert.equal(ownerState({ owner: 'a' }, 'a'), 'mine');
  assert.equal(ownerState({ owner: 'b' }, 'a'), 'other');
  assert.equal(ownerState({}, 'a'), 'free');               // an old bridge with no owner
  assert.equal(ownerState(null, 'a'), 'free');
});
