// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { headLabel, radiusCircle } from '../www/wanderview.js';

const toPx = (x, y) => [100 + x * 50, 200 - y * 50];      // 50 px a metre, y up
const toLen = (m) => m * 50;

test('radiusCircle: Patrol\'s circle round its start, in pixels', () => {
  assert.deepEqual(radiusCircle({ mode: 'patrol', start: [1, 2], radius: 2 }, toPx, toLen), { cx: 150, cy: 100, r: 100 });
});

test('radiusCircle: nothing for Free roam, before a start or with no state', () => {
  assert.equal(radiusCircle({ mode: 'free', start: [1, 2], radius: null }, toPx, toLen), null);
  assert.equal(radiusCircle({ mode: 'patrol', start: null, radius: 2 }, toPx, toLen), null);
  assert.equal(radiusCircle(null, toPx, toLen), null);
});

test('headLabel: what the head is doing, in words', () => {
  assert.equal(headLabel({ state: 'walk' }), 'walking');
  assert.equal(headLabel({ state: 'look' }), 'looking around');
  assert.equal(headLabel({ state: 'greet' }), 'saying hello');
  assert.equal(headLabel({ state: 'turn_away' }), 'turning away');
  assert.equal(headLabel({ state: 'dancing' }), 'dancing');
  assert.equal(headLabel(null), '');
});
