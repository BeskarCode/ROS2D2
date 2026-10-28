// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Navigation page: watch the navigator drive R2 (the real one or the simulated one), give it a
// goal, edit the simulated room, and read the telemetry and what goes to the Mega.
import { connect, publish, subscribe } from './rosbridge.js';
import { createNavMap } from './navmap.js';

const $ = (id) => document.getElementById(id);
const COL = { rplidar_c1: '#39c5cf', vl53l0x: '#a371f7', hcsr04: '#f0b429' };
const STATE_CLASS = { going: 'ok', arrived: 'ok', avoiding: 'warn', turning: 'warn', reversing: 'warn', waiting: 'warn',
                      stop: 'bad', 'gave up': 'bad', 'no data': 'bad' };

export const page = {
  sensors: {}, nav: {}, world: null, simSensors: null, pose: null, prevPose: null, poseAt: 0,
  scan: [], state: {}, auto: null, selected: null, trail: [], stateTimes: [],
};
const P = page;

// ---------- settings from the web server (sensors.yaml, nav.yaml) ----------
async function loadFiles() {
  try { P.sensors = (await (await fetch('api/sensors', { cache: 'no-store' })).json()).sensors || {}; } catch { /* restarting */ }
  try { P.nav = (await (await fetch('api/nav', { cache: 'no-store' })).json()).nav || {}; } catch { /* restarting */ }
  buildReadings();
}

// ---------- ROS ----------
const yawOf = (q) => Math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z));
subscribe('/odom', 'nav_msgs/msg/Odometry', (m) => {
  const p = m.pose.pose;
  P.prevPose = interpolatedPose() || { x: p.position.x, y: p.position.y, th: yawOf(p.orientation) };
  P.pose = { x: p.position.x, y: p.position.y, th: yawOf(p.orientation) };
  P.poseAt = performance.now();
  const t = P.trail[P.trail.length - 1];
  if (!t || Math.hypot(t[0] - P.pose.x, t[1] - P.pose.y) > 0.05) { P.trail.push([P.pose.x, P.pose.y]); if (P.trail.length > 400) P.trail.shift(); }
  $('pose').textContent = `x ${P.pose.x.toFixed(2)} · y ${P.pose.y.toFixed(2)} · ${Math.round(P.pose.th * 180 / Math.PI)}°`;
}, 100);
subscribe('/scan', 'sensor_msgs/msg/LaserScan', (m) => {
  const lidar = Object.values(P.sensors).find((s) => s.type === 'rplidar_c1');
  if (!lidar || !P.pose) return;
  const { x, y, th } = P.pose, pts = [];
  let nearest = Infinity;
  for (let i = 0; i < m.ranges.length; i++) {
    const r = m.ranges[i];
    if (r == null || !Number.isFinite(r) || r < m.range_min || r > m.range_max) continue;
    nearest = Math.min(nearest, r);
    const a = m.angle_min + i * m.angle_increment + lidar.yaw_deg * Math.PI / 180;
    const lx = lidar.x + r * Math.cos(a), ly = lidar.y + r * Math.sin(a);
    pts.push([x + lx * Math.cos(th) - ly * Math.sin(th), y + lx * Math.sin(th) + ly * Math.cos(th)]);
  }
  P.scan = pts;
  P.lidarNearest = nearest;
  P.scanAt = performance.now();
}, 200);
subscribe('/nav/state', 'std_msgs/msg/String', (m) => {
  P.state = JSON.parse(m.data);
  const now = performance.now();
  P.stateTimes = [...P.stateTimes.filter((t) => now - t < 2000), now];
  telemetry();
}, 100);
subscribe('/sim/world', 'std_msgs/msg/String', (m) => {
  P.world = JSON.parse(m.data);
  if (P.selected != null && !P.world.obstacles.some((o) => o.id === P.selected)) select(null);
  simMode(true);
  if (P.world.error) addLine(`· room: ${P.world.error}`, 'info');
});
subscribe('/sim/sensors', 'std_msgs/msg/String', (m) => { P.simSensors = JSON.parse(m.data); buildReadings(); });
subscribe('/r2/auto_mode', 'std_msgs/msg/Bool', (m) => {
  P.auto = m.data;
  $('automode').className = 'pill ' + (m.data ? 'ok' : '');
  $('automode').innerHTML = `<i class="fa-solid fa-gamepad"></i>auto: ${m.data ? 'ON' : 'off'}`;
});
subscribe('/mega/tx', 'std_msgs/msg/String', (m) => {
  if (m.data.startsWith('(not sent) ')) addLine('→ ' + m.data.slice(11) + '   (not sent)', 'unsent');
  else addLine('→ ' + m.data, /^(S1|S3|MD):/.test(m.data) ? 'sound' : 'tx');
});
subscribe('/mega/log', 'std_msgs/msg/String', (m) => addLine('← ' + m.data, 'rx'));

