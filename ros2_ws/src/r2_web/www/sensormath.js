// What the droid's sensors see, without DOM or three.js (tested with node --test).
// Sensors carry the sensors.yaml fields: metres and degrees in ROS axes (base_link):
// x forward, y left, z up; yaw_deg + = left, pitch_deg + = down.
// Screens never show signs: sideText() says "30° left".

export const R2 = {
  bodyR: 0.2286,     // 18" body
  heightM: 1.09,
  // outer feet and centre foot: centre (x, y), w across (along y), l along x
  feet: [
    { x: -0.04, y: 0.30, w: 0.15, l: 0.34 },
    { x: -0.04, y: -0.30, w: 0.15, l: 0.34 },
    { x: 0.14, y: 0, w: 0.12, l: 0.20 },     // centre foot, ahead (three-leg stance)
  ],
};

export const TYPES = {
  rplidar_c1: { prefix: 'lidar', label: 'RPLIDAR C1', colour: '#39c5cf', fov: [90, 360], range: [1, 12], fovDeg: 200, rangeMax: 12 },
  vl53l0x: { prefix: 'tof', label: 'VL53L0X', colour: '#a371f7', fov: [15, 35], range: [0.3, 2], fovDeg: 25, rangeMax: 1.2 },
  hcsr04: { prefix: 'sonar', label: 'HC-SR04', colour: '#f0b429', fov: [15, 40], range: [0.5, 4], fovDeg: 30, rangeMax: 3 },
};
// Pico GPIO a sensor may use: not the VL53L0X's I2C (GP16, GP17), the Pico's own (GP23-25),
// nor the carrier board's status LEDs (GP0, GP1, GP6-9, GP22, GP27, GP28) and button (GP26)
const PICO_RESERVED = [0, 1, 6, 7, 8, 9, 16, 17, 22, 23, 24, 25, 26, 27, 28];
export const PICO_GPIO = Array.from({ length: 29 }, (_, g) => g).filter((g) => !PICO_RESERVED.includes(g));

export const isLidar = (s) => s.type === 'rplidar_c1';

const rad = (d) => d * Math.PI / 180;
const deg = (r) => r * 180 / Math.PI;
/** Angle in (-180, 180]. */
export const norm = (a) => { const n = ((a % 360) + 540) % 360 - 180; return n === -180 ? 180 : n; };

/** ROS (x, y) -> SVG map in metres, front up, left on the left. */
export const toMap = (x, y) => [-y, -x];
export const fromMap = (sx, sy) => ({ x: -sy, y: -sx });
/** ROS (x, y, z) -> three.js (X left, Y up, Z forward). */
export const toThree = (x, y, z) => [y, z, x];

export function sideText(yawDeg) {
  const a = norm(yawDeg);
  if (Math.abs(a) < 0.5) return 'ahead';
  if (Math.abs(a) > 179.5) return 'behind';
  return `${Math.round(Math.abs(a))}° ${a > 0 ? 'left' : 'right'}`;
}

export function inRobot(x, y) {
  if (Math.hypot(x, y) <= R2.bodyR) return true;
  return R2.feet.some((f) => Math.abs(x - f.x) <= f.l / 2 && Math.abs(y - f.y) <= f.w / 2);
}

/** Distance from (x, y) to the droid's outline (body circle or a foot). */
export function edgeDistance(x, y) {
  return Math.min(Math.hypot(x, y) - R2.bodyR,
    ...R2.feet.map((f) => Math.hypot(Math.max(Math.abs(x - f.x) - f.l / 2, 0), Math.max(Math.abs(y - f.y) - f.w / 2, 0))));
}

// Vertical half-angle of the beam: the lidar is a flat slice, the others are cones
const vHalf = (s) => (isLidar(s) ? 0 : s.fov_deg / 2);

/** How far it reaches over the floor: a sensor tilted down hits the floor sooner. */
export function reach(s) {
  const down = s.pitch_deg + vHalf(s);
  if (s.pitch_deg <= 0 || down <= 0) return s.range_max;
  return Math.min(s.range_max, s.z / Math.tan(rad(Math.min(down, 89.9))) + s.z * Math.tan(rad(vHalf(s))));
}

