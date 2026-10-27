// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { picoPill, sensorBadge } from '../www/picostate.js';

const up = (sensors = {}, more = {}) => ({ connected: true, firmware: '0.1.0', config_error: null, sensors, ...more });

test('the Pico pill', () => {
  assert.deepEqual(picoPill(null, 0), { cls: 'wait', text: 'Pico: no bridge' });
  assert.deepEqual(picoPill(up(), 3500), { cls: 'wait', text: 'Pico: no bridge' });
  assert.deepEqual(picoPill(up({}, { connected: false }), 100), { cls: 'bad', text: 'Pico: disconnected' });
  assert.deepEqual(picoPill(up(), 100), { cls: 'ok', text: 'Pico: connected · 0.1.0' });
  assert.deepEqual(picoPill(up({}, { config_error: 'pin 16 reserved' }), 100), { cls: 'bad', text: 'Pico: config error' });
});

test('a sensor card in the simulation', () => {
  assert.deepEqual(sensorBadge('tof_front', null, null, 0, true), { cls: 'sim', text: 'simulated' });
  assert.deepEqual(sensorBadge('tof_front', null, { range: 0.42, ageMs: 100 }, 0, true), { cls: 'sim', text: 'simulated · 0.42 m' });
});

test('a sensor card with no bridge or no Pico', () => {
  assert.deepEqual(sensorBadge('tof_front', null, null, 0, false), { cls: 'wait', text: 'waiting for the Pico' });
  assert.deepEqual(sensorBadge('tof_front', up(), null, 5000, false), { cls: 'wait', text: 'waiting for the Pico' });
  assert.deepEqual(sensorBadge('tof_front', up({}, { connected: false }), null, 100, false), { cls: 'bad', text: 'Pico disconnected' });
  assert.deepEqual(sensorBadge('tof_front', up({}, { config_error: 'x' }), null, 100, false), { cls: 'bad', text: 'Pico config error' });
});

test('a sensor card from the Pico', () => {
  const st = up({ a: 'not_responding', b: 'waiting', c: 'ok' });
  assert.deepEqual(sensorBadge('a', st, null, 100, false), { cls: 'off', text: 'not responding' });
  assert.deepEqual(sensorBadge('b', st, null, 100, false), { cls: 'wait', text: 'starting…' });
  assert.deepEqual(sensorBadge('c', st, { range: 0.42, ageMs: 100 }, 100, false), { cls: 'ok', text: '0.42 m' });
  assert.deepEqual(sensorBadge('c', st, { range: Infinity, ageMs: 100 }, 100, false), { cls: 'ok', text: 'nothing in range' });
  assert.deepEqual(sensorBadge('c', st, { range: 0.42, ageMs: 900 }, 100, false), { cls: 'wait', text: 'no reading' });
  assert.deepEqual(sensorBadge('c', st, null, 100, false), { cls: 'wait', text: 'no reading' });
  // saved in the console but not yet sent to the Pico
  assert.deepEqual(sensorBadge('new_one', st, null, 100, false), { cls: 'wait', text: 'starting…' });
});