connect(() => {
  $('conn').className = 'pill ok';
  $('conn').innerHTML = '<i class="fa-solid fa-plug"></i>rosbridge ok';
  loadFiles();
});

function simMode(on) {
  $('simpill').hidden = !on;
  document.querySelectorAll('.simonly').forEach((e) => { e.hidden = !on; });
  $('megahint').textContent = on ? 'simulated Mega' : '–';
  $('maphint').textContent = on
    ? 'Click the floor to send R2 there. Drag an obstacle to move it; click it and press Delete (or right-click it) to remove it.'
    : 'Click the floor to send R2 there (in the odometry frame).';
}
simMode(false);

// ---------- commands ----------
const worldCmd = (cmd) => publish('/sim/world_cmd', 'std_msgs/msg/String', { data: JSON.stringify(cmd) });
function sendGoal(x, y) {
  publish('/nav/goal', 'geometry_msgs/msg/PoseStamped',
    { header: { frame_id: 'odom' }, pose: { position: { x, y, z: 0 }, orientation: { x: 0, y: 0, z: 0, w: 1 } } });
  addLine(`· goal x ${x.toFixed(2)}, y ${y.toFixed(2)}`, 'info');
}
function select(id) { P.selected = id; $('del').disabled = id == null; }
let moveTimer = 0;
const map = createNavMap($('map'), {
  onGoal: sendGoal,
  onSelect: select,
  onRemove: (id) => worldCmd({ op: 'remove', id }),
  onMove: (id, x, y, done) => {
    const now = performance.now();
    if (done || now - moveTimer > 100) { moveTimer = now; worldCmd({ op: 'move', id, x, y }); }
  },
});
$('cancel').onclick = () => { publish('/nav/cancel', 'std_msgs/msg/Empty', {}); addLine('· goal cancelled', 'info'); };
$('reset').onclick = () => { worldCmd({ op: 'reset' }); P.trail = []; };
$('del').onclick = () => { if (P.selected != null) worldCmd({ op: 'remove', id: P.selected }); };
const add = (kind, x, y) => worldCmd({ op: 'add', kind, x, y });
$('addpost').onclick = () => add('post', 0, -1.3);
$('addbox').onclick = () => add('box', -1.5, 1.2);
$('addlow').onclick = () => add('low', 0.6, -1.4);
addEventListener('keydown', (e) => {
  if ((e.key === 'Delete' || e.key === 'Backspace') && P.selected != null && !e.target.closest('input, select, textarea')) {
    worldCmd({ op: 'remove', id: P.selected });
  }
});

