// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { FIELDS, changedKeys, toNavYaml } from '../www/navsettings.js';

const CFG = { safety_radius: 0.55, safety_cone_deg: 60, slow_from: 0.8, max_speed: 0.35, max_turn_deg: 15, accel: 0.25,
  turn_accel_deg: 20, max_drive_power: 40, max_turn_power: 30, goal_tolerance: 0.25, sensors_may_stop_earlier: true,
  filter: true, on_blocked: 'turn', allow_reverse: true, give_up_after: 3, search_turn: 0.5, search_free: 0.3,
  search_wide_deg: 60, search_near: 0.1, forward_stuck_s: 8,
  sounds: { auto_on: 'S1:$11', obstacle: 'S1:$21', blocked: 'S1:$31', give_up: 'S1:$41', arrived: 'S1:$W' } };

test('every nav.yaml setting is on the page once', () => {
  const keys = FIELDS.map((f) => f.key);
  assert.equal(new Set(keys).size, keys.length);
  assert.deepEqual([...keys].sort(), Object.keys(CFG).filter((k) => k !== 'sounds').sort());
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
