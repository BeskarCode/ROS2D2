// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Navigation page: watch the navigator drive R2 (the real one or the simulated one), give it a
// goal, edit the simulated room, and read the telemetry and what goes to the Mega.
import { connect, publish, subscribe } from './rosbridge.js';
import { MODELS } from './models.js';
import { createNavMap } from './navmap.js';
import { createNavView3d } from './navview3d.js';
import { freeText, nearestPoint } from './sensormath.js';

const $ = (id) => document.getElementById(id);
const COL = { rplidar_c1: '#39c5cf', vl53l0x: '#a371f7', hcsr04: '#f0b429' };
const STATE_CLASS = { going: 'ok', arrived: 'ok', forward: 'ok', avoiding: 'warn', turning: 'warn', reversing: 'warn', waiting: 'warn',
                      searching: 'warn', stop: 'bad', 'gave up': 'bad', 'no data': 'bad' };
const MODES = [['goto', 'fa-location-crosshairs', 'Go to a point'], ['forward', 'fa-arrow-up', 'Go forward'],
               ['patrol', 'fa-route', 'Patrol'], ['follow', 'fa-shirt', 'Follow a colour']];
const ROOM_LABELS = { default: 'Test room', living: 'Living room', corridor: 'Narrow corridor', rooms: 'Several rooms', event: 'Event with people' };

export const page = {
  // until /odom arrives (it needs the Mega or the simulator) the droid stands at the origin,
  // so the lidar and the sensors still show with R2 on the bench
  sensors: {}, nav: {}, world: null, simSensors: null, pose: { x: 0, y: 0, th: 0 }, prevPose: null, poseAt: 0,
  scan: [], state: {}, auto: null, selected: null, trail: [], stateTimes: [],
  mode: '', route: [], clickRoute: false,
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
  const { x, y, th } = P.pose, pts = [], base = [];
  let nearest = Infinity;
  for (let i = 0; i < m.ranges.length; i++) {
    const r = m.ranges[i];
    if (r == null || !Number.isFinite(r) || r < m.range_min || r > m.range_max) continue;
    nearest = Math.min(nearest, r);
    const a = m.angle_min + i * m.angle_increment + lidar.yaw_deg * Math.PI / 180;
    const lx = lidar.x + r * Math.cos(a), ly = lidar.y + r * Math.sin(a);
    base.push([lx, ly]);
    pts.push([x + lx * Math.cos(th) - ly * Math.sin(th), y + lx * Math.sin(th) + ly * Math.cos(th)]);
  }
  P.scan = pts;
  P.near = nearestPoint(base);
  P.lidarNearest = nearest;
  P.scanAt = performance.now();
}, 200);
subscribe('/nav/state', 'std_msgs/msg/String', (m) => {
  P.state = JSON.parse(m.data);
  // the navigator's copy of the route wins (another browser may have changed it)
  if (P.state.mode === 'patrol' && Array.isArray(P.state.route) && JSON.stringify(P.state.route) !== JSON.stringify(P.route)) {
    P.route = P.state.route;
    showRoute();
  }
  const now = performance.now();
  P.stateTimes = [...P.stateTimes.filter((t) => now - t < 2000), now];
  telemetry();
}, 100);
subscribe('/sim/world', 'std_msgs/msg/String', (m) => {
  const first = !P.world;
  P.world = JSON.parse(m.data);
  showRooms();
  if (first) buildReadings();
  showSwitches();
  if (P.selected != null && !P.world.obstacles.some((o) => o.id === P.selected)) select(null);
  simMode(true);
  if (P.world.error) addLine(`· room: ${P.world.error}`, 'info');
});
subscribe('/sim/sensors', 'std_msgs/msg/String', (m) => { P.simSensors = JSON.parse(m.data); buildReadings(); });
subscribe('/r2/mode', 'std_msgs/msg/String', (m) => { P.mode = m.data; showModes(); });
subscribe('/r2/auto_mode', 'std_msgs/msg/Bool', (m) => {
  P.auto = m.data;
  showModes();
  $('automode').className = 'pill ' + (m.data ? 'ok' : '');
  $('automode').innerHTML = `<i class="fa-solid fa-gamepad"></i>auto: ${m.data ? 'ON' : 'off'}`;
  // in simulation the page can press the fake Mega's PS + L2: ON when off, OFF when on
  $('autobtn').innerHTML = m.data ? '<i class="fa-solid fa-stop"></i>Autonomous OFF' : '<i class="fa-solid fa-play"></i>Autonomous ON';
  $('autobtn').className = m.data ? '' : 'primary';
});
subscribe('/mega/tx', 'std_msgs/msg/String', (m) => {
  if (m.data.startsWith('(not sent) ')) addLine('→ ' + m.data.slice(11) + '   (not sent)', 'unsent');
  else addLine('→ ' + m.data, /^(S1|S3|MD):/.test(m.data) ? 'sound' : 'tx');
});
subscribe('/mega/log', 'std_msgs/msg/String', (m) => addLine('← ' + m.data, 'rx'));
// without the Mega the telemetry still shows (lidar, Pico), but nothing reaches the feet
// and there is no /odom: R2 stays drawn at the origin
let megaConnected = false;
subscribe('/mega/connected', 'std_msgs/msg/Bool', (m) => { megaConnected = m.data; showMega(); });
function showMega() {
  $('megapill').className = 'pill ' + (megaConnected ? 'ok' : 'bad');
  $('megapill').innerHTML = `<i class="fa-solid fa-microchip"></i>mega: ${megaConnected ? 'connected' : 'not connected'}`;
  if (!$('simpill').hidden) return;
  $('megahint').textContent = megaConnected ? 'connected' : 'not connected: telemetry only, the feet will not move';
}

