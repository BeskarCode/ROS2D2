// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup → IMU, what the tab shows, worked out without the page (node --test): R2's angles from /imu/data,
// the tilt's colour, the acceleration bars, the status pills from /imu/status, the box check and the
// first-time check steps that tick by themselves.

export const G = 9.80665;
export const BUMP_ALARM = 6;          // m/s²: a knock this strong is worth a look
const TILT_WARN = 10, TILT_BAD = 20;  // degrees
const STALE_MS = 3000;                // no /imu/status this long = no node

const DEG = 180 / Math.PI;
const wrap = (d) => ((((d + 180) % 360) + 360) % 360) - 180;

// R2's roll, pitch and yaw in degrees from a quaternion (ZYX, as the node)
export function euler(q) {
  const { x, y, z, w } = q;
  const sp = Math.max(-1, Math.min(1, 2 * (w * y - z * x)));
  return {
    roll: Math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)) * DEG,
    pitch: Math.asin(sp) * DEG,
    yaw: Math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)) * DEG,
  };
}

// degrees from level
export function tiltOf(roll, pitch) {
  const c = Math.cos(pitch / DEG) * Math.cos(roll / DEG);
  return Math.acos(Math.max(-1, Math.min(1, c))) * DEG;
}

export const tiltClass = (deg) => (deg > TILT_BAD ? 'bad' : deg > TILT_WARN ? 'warn' : 'ok');

// acceleration in R2's axes minus gravity as felt at that tilt (what moves R2), m/s²
export function linearAccel(roll, pitch, a) {
  const sr = Math.sin(roll / DEG), cr = Math.cos(roll / DEG), sp = Math.sin(pitch / DEG), cp = Math.cos(pitch / DEG);
  const g = [-G * sp, G * sr * cp, G * cr * cp];
  return a.map((v, i) => v - g[i]);
}

// a bar with 0 in the middle: where it starts and how wide, in % (full = the value that fills one side)
export function bar(v, full = 3) {
  const width = Math.min(Math.abs(v) / full, 1) * 50;
  return { left: v >= 0 ? 50 : 50 - width, width };
}

// the strip of pills at the top, from /imu/status and how old it is
export function statusPills(st, ageMs) {
  if (!st || ageMs > STALE_MS) return [{ text: 'no IMU node', cls: 'bad' }];
  if (!st.connected) {
    const p = [{ text: 'not connected', cls: 'bad' }, { text: st.port, cls: '' }];
    if (st.error) p.push({ text: st.error, cls: 'bad' });
    return p;
  }
  const p = [st.simulate ? { text: 'simulated', cls: 'warn' } : { text: 'BNO085 connected', cls: 'ok' },
    { text: `${st.fps} frames/s`, cls: st.fps >= 50 ? '' : 'warn' },
    { text: `checksum errors ${st.bad_frames}`, cls: st.bad_frames > 0 ? 'warn' : '' },
    ...(st.simulate ? [] : [{ text: st.port, cls: '' }]),     // simulated: its port is "simulated", said already
    { text: `box: ${st.box}`, cls: '' },
    st.levelled ? { text: 'levelled', cls: 'ok' } : { text: 'not levelled yet', cls: 'warn' }];
  if (!st.in_use) p.push({ text: 'not in use', cls: 'warn' });
  if (st.error) p.push({ text: st.error, cls: 'bad' });
  return p;
}

// the levelling says the board is upside down (roll near 180) or not: does that match the box chosen?
export function boxMismatch(st) {
  if (!st || !st.level) return '';
  const r = Math.abs(wrap(st.level.roll_deg));
  if (st.box === 'standing' && r > 135) return 'The board is upside down, as on the divider: is the box lying? Choose "lying" or check how it is screwed.';
  if (st.box === 'lying' && r < 45) return 'The board is the right way up, as on the floor: is the box standing? Choose "standing" or check how it is screwed.';
  return '';
}

// The first-time check, in order: 1 frames keep coming for a second; 2 tilting R2's front down makes pitch
// go up 5°; 3 turning R2 left makes heading go up 20° ('inverted' if it goes down); 4 by hand.
export function createChecks() {
  let since, pitch0, yaw0, st;
  const reset = () => { since = null; pitch0 = null; yaw0 = null; st = { 1: 'todo', 2: 'todo', 3: 'todo', 4: 'todo' }; };
  reset();
  return {
    feed({ t, fps, pitch, yaw }) {
      if (st[1] !== 'done') {
        if (fps < 50) { since = null; return; }
        if (since === null) since = t;
        if (t - since >= 1 - 1e-9) { st[1] = 'done'; pitch0 = pitch; }
        return;
      }
      if (st[2] !== 'done') {
        if (pitch - pitch0 >= 5) { st[2] = 'done'; yaw0 = yaw; }
        return;
      }
      if (st[3] === 'todo') {
        const d = wrap(yaw - yaw0);
        if (d >= 20) st[3] = 'done';
        else if (d <= -20) st[3] = 'inverted';
      }
    },
    mark(n) { st[n] = 'done'; },
    steps: () => [1, 2, 3, 4].map((n) => ({ n, state: st[n] })),
    reset,
  };
}
