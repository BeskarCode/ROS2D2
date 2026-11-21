// Remote -> Shortcuts: which buttons each combination needs, in which order, and what it does
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { stepsFor, shortcutList, MD_ACTIONS, PRE_MS, HOLD_MS, GAP_MS } from '../www/shortcuts.js';
import { COMBOS } from '../www/modesform.js';

test('a plain arrow is that arrow on its own Nav, nothing first', () => {
  assert.deepEqual(stepsFor('FOOT_UP'), { first: { F: [], D: [] }, then: { F: ['UP'], D: [] } });
  assert.deepEqual(stepsFor('DOME_LEFT'), { first: { F: [], D: [] }, then: { F: [], D: ['LEFT'] } });
});

test('foot arrow + Cross/Circle/PS/L3: the modifier is on the dome Nav and goes down first', () => {
  for (const m of ['CROSS', 'CIRCLE', 'PS', 'L3']) {
    assert.deepEqual(stepsFor(`FOOT_DOWN_${m}`), { first: { F: [], D: [m] }, then: { F: ['DOWN'], D: [m] } });
  }
});

test('foot arrow + L1: L1 on the foot Nav itself', () => {
  assert.deepEqual(stepsFor('FOOT_RIGHT_L1'), { first: { F: ['L1'], D: [] }, then: { F: ['L1', 'RIGHT'], D: [] } });
});

test('dome arrow + Cross/Circle/PS/L3: the modifier is on the foot Nav', () => {
  assert.deepEqual(stepsFor('DOME_UP_PS'), { first: { F: ['PS'], D: [] }, then: { F: ['PS'], D: ['UP'] } });
  assert.deepEqual(stepsFor('DOME_LEFT_L3'), { first: { F: ['L3'], D: [] }, then: { F: ['L3'], D: ['LEFT'] } });
});

test('dome arrow + L1/L2 on the dome Nav; L2 + Cross splits across both', () => {
  assert.deepEqual(stepsFor('DOME_UP_L1'), { first: { F: [], D: ['L1'] }, then: { F: [], D: ['L1', 'UP'] } });
  assert.deepEqual(stepsFor('DOME_DOWN_L2_CROSS'),
    { first: { F: ['CROSS'], D: ['L2'] }, then: { F: ['CROSS'], D: ['L2', 'DOWN'] } });
});

test('PS + L2 (no arrow): PS first, then L2, on its own Nav', () => {
  assert.deepEqual(stepsFor('FOOT_PS_L2'), { first: { F: ['PS'], D: [] }, then: { F: ['PS', 'L2'], D: [] } });
  assert.deepEqual(stepsFor('DOME_PS_L2'), { first: { F: [], D: ['PS'] }, then: { F: [], D: ['PS', 'L2'] } });
});

test('every combination the modes can take has steps', () => {
  for (const c of COMBOS) assert.ok(stepsFor(c).then.F.length + stepsFor(c).then.D.length > 0, c);
});

test('the list: MarcDuino actions, face tracking, and no free combinations', () => {
  const l = shortcutList({});
  const by = Object.fromEntries(l.map((s) => [s.combo, s]));
  assert.equal(by.FOOT_UP_CROSS.what, 'Volume up');
  assert.equal(by.FOOT_UP_CROSS.kind, 'marcduino');
  assert.equal(by.DOME_PS_L2.kind, 'tracking');
  assert.equal(by.FOOT_DOWN_L1, undefined);           // free
  assert.equal(by.DOME_UP_L2, undefined);             // free
  assert.equal(by.FOOT_PS_L2, undefined);             // no mode on it: does nothing
  assert.equal(l.length, Object.keys(MD_ACTIONS).length + 1);
});

test('a combination given to a mode starts the mode instead of its MarcDuino action', () => {
  const l = shortcutList({ goto: { combo: 'FOOT_PS_L2' }, patrol: { combo: 'FOOT_UP_CROSS' }, follow: { combo: null } });
  const by = Object.fromEntries(l.map((s) => [s.combo, s]));
  assert.equal(by.FOOT_PS_L2.kind, 'mode');
  assert.equal(by.FOOT_PS_L2.what, 'Go to a point (on / off)');
  assert.equal(by.FOOT_UP_CROSS.kind, 'mode');
  assert.equal(by.FOOT_UP_CROSS.what, 'Patrol (on / off)');
  assert.equal(by.FOOT_UP_CROSS.label, 'Foot ↑ + Cross');
  assert.equal(l[0].kind, 'mode');                    // modes first
});

test('timings: modifiers first, then a press long enough, then a pause the sketch needs (> 1 s)', () => {
  assert.ok(PRE_MS >= 100 && HOLD_MS >= 250 && GAP_MS > 1000);
});
