// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { COMBOS, comboChoices, comboLabel, hsvToRgb, losesAction, pickToColor, toYaml } from '../www/modesform.js';

const DEFAULTS = {
  goto: { combo: 'FOOT_PS_L2', sound_on: '', sound_off: '' },
  forward: { combo: null, sound_on: '', sound_off: '' },
  patrol: { combo: null, sound_on: '', sound_off: '' },
  follow: { combo: null, sound_on: 'S1:$12', sound_off: 'S1:$13', sound_lost: 'S1:$22', camera: 'cam1', color: null,
            hue_tol: 12, light_tol: 70, area_ref: null, distance: 1.5, max_speed: 0.3, search_s: 5 },
};
const cfg = () => JSON.parse(JSON.stringify(DEFAULTS));

// The case the Python test reads back with parse_modes (test_modes_api.py)
function fixedCfg() {
  let c = cfg();
  c.follow.combo = 'FOOT_UP_PS';
  c.patrol.combo = 'DOME_LEFT_L2_CROSS';
  c.forward.sound_on = 'MD:$PS1';
  Object.assign(c.follow, { hue_tol: 8, light_tol: 55, distance: 2.2, max_speed: 0.25, search_s: 0 });
  c = pickToColor({ h: 104, s: 201, v: 87.6, rgb: [20, 60, 88], warning: '', match: 0.21, area: 0.0712345 }, c);
  return c;
}

test('the 61 combos, in the firmware order', () => {
  assert.equal(COMBOS.length, 61);
  assert.equal(new Set(COMBOS).size, 61);
  assert.deepEqual(COMBOS.slice(0, 3), ['FOOT_PS_L2', 'FOOT_UP', 'FOOT_UP_CROSS']);
  assert.equal(COMBOS[25], 'DOME_UP');
  assert.equal(COMBOS.at(-1), 'DOME_RIGHT_L2_CIRCLE');
});

test('combo labels read like the controller', () => {
  assert.equal(comboLabel('FOOT_UP_PS'), 'Foot ↑ + PS');
  assert.equal(comboLabel('FOOT_PS_L2'), 'Foot PS + L2');
  assert.equal(comboLabel('DOME_LEFT_L2_CROSS'), 'Dome ← + L2 + Cross');
  assert.equal(comboLabel('DOME_RIGHT'), 'Dome →');
});

test('comboChoices marks the combos other modes have and never offers face tracking', () => {
  const c = cfg();
  c.patrol.combo = 'FOOT_DOWN_CIRCLE';
  const choices = comboChoices(c, 'follow');
  assert.equal(choices.length, 61);
  assert.ok(!choices.some((x) => x.name === 'DOME_PS_L2'));
  const by = Object.fromEntries(choices.map((x) => [x.name, x]));
  assert.equal(by.FOOT_PS_L2.taken_by, 'goto');
  assert.equal(by.FOOT_DOWN_CIRCLE.taken_by, 'patrol');
  assert.equal(by.FOOT_UP_PS.taken_by, null);
  assert.equal(by.FOOT_UP_PS.label, 'Foot ↑ + PS');
  // its own combo is free for itself
  assert.equal(comboChoices(c, 'goto').find((x) => x.name === 'FOOT_PS_L2').taken_by, null);
  // even if a server list carried it, face tracking is left out
  assert.deepEqual(comboChoices(c, 'follow', ['DOME_PS_L2', 'DOME_UP']).map((x) => x.name), ['DOME_UP']);
});

test('only a combo other than PS + L2 loses its MarcDuino action', () => {
  assert.equal(losesAction(null), false);
  assert.equal(losesAction('FOOT_PS_L2'), false);
  assert.equal(losesAction('FOOT_UP_PS'), true);
});

test('pickToColor copies h, s, v and the area, and keeps cfg as it was', () => {
  const c = cfg();
  const out = pickToColor({ h: 10.4, s: 200, v: 150, rgb: [1, 2, 3], warning: 'grey', match: 0.3, area: 0.12 }, c);
  assert.deepEqual(out.follow.color, { h: 10, s: 200, v: 150 });
  assert.equal(out.follow.area_ref, 0.12);
  assert.equal(c.follow.color, null);
  assert.equal(pickToColor({ h: 1, s: 2, v: 3, area: 0 }, c).follow.area_ref, null);
});

test('toYaml writes the fixture that parse_modes accepts', () => {
  const want = readFileSync(new URL('./fixtures/modes_from_form.yaml', import.meta.url), 'utf8').replace(/\r\n/g, '\n');
  assert.equal(toYaml(fixedCfg()), want);
});

test('a saved OpenCV colour shows as RGB', () => {
  assert.deepEqual(hsvToRgb({ h: 0, s: 255, v: 255 }), [255, 0, 0]);
  assert.deepEqual(hsvToRgb({ h: 60, s: 255, v: 255 }), [0, 255, 0]);
  assert.deepEqual(hsvToRgb({ h: 120, s: 255, v: 128 }), [0, 0, 128]);
  assert.deepEqual(hsvToRgb({ h: 10, s: 0, v: 200 }), [200, 200, 200]);
});

import { startMode } from '../www/modesform.js';
test('startMode: the mode PS + L2 starts, or null', () => {
  assert.equal(startMode(DEFAULTS), 'goto');
  assert.equal(startMode({ ...DEFAULTS, goto: { combo: null }, patrol: { combo: 'FOOT_PS_L2' } }), 'patrol');
  assert.equal(startMode({ ...DEFAULTS, goto: { combo: 'FOOT_UP' } }), null);
  assert.equal(startMode({}), null);
});
