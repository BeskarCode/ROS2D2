// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { CPU_ZONES, PI_TEMP_ZONES, PICO_TEMP_ZONES, bytes, level, minMax, pct, throttleText, uptime, versionText, zone } from '../www/systemfmt.js';

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

test('zone: where a value sits in its ranges (Pi temperature, CPU load)', () => {
  // Pi 4/5: normal up to 65 °C working (in a box), warm to 80, it slows itself down from 80
  assert.deepEqual(zone(61.3, PI_TEMP_ZONES), { cls: 'ok', label: 'normal' });
  assert.deepEqual(zone(70, PI_TEMP_ZONES), { cls: 'warn', label: 'warm' });
  assert.deepEqual(zone(45, PI_TEMP_ZONES), { cls: 'ok', label: 'normal' });
  assert.deepEqual(zone(82, PI_TEMP_ZONES), { cls: 'bad', label: 'throttling' });
  assert.deepEqual(zone(50, CPU_ZONES), { cls: 'ok', label: 'normal' });
  assert.deepEqual(zone(85, CPU_ZONES), { cls: 'warn', label: 'busy' });
  assert.deepEqual(zone(97, CPU_ZONES), { cls: 'bad', label: 'saturated' });
  assert.deepEqual(zone(70, PICO_TEMP_ZONES), { cls: 'warn', label: 'warm' });
  assert.equal(zone(null, CPU_ZONES), null);
});

test('minMax: the lowest and highest seen', () => {
  let r = minMax(null, 55);
  assert.deepEqual(r, { min: 55, max: 55 });
  r = minMax(r, 61);
  r = minMax(r, 48);
  assert.deepEqual(r, { min: 48, max: 61 });
  assert.deepEqual(minMax(r, null), { min: 48, max: 61 });
});

test('uptime', () => {
  assert.equal(uptime(45), '45 s');
  assert.equal(uptime(3720), '1 h 02 min');
  assert.equal(uptime(600), '10 min');
  assert.equal(uptime(null), '–');
});
