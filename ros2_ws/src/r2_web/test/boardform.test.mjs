// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { CONNECTORS, OPTIONS, toYaml } from '../www/boardform.js';

test('the options are the ones r2_pico_bridge/board_settings.py accepts', () => {
  assert.deepEqual(OPTIONS.display_timeout_s.map(([v]) => v), [10, 30, 60, 300, 0]);
  assert.deepEqual(OPTIONS.brightness.map(([v]) => v), [0, 1, 2, 3]);
  assert.deepEqual(OPTIONS.leds.map(([v]) => v), ['auto', 'on', 'off', 'errors']);
  assert.equal(OPTIONS.display_timeout_s.find(([v]) => v === 0)[1], 'never');
  assert.deepEqual(CONNECTORS, ['VL1', 'VL2', 'VL3', 'VL4', 'US1', 'US2', 'US3', 'US4', 'US5']);
});

test('toYaml: what the System tab saves (on/off quoted: bare, YAML reads them as true/false)', () => {
  assert.equal(toYaml({ display_timeout_s: 60, brightness: 3, leds: 'errors' }),
    '# The Pico carrier board, saved from the web console (Setup -> System). Hand edits are fine too.\n' +
    'display_timeout_s: 60\nbrightness: 3\nleds: errors\n');
  assert.match(toYaml({ display_timeout_s: 30, brightness: 2, leds: 'on' }), /leds: "on"\n/);
  assert.match(toYaml({ display_timeout_s: 30, brightness: 2, leds: 'off' }), /leds: "off"\n/);
});
