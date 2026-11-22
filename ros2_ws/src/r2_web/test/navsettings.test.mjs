// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { FIELDS, changedKeys, toNavYaml } from '../www/navsettings.js';

const CFG = { safety_radius: 0.55, safety_cone_deg: 60, slow_from: 0.8, max_speed: 0.35, max_turn_deg: 15, accel: 0.25,
  decel: 0.25, brake_decel: 0.25, wait_max_s: 4, reverse_max: 0.3, stuck_after_s: 12, free_s: 0.8, turn_accel_deg: 20, max_drive_power: 40, max_turn_power: 30, goal_tolerance: 0.25, sensors_may_stop_earlier: true,
  filter: true, on_blocked: 'turn', allow_reverse: true, give_up_after: 3, search_turn: 0.5, search_free: 0.3,
  search_wide_deg: 60, search_near: 0.1, forward_stuck_s: 8,
  wander: { max_speed: 0.15, radius: 2, turn_every_s: [8, 20], turn_deg: [30, 120], pause_chance: 0.3, pause_s: [3, 8],
    greet_size: 0.08, greet_s: 10, greet_cooldown_s: 20, blocked_s: 3, heading_home_deg: 30, hello: 'S1:$12', idle_sounds: [] },
  sounds: { auto_on: 'S1:$11', obstacle: 'S1:$21', blocked: 'S1:$31', give_up: 'S1:$41', arrived: 'S1:$W' } };

test('every nav.yaml setting is on the page once', () => {
  const keys = FIELDS.map((f) => f.key);
  assert.equal(new Set(keys).size, keys.length);
  const flat = Object.keys(CFG).filter((k) => k !== 'sounds' && k !== 'wander');
  // the wander block: numbers one field each, a [min, max] pair two (.0 and .1); its sounds are not on the page
  const wander = Object.entries(CFG.wander).flatMap(([k, v]) => (Array.isArray(v) && k !== 'idle_sounds' ? [`wander.${k}.0`, `wander.${k}.1`]
    : typeof v === 'number' ? [`wander.${k}`] : []));
  assert.deepEqual([...keys].sort(), [...flat, ...wander].sort());
});

test('toNavYaml writes every key and the sounds', () => {
  const y = toNavYaml({ ...CFG, search_turn: 0.75, on_blocked: 'reverse' });
  assert.match(y, /^search_turn: 0\.75$/m);
  assert.match(y, /^on_blocked: reverse$/m);
  assert.match(y, /^filter: true$/m);
  assert.match(toNavYaml({ ...CFG, accel: 1 }), /^accel: 1\.0$/m);          // stays a decimal for ROS
  assert.match(toNavYaml(CFG), /^max_turn_deg: 15$/m);
  assert.match(y, /^ {2}arrived: "S1:\$W"$/m);
});

test('changedKeys: the ones away from the defaults', () => {
  assert.deepEqual(changedKeys({ ...CFG, max_speed: 0.2 }, CFG), ['max_speed']);
  assert.deepEqual(changedKeys(CFG, CFG), []);
});

import { getK, setK, liveParam } from '../www/navsettings.js';
test('the wander block: written as its own block, pairs as [min, max], sounds kept', () => {
  const y = toNavYaml({ ...CFG, wander: { ...CFG.wander, radius: 3.5, idle_sounds: ['S1:$15'] } });
  assert.match(y, /^wander:$/m);
  assert.match(y, /^ {2}radius: 3\.5$/m);
  assert.match(y, /^ {2}turn_every_s: \[8, 20\]$/m);
  assert.match(y, /^ {2}hello: "S1:\$12"$/m);
  assert.match(y, /^ {2}idle_sounds: \["S1:\$15"\]$/m);
  assert.match(toNavYaml(CFG), /^ {2}idle_sounds: \[\]$/m);
});
test('getK / setK reach into the wander block and its pairs', () => {
  const c = JSON.parse(JSON.stringify(CFG));
  assert.equal(getK(c, 'wander.radius'), 2);
  assert.equal(getK(c, 'wander.turn_every_s.1'), 20);
  setK(c, 'wander.turn_every_s.0', 5);
  assert.deepEqual(c.wander.turn_every_s, [5, 20]);
  setK(c, 'max_speed', 0.2);
  assert.equal(c.max_speed, 0.2);
});
test('liveParam: the ROS parameter a field changes (a pair sends the whole list)', () => {
  const c = JSON.parse(JSON.stringify(CFG));
  assert.deepEqual(liveParam(c, 'wander.turn_every_s.1'), { name: 'wander.turn_every_s', value: [8, 20] });
  assert.deepEqual(liveParam(c, 'wander.radius'), { name: 'wander.radius', value: 2 });
  assert.deepEqual(liveParam(c, 'max_speed'), { name: 'max_speed', value: 0.35 });
});
import { readFileSync } from 'node:fs';
test('toNavYaml writes the fixture that parse_nav accepts (test_nav_api.py reads it back)', () => {
  const want = readFileSync(new URL('./fixtures/nav_from_form.yaml', import.meta.url), 'utf8').replace(/\r\n/g, '\n');
  const c = JSON.parse(JSON.stringify(CFG));
  Object.assign(c.wander, { radius: 3.5, turn_every_s: [5, 12], idle_sounds: ['S1:$15', 'S1:$16'] });
  assert.equal(toNavYaml(c), want);
});
