// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { bytes, level, pct, throttleText, versionText } from '../www/systemfmt.js';

test('bytes', () => {
  assert.equal(bytes(12.3e9), '12.3 GB');
  assert.equal(bytes(512e6), '512 MB');
  assert.equal(bytes(900e3), '900 KB');
  assert.equal(bytes(null), '–');
});

test('pct', () => {
  assert.equal(pct(37.4), '37 %');
  assert.equal(pct(null), '–');
});

test('level: the free fraction against its warn and bad limits', () => {
  // SD: warn < 15 % free, bad < 5 %
  assert.equal(level(0.5, 0.15, 0.05), 'ok');
  assert.equal(level(0.10, 0.15, 0.05), 'warn');
  assert.equal(level(0.04, 0.15, 0.05), 'bad');
  // RAM: warn < 20 %, bad < 10 %
  assert.equal(level(0.19, 0.20, 0.10), 'warn');
  assert.equal(level(0.09, 0.20, 0.10), 'bad');
});

test('throttleText: what the Pi warns about', () => {
  assert.deepEqual(throttleText({ undervoltage_now: true, throttled_now: false, undervoltage_since_boot: true, throttled_since_boot: true }),
    ['Under-voltage now', 'Under-voltage since boot', 'Throttled since boot']);
  assert.deepEqual(throttleText({ undervoltage_now: false, throttled_now: null, undervoltage_since_boot: null, throttled_since_boot: null }), []);
  assert.deepEqual(throttleText(null), []);
});

test('versionText', () => {
  assert.equal(versionText({ commit: '265a841', date: '2026-11-11T23:50:00+01:00', dirty: false }), '265a841 · 2026-11-11');
  assert.equal(versionText({ commit: '265a841', date: '2026-11-11T23:50:00+01:00', dirty: true }), '265a841 · 2026-11-11 + local changes');
  assert.equal(versionText({ commit: null }), 'unknown');
  assert.equal(versionText(null), 'unknown');
});
