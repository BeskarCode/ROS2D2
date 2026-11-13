// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { fbPixels, isLive, ledsOf, pixelColor, pressKind, pwrLit, readingsByConnector, stripItems } from '../www/boardmirror.js';

const b64 = (bytes) => Buffer.from(bytes).toString('base64');

test('fbPixels: SSD1306 pages, a byte per column, LSB on top', () => {
  const pic = new Uint8Array(1024);
  pic[0] = 0x01;          // page 0, column 0, row 0
  pic[128] = 0x80;        // page 1, column 0, row 15
  pic[1023] = 0x80;       // page 7, column 127, row 63
  const px = fbPixels(b64(pic));
  assert.equal(px.length, 128 * 64);
  assert.equal(px[0 * 128 + 0], 1);
  assert.equal(px[1 * 128 + 0], 0);
  assert.equal(px[15 * 128 + 0], 1);
  assert.equal(px[63 * 128 + 127], 1);
  assert.equal(px.reduce((a, b) => a + b, 0), 3);
});

test('fbPixels: anything but 1024 bytes is no picture', () => {
  assert.equal(fbPixels(b64(new Uint8Array(10))), null);
  assert.equal(fbPixels(null), null);
  assert.equal(fbPixels('@@@'), null);
});

test('pixelColor: the two-colour display, yellow on top', () => {
  assert.equal(pixelColor(0), '#ffd400');
  assert.equal(pixelColor(15), '#ffd400');
  assert.equal(pixelColor(16), '#39c5cf');
  assert.equal(pixelColor(63), '#39c5cf');
});

test('ledsOf: VL1..US5 from the LED digits', () => {
  assert.deepEqual(ledsOf('100010000'),
    { VL1: true, VL2: false, VL3: false, VL4: false, US1: true, US2: false, US3: false, US4: false, US5: false });
  assert.equal(ledsOf('100010000').PICO, undefined);       // 9 digits: no Pico LED known
  assert.equal(ledsOf('1000100001').PICO, true);           // the 10th is the Pico's own LED
  assert.equal(ledsOf('101'), null);
  assert.equal(ledsOf(null), null);
});

test('pwrLit: on if an HC-SR04 answers (they need the 5 V), else unknown', () => {
  assert.equal(pwrLit({ sensors: { sonar_front_left: 'ok', tof_front_left: 'ok' } }), true);
  assert.equal(pwrLit({ sensors: { sonar_front_left: 'not_responding', tof_front_left: 'ok' } }), null);
  assert.equal(pwrLit(null), null);
});

test('readingsByConnector: each connector its sensor and reading', () => {
  const sensors = {
    tof_front_left: { type: 'vl53l0x', pico: { xshut: 2 } },
    sonar_front_left: { type: 'hcsr04', pico: { trig: 10, echo: 11 } },
    odd: { type: 'hcsr04', pico: { trig: 26, echo: 27 } },      // not on the board
    lidar: { type: 'rplidar_c1' },
  };
  const r = readingsByConnector(sensors, { tof_front_left: 0.16, sonar_front_left: Infinity });
  assert.deepEqual(r.VL1, { name: 'tof_front_left', m: 0.16 });
  assert.deepEqual(r.US1, { name: 'sonar_front_left', m: Infinity });
  assert.equal(r.VL2, undefined);
  assert.equal(Object.keys(r).length, 2);
});

test('stripItems: Mega, Pi, lidar, Pico board, then the cameras', () => {
  const items = stripItems({
    mega: false, pi: { temp_c: 48 }, lidar: { ok: true, detail: '10 Hz' },
    pico: { connected: true, firmware: '0.3.0' },
    cameras: [{ title: 'Dome camera', ok: false }, { title: 'USB webcam', ok: true }],
  });
  assert.deepEqual(items.map((i) => i.key), ['mega', 'pi', 'lidar', 'pico', 'cam0', 'cam1']);
  assert.deepEqual(items[0], { key: 'mega', label: 'Mega', ok: false, detail: 'not connected' });
  assert.equal(items[1].ok, true);
  assert.equal(items[1].detail, '48 °C');
  assert.equal(items[2].detail, '10 Hz');
  assert.equal(items[3].detail, '0.3.0');
  assert.equal(items[4].ok, false);
  assert.equal(items[4].label, 'Dome camera');
  assert.equal(items[4].detail, 'not found');
  const net = stripItems({ mega: true, cameras: [{ title: 'cam1', ok: null }] });
  assert.equal(net[4].ok, null);
  assert.equal(net[4].detail, 'network');
});

test('pressKind: held 3 s or more is a long press', () => {
  assert.equal(pressKind(100), 'short');
  assert.equal(pressKind(2999), 'short');
  assert.equal(pressKind(3000), 'long');
});

test('isLive: the board is live only while /pico/state keeps coming and says connected', () => {
  const now = 100000;
  assert.equal(isLive({ connected: true }, now - 1000, now), true);
  assert.equal(isLive({ connected: true }, now - 3000, now), false);     // nothing for 3 s: stale
  assert.equal(isLive({ connected: false }, now, now), false);
  assert.equal(isLive(null, now, now), false);
});