// ---------- telemetry ----------
function buildReadings() {
  const box = $('readings');
  box.innerHTML = Object.entries(P.sensors).map(([n, s]) => {
    const tag = P.simSensors ? (P.simSensors.includes(n) ? '<i class="sim">sim</i>' : '<i class="real">real</i>') : '';
    return `<div class="rd" data-n="${n}"><span class="n">${n}${tag}</span><span class="track">` +
           `<span class="fill" style="background:${COL[s.type]}"></span><span class="raw"></span><span class="stop"></span></span><b>–</b></div>`;
  }).join('');
}
function telemetry() {
  const st = P.state, filtered = st.filtered || {}, raw = st.raw || {}, stops = st.stops || {};
  for (const el of document.querySelectorAll('#readings .rd')) {
    const n = el.dataset.n, s = P.sensors[n];
    if (!s) continue;
    const lidar = s.type === 'rplidar_c1';
    const d = lidar ? (P.scanAt && performance.now() - P.scanAt < 1000 ? P.lidarNearest : undefined) : filtered[n];
    const max = Math.min(s.range_max, 3);
    const frac = (v) => (v == null || !Number.isFinite(v) ? 0 : 1 - Math.min(v, max) / max);
    const reporting = lidar ? d !== undefined : n in filtered;
    el.querySelector('b').textContent = !reporting ? 'no data' : s.pitch_deg > 30 ? 'floor ok'
      : d == null || !Number.isFinite(d) ? 'clear' : `${d.toFixed(2)} m`;
    const stop = stops[n] || 0, fill = el.querySelector('.fill');
    fill.style.width = `${Math.round(frac(d) * 100)}%`;
    fill.style.background = stop && d != null && d < stop ? '#f85149' : stop && d != null && d < stop * 2 ? '#d29922' : COL[s.type];
    const mk = el.querySelector('.stop');
    mk.style.display = stop ? '' : 'none';
    mk.style.left = `${frac(stop) * 100}%`;
    const rw = el.querySelector('.raw'), r0 = raw[n];
    rw.style.display = lidar || r0 == null || s.pitch_deg > 30 ? 'none' : '';
    if (r0 != null) rw.style.left = `${frac(r0) * 100}%`;
  }
  const state = st.state || '?';
  $('navpill').className = 'pill ' + (STATE_CLASS[state] || '');
  $('navpill').textContent = 'nav: ' + state;
  const col = { ok: 'var(--green)', warn: 'var(--amber)', bad: 'var(--red)' }[STATE_CLASS[state]] || 'var(--muted)';
  $('navstate').innerHTML = `<div class="big" style="color:${col}"></div><div class="why"></div>
    <div style="color:var(--muted);margin-top:4px">/foot/cmd_vel: ${(st.v ?? 0).toFixed(2)} m/s, ${Math.round((st.w ?? 0) * 180 / Math.PI)}°/s
    · tries ${st.tries ?? 0} · lidar ${P.scan.length} points</div>`;
  $('navstate').querySelector('.big').textContent = state;
  $('navstate').querySelector('.why').textContent = st.why || '';
  $('hz').textContent = `${P.stateTimes.length / 2} Hz`;
}

// ---------- the Mega's lines, repeats grouped ----------
let lastLine = '', repeat = 0;
function addLine(text, cls) {
  const box = $('log');
  if (text === lastLine && box.lastChild) { repeat++; box.lastChild.textContent = `${text}  ×${repeat + 1}`; return; }
  lastLine = text; repeat = 0;
  const el = document.createElement('div');
  el.className = cls;
  el.textContent = text;
  const atEnd = box.scrollTop + box.clientHeight >= box.scrollHeight - 20;
  box.append(el);
  while (box.children.length > 300) box.firstChild.remove();
  if (atEnd) box.scrollTop = box.scrollHeight;
}

// ---------- drawing: at the screen's rate, R2 sliding between the 10 Hz poses ----------
function interpolatedPose() {
  if (!P.pose) return null;
  if (!P.prevPose) return P.pose;
  const k = Math.min(1, (performance.now() - P.poseAt) / 100);
  const dth = Math.atan2(Math.sin(P.pose.th - P.prevPose.th), Math.cos(P.pose.th - P.prevPose.th));
  return { x: P.prevPose.x + (P.pose.x - P.prevPose.x) * k, y: P.prevPose.y + (P.pose.y - P.prevPose.y) * k, th: P.prevPose.th + dth * k };
}
export function frameState() {
  return {
    world: P.world, pose: interpolatedPose(), scan: P.scan, sensors: P.sensors, readings: P.state.filtered || {},
    stops: P.state.stops || {}, radius: P.nav.safety_radius, goal: P.state.goal, heading: P.state.heading,
    state: P.state.state, v: P.state.v, selected: P.selected, trail: P.trail,
    showRays: $('rays').checked, showTrail: $('trail').checked,
  };
}
export const drawers = [];
(function frame() {
  if (!document.hidden) {
    const st = frameState();
    map.draw(st);
    for (const d of drawers) d(st);
  }
  requestAnimationFrame(frame);
})();
