// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs — Setup → IMU is wired in, with the console's shared pieces
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = (f) => readFileSync(new URL(`../www/${f}`, import.meta.url), 'utf8');
const section = (html, id) => { const a = html.indexOf(`<section id="${id}"`); return html.slice(a, html.indexOf('</section>', a)); };

test('the IMU tab sits between Sensors and Modes, with an icon', () => {
  const h = read('setup.html');
  assert.ok(h.indexOf('id="tab-sensors"') < h.indexOf('id="tab-imu"') && h.indexOf('id="tab-imu"') < h.indexOf('id="tab-modes"'));
  assert.match(h, /id="tab-imu"[^>]*title="[^"]+"><i class="fa-solid fa-compass"><\/i>IMU/);
});

test('the tab uses the shared pieces', () => {
  const s = section(read('setup.html'), 'imu');
  for (const k of ['class="card"', 'details class="howto"', 'class="systog"', 'fa-ruler-horizontal', 'fa-compass', 'fa-rotate-left', 'fa-burst'])
    assert.ok(s.includes(k), k);
});

test('setup.js knows the imu tab', () => {
  const j = read('setup.js');
  assert.match(j, /TABS = \[[^\]]*'imu'/);
  assert.ok(j.includes('imuTab.show()') && j.includes('imuTab.hide()'));
});

test('the tab talks to the node by its names', () => {
  const j = read('imu.js');
  for (const k of ['/imu/status', '/imu/data', '/imu/level_here', '/imu/heading_zero', '/imu/forget_calibration', "setParam('/imu'", 'confirmDialog', 'r2web.telemetry'])
    assert.ok(j.includes(k), k);
});

test('setParam can send text (port, box, front)', () => assert.match(read('rosbridge.js'), /string_value/));