connect(() => {
  $('conn').className = 'pill ok';
  $('conn').innerHTML = '<i class="fa-solid fa-plug"></i>rosbridge ok';
  loadFiles();
});

function simMode(on) {
  $('simpill').hidden = !on;
  document.querySelectorAll('.simonly').forEach((e) => { e.hidden = !on; });
  if (on) $('megahint').textContent = 'simulated Mega';
  else showMega();
  $('maphint').textContent = on
    ? 'Click the floor to send R2 there. Drag an obstacle to move it; click it and press Delete (or right-click it) to remove it.'
    : 'Click the floor to send R2 there (in the odometry frame). With "route point", clicks make the patrol route.';
}
simMode(false);

// ---------- commands ----------
const worldCmd = (cmd) => publish('/sim/world_cmd', 'std_msgs/msg/String', { data: JSON.stringify(cmd) });
function sendGoal(x, y) {
  publish('/nav/goal', 'geometry_msgs/msg/PoseStamped',
    { header: { frame_id: 'odom' }, pose: { position: { x, y, z: 0 }, orientation: { x: 0, y: 0, z: 0, w: 1 } } });
  addLine(`· goal x ${x.toFixed(2)}, y ${y.toFixed(2)}`, 'info');
}
function select(id) { P.selected = id; $('del').disabled = $('shirt').disabled = id == null; }
let moveTimer = 0;
// ---------- rooms, modes, patrol route, sensors off (rooms, modes and sensors: simulator only) ----------
function showRooms() {
  const sel = $('room'), names = P.world.rooms || [];
  if (sel.options.length !== names.length) {
    sel.innerHTML = names.map((n) => `<option value="${n}">${ROOM_LABELS[n] || n}</option>`).join('');
  }
  if (P.world.name && document.activeElement !== sel) sel.value = P.world.name;
}
$('room').onchange = () => { worldCmd({ op: 'room', name: $('room').value }); P.trail = []; addLine(`· room: ${$('room').selectedOptions[0].textContent}`, 'info'); };
$('modebtns').innerHTML = MODES.map(([m, icon, label]) =>
  `<button data-mode="${m}" title="${label}: on (press again: off)"><i class="fa-solid ${icon}"></i>${label}</button>`).join('');