/**
 * Distance the sensor would read to something at (x, y) of width `size` and `heightTop`
 * tall, or null if it cannot see it (outside its cone or range, behind the droid, or
 * the beam passes over it).
 */
export function sees(s, x, y, size = 0, heightTop = Infinity) {
  const dx = x - s.x, dy = y - s.y;
  const d = Math.max(0, Math.hypot(dx, dy) - size / 2);
  if (d > reach(s)) return null;
  const half = s.fov_deg / 2 + (size ? deg(Math.atan2(size / 2, Math.max(d, 1e-3))) : 0);
  if (Math.abs(norm(deg(Math.atan2(dy, dx)) - s.yaw_deg)) > half) return null;
  for (let k = 0.15; k < 1; k += 0.05) {
    if (Math.hypot(dx * k, dy * k) > 0.04 && inRobot(s.x + dx * k, s.y + dy * k)) return null;
  }
  if (heightTop !== Infinity) {
    const lowest = s.z - d * Math.tan(rad(s.pitch_deg + vHalf(s)));
    if (lowest > heightTop) return null;
  }
  return d;
}

/**
 * What the sensors cover around the droid, on a grid: near = share of the ground up to
 * 0.5 m from the outline, far = up to 1 m (0..1). gaps: [x, y, edgeDistance] not seen.
 * blind: [from, to] sectors (screen degrees: 0 front, + right) uncovered within 0.5 m.
 * Sensors with found === false do not count.
 */
export function coverage(sensors, step = 0.05) {
  const live = sensors.filter((s) => s.found !== false);
  let n50 = 0, c50 = 0, n100 = 0, c100 = 0;
  const gaps = [];
  const bins = new Array(36).fill(0);
  for (let x = -1.3; x <= 1.3 + 1e-9; x += step) {
    for (let y = -1.3; y <= 1.3 + 1e-9; y += step) {
      if (inRobot(x, y)) continue;
      const e = edgeDistance(x, y);
      if (e > 1.0) continue;
      const ok = live.some((s) => sees(s, x, y) !== null);
      n100++; if (ok) c100++;
      if (e <= 0.5) { n50++; if (ok) c50++; }
      if (!ok) {
        gaps.push([x, y, e]);
        if (e <= 0.5) bins[Math.floor((norm(-deg(Math.atan2(y, x))) + 180) / 10) % 36]++;
      }
    }
  }
  const blind = [];
  let start = null;
  for (let i = 0; i <= 36; i++) {
    const g = i < 36 && bins[i] > 2;
    if (g && start === null) start = i;
    if (!g && start !== null) { blind.push([start * 10 - 180, i * 10 - 180]); start = null; }
  }
  return { near: n50 ? c50 / n50 : 0, far: n100 ? c100 / n100 : 0, gaps, blind };
}

const SITES = [[10, 'front'], [67.5, 'front_left'], [112.5, 'left'], [170, 'rear_left'], [180.1, 'rear']];

/** Default name type_site: where it points (or where it sits, when it points straight ahead). */
export function defaultName(s, taken) {
  const prefix = TYPES[s.type].prefix;
  let base = prefix;
  if (!isLidar(s)) {
    let site;
    if (s.pitch_deg > 30) site = 'floor';
    else {
      const a = Math.abs(norm(s.yaw_deg)) >= 10 ? norm(s.yaw_deg) : norm(deg(Math.atan2(s.y, s.x)));
      site = SITES.find(([lim]) => Math.abs(a) < lim)[1];
      if (a < 0) site = site.replace('left', 'right');
    }
    base = `${prefix}_${site}`;
  }
  if (!taken.has(base)) return base;
  for (let i = 2; ; i++) if (!taken.has(`${base}_${i}`)) return `${base}_${i}`;
}

/** A name typed by hand, trimmed, or null if empty, invalid or already used. */
export function uniqueName(name, taken) {
  const n = String(name).trim();
  return /^[a-z][a-z0-9_]*$/.test(n) && !taken.has(n) ? n : null;
}
