// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { topicWants } from '../www/subthrottle.js';

test('a slow subscriber first does not slow down a faster one after it (WEB-1)', () => {
  const w = topicWants();
  const slow = [], fast = [];
  assert.equal(w.add('/scan', (m) => slow.push(m), 2000), 2000);   // the status bar
  assert.equal(w.add('/scan', (m) => fast.push(m), 200), 200);      // the Navigation page: ask again, faster
  for (let t = 0; t <= 2000; t += 200) w.deliver('/scan', t, t);
  assert.equal(fast.length, 11);              // every 200 ms
  assert.deepEqual(slow, [0, 2000]);          // still at its own 2 s
});

test('a slower one after a faster one: no new subscribe', () => {
  const w = topicWants();
  assert.equal(w.add('/pico/state', () => {}, 0), 0);
  assert.equal(w.add('/pico/state', () => {}, 1000), null);
  assert.equal(w.rate('/pico/state'), 0);
});

test('the fastest leaves: subscribe again at the slower rate; the last leaves: gone', () => {
  const w = topicWants();
  const a = () => {}, b = () => {};
  w.add('/range/x', a, 200);
  w.add('/range/x', b, 100);
  assert.equal(w.remove('/range/x', b), 200);
  assert.equal(w.remove('/range/x', a).gone, true);
  assert.equal(w.has('/range/x'), false);
  assert.equal(w.remove('/range/x', a), null);    // nothing left: nothing to do
});

test('a slower one leaves: nothing to send', () => {
  const w = topicWants();
  const a = () => {}, b = () => {};
  w.add('/t', a, 100);
  w.add('/t', b, 500);
  assert.equal(w.remove('/t', b), null);
  assert.equal(w.rate('/t'), 100);
});

test('rosbridge jitter: a 200 ms callback keeps a 195 ms stream', () => {
  const w = topicWants();
  const got = [];
  w.add('/t', (m) => got.push(m), 200);
  [0, 195, 390, 590].forEach((t) => w.deliver('/t', t, t));
  assert.equal(got.length, 4);
});

test('throttle 0 gets everything; a callback may unsubscribe itself while delivered', () => {
  const w = topicWants();
  const got = [];
  const once = () => { got.push('once'); w.remove('/t', once); };
  w.add('/t', once, 0);
  w.add('/t', (m) => got.push(m), 0);
  w.deliver('/t', 1, 0);
  w.deliver('/t', 2, 1);
  assert.deepEqual(got, ['once', 1, 2]);
});