$('modebtns').querySelectorAll('button').forEach((b) => { b.onclick = () => worldCmd({ op: 'press', what: `mode:${b.dataset.mode}` }); });
function showModes() {
  $('modebtns').querySelectorAll('button').forEach((b) => b.classList.toggle('on', !!P.auto && P.mode === b.dataset.mode));
}
function setClick(route) {
  P.clickRoute = route;
  $('click-goal').classList.toggle('on', !route);
  $('click-route').classList.toggle('on', route);
}
$('click-goal').onclick = () => setClick(false);
$('click-route').onclick = () => setClick(true);
function sendRoute() {
  publish('/nav/patrol', 'std_msgs/msg/String', { data: JSON.stringify(P.route.map(([x, y]) => [+x.toFixed(2), +y.toFixed(2)])) });
  showRoute();
}
function showRoute() {
  $('routeinfo').textContent = P.route.length ? `patrol route: ${P.route.length} point${P.route.length > 1 ? 's' : ''}` : 'no patrol route';
}
$('clearroute').onclick = () => { P.route = []; sendRoute(); addLine('· patrol route cleared', 'info'); };
showRoute();
function onFloor(x, y) {
  if (!P.clickRoute) return sendGoal(x, y);
  P.route.push([x, y]);
  sendRoute();
  addLine(`· route point ${P.route.length}: x ${x.toFixed(2)}, y ${y.toFixed(2)}`, 'info');
}
function showSwitches() {
  const off = new Set((P.world && P.world.off) || []);
  document.querySelectorAll('#readings .sw').forEach((b) => {
    const on = !off.has(b.dataset.sw);
    b.classList.toggle('off', !on);
    b.innerHTML = on ? '<i class="fa-solid fa-power-off"></i>on' : '<i class="fa-solid fa-power-off"></i>off';
    b.title = on ? 'Simulate this sensor unplugged (only in the simulator)' : 'Plug it back in (simulator)';
  });
}
const map = createNavMap($('map'), {
  onGoal: onFloor,
  onSelect: select,
  onRemove: (id) => worldCmd({ op: 'remove', id }),
  onMove: (id, x, y, done) => {
    const now = performance.now();
    if (done || now - moveTimer > 100) { moveTimer = now; worldCmd({ op: 'move', id, x, y }); }
  },
});
$('cancel').onclick = () => { publish('/nav/cancel', 'std_msgs/msg/Empty', {}); addLine('· goal cancelled', 'info'); };
$('reset').onclick = () => { worldCmd({ op: 'reset' }); P.trail = []; };
$('autobtn').onclick = () => worldCmd({ op: 'press', what: 'button' });
$('stickbtn').onclick = () => worldCmd({ op: 'press', what: 'stick' });
$('del').onclick = () => { if (P.selected != null) worldCmd({ op: 'remove', id: P.selected }); };
const add = (kind, x, y) => worldCmd({ op: 'add', kind, x, y });
$('addpost').onclick = () => add('post', 0, -1.3);
$('addbox').onclick = () => add('box', -1.5, 1.2);
$('addperson').onclick = () => worldCmd({ op: 'add', kind: 'post', x: 0, y: -1.3, r: 0.15, height: 1.7, marker: true });
$('shirt').onclick = () => {
  const o = P.world && P.world.obstacles.find((q) => q.id === P.selected);
  if (o) worldCmd({ op: 'marker', id: o.id, on: !o.marker });
};
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
    const sw = P.world ? `<button class="sw" data-sw="${n}"></button>` : '<span></span>';
    return `<div class="rd" data-n="${n}"><span class="n">${n}${tag}</span><span class="track">` +
           `<span class="fill" style="background:${COL[s.type]}"></span><span class="raw"></span><span class="stop"></span></span><b>–</b>${sw}</div>`;
  }).join('');
  box.querySelectorAll('.sw').forEach((b) => {
    b.onclick = () => worldCmd({ op: 'sensor', name: b.dataset.sw, on: b.classList.contains('off') });
  });
  showSwitches();
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
    const ignored = (st.ignored || []).includes(n);
    el.style.opacity = ignored ? 0.45 : '';
    el.querySelector('b').textContent = (ignored ? 'ignored · ' : '') + (!reporting ? 'no data' : s.pitch_deg > 30 ? 'floor ok'
      : d == null || !Number.isFinite(d) ? 'clear' : `${d.toFixed(2)} m`);
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
    · tries ${st.tries ?? 0} · lidar ${P.scan.length} points${lidarFree() ? ` · ${freeText(lidarFree())}` : ''}</div>`;
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
// the free circle only while the lidar is talking
const lidarNear = () => (P.scanAt && performance.now() - P.scanAt < 1000 ? P.near : null);
const lidarFree = () => (lidarNear() ? lidarNear().r : null);
function interpolatedPose() {
  if (!P.pose) return null;
  if (!P.prevPose) return P.pose;
  const k = Math.min(1, (performance.now() - P.poseAt) / 100);
  const dth = Math.atan2(Math.sin(P.pose.th - P.prevPose.th), Math.cos(P.pose.th - P.prevPose.th));
  return { x: P.prevPose.x + (P.pose.x - P.prevPose.x) * k, y: P.prevPose.y + (P.pose.y - P.prevPose.y) * k, th: P.prevPose.th + dth * k };
}
export function frameState() {
  return {
    world: P.world, pose: interpolatedPose(), scan: P.scan, free: lidarFree(), near: lidarNear(), sensors: P.sensors, readings: P.state.filtered || {},
    stops: P.state.stops || {}, radius: P.nav.safety_radius, goal: P.state.goal, heading: P.state.heading,
    state: P.state.state, v: P.state.v, selected: P.selected, trail: P.trail,
    route: P.route, routeI: P.state.mode === 'patrol' ? P.state.route_i : null,
    showRays: $('rays').checked, showTrail: $('trail').checked,
  };
}
export const drawers = [];

// ---------- 3D ----------
const view3d = createNavView3d($('view3d'));
$('bar3d').innerHTML = `<label class="chk"><input type="checkbox" id="follow" checked><i class="fa-solid fa-crosshairs"></i>follow R2</label>
  <label class="chk"><input type="checkbox" id="room3d" checked><i class="fa-solid fa-border-all"></i>show the room</label>
  <label class="chk"><i class="fa-solid fa-robot"></i><select id="model3d" aria-label="3D model">${Object.entries(MODELS)
    .map(([k, m]) => `<option value="${k}">${m.label}</option>`).join('')}</select></label>
  <span class="hint" style="padding:0">drag to orbit · wheel to zoom</span>`;
$('follow').onchange = () => { view3d.opts.follow = $('follow').checked; view3d.redraw(); };
$('room3d').onchange = () => { view3d.opts.room = $('room3d').checked; view3d.redraw(); };
let model = 'simple';
try { model = localStorage.getItem('r2web.model') || 'simple'; } catch { /* private window */ }
$('model3d').value = MODELS[model] ? model : 'simple';
const pickModel = () => {
  try { localStorage.setItem('r2web.model', $('model3d').value); } catch { /* private window */ }
  view3d.setModel($('model3d').value).catch((e) => addLine(`· could not load the model: ${e}`, 'info'));
};
$('model3d').onchange = pickModel;
pickModel();
drawers.push((st) => view3d.draw(st));
(function frame() {
  if (!document.hidden) {
    const st = frameState();
    map.draw(st);
    for (const d of drawers) d(st);
  }
  requestAnimationFrame(frame);
})();
