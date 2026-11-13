// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> System: what the live strip and the mirror of the Pico board show, from /pico/mirror
// (LED, FB and BTN of the Pico, protocol 3), /pico/state and the rest of the console's sources.
// Plain functions, no DOM: test/boardmirror.test.mjs.
import { connectorOf } from './sensormath.js';

export const CONNECTOR_NAMES = ['VL1', 'VL2', 'VL3', 'VL4', 'US1', 'US2', 'US3', 'US4', 'US5'];
export const LONG_PRESS_MS = 3000;
const W = 128, H = 64;

/** The display's picture (base64 of the 8 SSD1306 pages) as 128*64 pixels (1 = lit), or null. */
export function fbPixels(b64) {
  if (!b64) return null;
  let bin;
  try { bin = atob(b64); } catch { return null; }
  if (bin.length !== W * H / 8) return null;
  const px = new Uint8Array(W * H);
  for (let page = 0; page < 8; page++) {
    for (let x = 0; x < W; x++) {
      const v = bin.charCodeAt(page * W + x);
      for (let k = 0; k < 8; k++) if (v & (1 << k)) px[(page * 8 + k) * W + x] = 1;
    }
  }
  return px;
}

/** The two-colour display: the top 16 rows yellow, the rest blue. */
export const pixelColor = (y) => (y < 16 ? '#ffd400' : '#39c5cf');

/** {VL1: true, ..., PICO: true} from the LED line: 9 connector digits, then the Pico's own LED. */
export function ledsOf(digits) {
  if (typeof digits !== 'string' || !/^[01]{9,10}$/.test(digits)) return null;
  const out = Object.fromEntries(CONNECTOR_NAMES.map((c, i) => [c, digits[i] === '1']));
  if (digits.length === 10) out.PICO = digits[9] === '1';
  return out;
}

/** The PWR LED: the Pico cannot read it; on if an HC-SR04 answers (they need its 5 V), else unknown (null). */
export function pwrLit(pico) {
  const s = (pico && pico.sensors) || {};
  return Object.entries(s).some(([n, st]) => n.startsWith('sonar') && st === 'ok') ? true : null;
}

/** Each board connector with a sensor: {VL1: {name, m}} (m in metres, Infinity = nothing in range). */
export function readingsByConnector(sensors, ranges) {
  const out = {};
  for (const [name, s] of Object.entries(sensors || {})) {
    if (!s || !s.pico) continue;
    const c = connectorOf(s);
    if (c) out[c] = { name, m: ranges ? ranges[name] : undefined };
  }
  return out;
}

/** The strip: Mega, Pi, lidar, Pico board and each camera, green when found. */
export function stripItems({ mega, pi, lidar, pico, cameras }) {
  const items = [
    { key: 'mega', label: 'Mega', ok: !!mega, detail: mega ? 'connected' : 'not connected' },
    { key: 'pi', label: 'Raspberry Pi', ok: true, detail: pi && pi.temp_c != null ? `${Math.round(pi.temp_c)} °C` : 'online' },
    { key: 'lidar', label: 'Lidar', ok: !!(lidar && lidar.ok), detail: (lidar && lidar.detail) || 'not connected' },
    { key: 'pico', label: 'Pico board', ok: !!(pico && pico.connected),
      detail: pico && pico.connected ? (pico.firmware || 'connected') : 'not connected' },
  ];
  // a network camera (ok null): the Pi cannot tell from here whether it answers
  (cameras || []).forEach((c, i) => items.push({ key: `cam${i}`, label: c.title, ok: c.ok === null ? null : !!c.ok,
    detail: c.ok === null ? 'network' : c.ok ? 'plugged in' : 'not found' }));
  return items;
}

/** How long the button was held: a short press or a long one (the real button's 3 s). */
export const pressKind = (ms) => (ms >= LONG_PRESS_MS ? 'long' : 'short');
