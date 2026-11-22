// The phone view's logic without the page: the sticks, the mode buttons and the action grid
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { actionGrid, modeButtons, stickValue } from '../www/phonelogic.js';

test('stickValue: centre, the edge, kept inside the circle; up is a smaller y', () => {
  assert.deepEqual(stickValue(0, 0, 50), { x: 128, y: 128 });
  assert.equal(stickValue(100, 0, 50).x, 255);           // past the edge: the edge
  assert.equal(stickValue(-50, 0, 50).x, 1);
  assert.equal(stickValue(0, -50, 50).y, 1);              // finger up = stick forward
  assert.equal(stickValue(0, 50, 50).y, 255);
  const d = stickValue(50, 50, 50);                       // a diagonal stays on the circle
  assert.ok(Math.abs(d.x - 218) <= 1 && Math.abs(d.y - 218) <= 1);
});

test('modeButtons: no Go to a point on the droid, face tracking last, no combo = no start', () => {
  const modes = { goto: { combo: 'FOOT_PS_L2' }, forward: { combo: 'FOOT_UP_PS' }, patrol: { combo: null }, follow: { combo: 'DOME_UP_L2' } };
  const droid = modeButtons(modes, false);
  assert.deepEqual(droid.map((b) => b.mode), ['forward', 'patrol', 'follow', 'free', 'tracking']);
  assert.equal(droid.find((b) => b.mode === 'patrol').combo, null);
  assert.equal(droid.find((b) => b.mode === 'free').label, 'Free roam');
  assert.equal(droid.at(-1).combo, 'DOME_PS_L2');
  assert.equal(droid.at(-1).label, 'Face tracking');
  const sim = modeButtons(modes, true);
  assert.equal(sim[0].mode, 'goto');
  assert.equal(sim[0].label, 'Go to a point');
  assert.deepEqual(modeButtons({}, false).map((b) => b.combo), [null, null, null, null, 'DOME_PS_L2']);
});

test('actionGrid: favourites on top with their names, the rest without them, a search', () => {
  const g = actionGrid([{ combo: 'FOOT_UP_CROSS', name: 'Vol +' }], '');
  assert.equal(g.favs[0].name, 'Vol +');
  assert.equal(g.favs[0].what, 'Volume up');
  assert.ok(!g.rest.some((a) => a.combo === 'FOOT_UP_CROSS'));
  assert.ok(g.rest.length > 30);
  const holo = actionGrid([], 'holo').rest;
  assert.ok(holo.length >= 2 && holo.every((a) => /holo/i.test(a.what)));
  assert.deepEqual(actionGrid([], 'zzz').rest, []);
});

test('actionGrid: a combination given to a mode starts the mode, so it is no action', () => {
  const g = actionGrid([], '', { patrol: { combo: 'FOOT_UP_CROSS' } });
  assert.ok(!g.rest.some((a) => a.combo === 'FOOT_UP_CROSS'));
  assert.ok(!g.rest.some((a) => a.combo === 'DOME_PS_L2'));    // face tracking is in Modes
});
