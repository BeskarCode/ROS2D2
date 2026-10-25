// ROS2D2 web console: talks to ROS through rosbridge's JSON protocol over a WebSocket.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { RoomEnvironment } from './vendor/environments/RoomEnvironment.js';
import { MODELS, loadModel } from './models.js';

const params = new URLSearchParams(location.search);
const WS_URL = params.get('ws') || `ws://${location.hostname || 'localhost'}:9090`;
// Pictures come from web_video_server as MJPEG (a plain <img>); rosbridge only carries data
const VIDEO = (topic) => `http://${location.hostname || 'localhost'}:${params.get('video') || 8081}` +
  `/stream?topic=${topic}&type=ros_compressed&qos_profile=sensor_data`;
const MAX_SPEED = 80;          // ShadowMDLite clamps |DM:| to DOME_TRACKER_MAX_SPEED
const TRACKER = '/dome_tracker';

const $ = (id) => document.getElementById(id);

// ---------- node parameters, changed live through rosbridge ----------
// rcl_interfaces/msg/ParameterValue types: 1 bool, 3 double
const PTYPE = { bool: [1, 'bool_value'], double: [3, 'double_value'] };
// The cameras the tracker follows, left to right: { name, yaw, hfov, width, frames, latest, tile }
let cams = [];
const detector = (c) => `/cameras/${c.name}/face_detector`;

function setParam(node, name, kind, value) {
  const [type, field] = PTYPE[kind];
  callService(`${node}/set_parameters`, 'rcl_interfaces/srv/SetParameters',
    { parameters: [{ name, value: { type, [field]: value } }] },
    (r) => { const res = r.results && r.results[0]; if (res && !res.successful) console.warn(name, res.reason); });
}

function getParams(node, names, fn) {
  callService(`${node}/get_parameters`, 'rcl_interfaces/srv/GetParameters', { names },
    (r) => fn(Object.fromEntries(names.map((n, i) => {
      const v = r.values[i];
      const value = { 1: v.bool_value, 2: v.integer_value, 3: v.double_value, 4: v.string_value,
                      9: v.string_array_value }[v.type];
      return [n, value];
    }))));
}

function readParams() {
  getParams(TRACKER, ['deg_per_s_at_80', 'simulate', 'cameras'], (v) => {
    $('rate').value = v.deg_per_s_at_80;
    $('simulate').checked = v.simulate;
    showSim(v.simulate);
    const names = v.cameras || [];
    getParams(TRACKER, names.flatMap((n) => [`${n}.yaw_deg`, `${n}.hfov_deg`]), (g) => {
      setCameras(names.map((n) => ({ name: n, yaw: g[`${n}.yaw_deg`], hfov: g[`${n}.hfov_deg`] })));
    });
  });
}

let simOn = false;
function showSim(on) { simOn = on; $('simpill').hidden = !on; }

$('rate').addEventListener('change', () => {
  const v = Number($('rate').value);
  if (v > 0) setParam(TRACKER, 'deg_per_s_at_80', 'double', v);
});
$('simulate').addEventListener('change', () => {
  setParam(TRACKER, 'simulate', 'bool', $('simulate').checked);
  showSim($('simulate').checked);
});
$('pixelate').addEventListener('change', () => {
  savePref('pixelate', String($('pixelate').checked));
  for (const c of cams) setParam(detector(c), 'pixelate', 'bool', $('pixelate').checked);
});
// Like the monitors in Windows: the number shows big on each picture for a moment
$('identify').addEventListener('click', () => {
  for (const c of cams) c.tile.classList.add('identify');
  setTimeout(() => { for (const c of cams) c.tile.classList.remove('identify'); }, 3000);
});

// ---------- rosbridge ----------
let ws = null;
const handlers = {};
const pending = {};
let callId = 0;
let trackOn = null;

function connect() {
  ws = new WebSocket(WS_URL);
  setPill('conn', 'connecting…', '');
  ws.onopen = () => {
    setPill('conn', 'rosbridge ok', 'ok');
    subscribe('/dome/speed_cmd', 'std_msgs/msg/Int16', onSpeed);
    subscribe('/dome_tracker/status', 'std_msgs/msg/String', onStatus);
    subscribe('/r2/track_mode', 'std_msgs/msg/Bool', (m) => setTrack(m.data));
    // latch: the tracker's subscription is transient-local, a volatile publisher would not match
    send({ op: 'advertise', topic: '/r2/track_mode', type: 'std_msgs/msg/Bool', latch: true });
    subscribe('/mega/tx', 'std_msgs/msg/String', onTx);
    subscribe('/mega/log', 'std_msgs/msg/String', (m) => { if ($('megarx').checked) addLine(m.data, 'rx'); });
    subscribe('/mega/connected', 'std_msgs/msg/Bool', onConnected);
    subscribe('/dome/angle_estimate', 'std_msgs/msg/Float32', (m) => { angleDeg = m.data; });
    send({ op: 'advertise', topic: '/dome/angle_reset', type: 'std_msgs/msg/Empty' });
    readParams();
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.op === 'publish' && handlers[msg.topic]) handlers[msg.topic](msg.msg);
    if (msg.op === 'service_response' && pending[msg.id]) {
      if (msg.result) pending[msg.id](msg.values);
      else console.warn('service failed', msg.id, msg.values);
      delete pending[msg.id];
    }
  };
  ws.onclose = () => { setPill('conn', 'no rosbridge — retrying', 'bad'); setTimeout(connect, 2000); };
  ws.onerror = () => ws.close();
}

function send(obj) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); }

function callService(service, type, args, fn) {
  const id = 'call' + (++callId);
  pending[id] = fn;
  send({ op: 'call_service', id, service, type, args });
}

function subscribe(topic, type, fn, throttle = 0) {
  handlers[topic] = fn;
  send({ op: 'subscribe', topic, type, throttle_rate: throttle, queue_length: 1 });
}

const PILL_ICONS = { conn: 'fa-plug', status: 'fa-crosshairs' };
function setPill(id, text, cls) {
  const el = $(id);
  el.innerHTML = PILL_ICONS[id] ? `<i class="fa-solid ${PILL_ICONS[id]}"></i>` : '';
  el.append(text);
  el.className = 'pill ' + cls;
}

// ---------- camera and faces ----------
// One tile per camera, left to right by where it points, numbered like monitors
function setCameras(list) {
  for (const c of cams) {
    for (const t of ['faces', 'camera_info']) send({ op: 'unsubscribe', topic: `/cameras/${c.name}/${t}` });
    c.tile.querySelector('img').src = '';      // closes the MJPEG connection
  }
  cams = list.sort((a, b) => a.yaw - b.yaw).map((c) => ({ ...c, width: null, frames: 0, latest: null }));
  const box = $('cams');
  box.textContent = '';
  if (!cams.length) box.innerHTML = '<div class="camtile"><div class="nocam">no camera — see ⚙ Camera setup</div></div>';
  cams.forEach((c, i) => {
    c.tile = document.createElement('div');
    c.tile.className = 'camtile';
    c.tile.title = `${c.name}: ${c.yaw >= 0 ? '+' : ''}${c.yaw}°, ${c.hfov}° wide`;
    c.tile.innerHTML = '<img alt=""><div class="offline">OFFLINE</div><div class="num"></div><div class="aim"><span>simulated dome</span></div>';
    c.tile.querySelector('.num').textContent = i + 1;
    c.tile.querySelector('img').alt = `camera ${i + 1} with detected faces`;
    c.tile.querySelector('img').src = VIDEO(`/cameras/${c.name}/faces/image`);
    box.append(c.tile);
    const base = `/cameras/${c.name}`;
    // One faces message per picture the detector handled: it counts the fps and tells
    // when a camera stops (unplugged)
    subscribe(`${base}/faces`, 'vision_msgs/msg/Detection2DArray', (m) => {
      c.frames++;
      c.lastFrame = performance.now();
      onFaces(c, m);
    });
    subscribe(`${base}/camera_info`, 'sensor_msgs/msg/CameraInfo', (m) => { c.width = m.width; }, 2000);
  });
  // Pixelate is remembered in this browser and put back after ROS2D2 restarts
  if (cams.length) getParams(detector(cams[0]), ['pixelate'], (v) => {
    const pref = loadPref('pixelate', null);
    const want = pref === null ? v.pixelate : pref === 'true';
    $('pixelate').checked = want;
    if (want !== v.pixelate) for (const c of cams) setParam(detector(c), 'pixelate', 'bool', want);
  });
  addFans();
}

// What each camera sees, drawn on the 3D dome as see-through fans that turn with it
const FAN_COLOURS = [0x3b82f6, 0xf0b429, 0x3fb950, 0xf85149, 0xa371f7, 0x39c5cf];
function addFans() {
  if (!current) return;
  const old = current.dome.getObjectByName('fans');
  if (old) current.dome.remove(old);
  const g = new THREE.Group();
  g.name = 'fans';
  g.visible = $('showfov').checked;
  cams.forEach((c, i) => {
    // CircleGeometry draws in XY; laid flat it maps angle phi to (cos phi, 0, -sin phi).
    // Front is +Z and + yaw is to the right (-X), so a yaw of t sits at phi = -90 deg - t.
    const h = THREE.MathUtils.degToRad(Math.min(c.hfov, 359));
    const mid = -Math.PI / 2 - THREE.MathUtils.degToRad(c.yaw);
    const fan = new THREE.Mesh(new THREE.CircleGeometry(3.2, 48, mid - h / 2, h),
      new THREE.MeshBasicMaterial({ color: FAN_COLOURS[i % FAN_COLOURS.length], transparent: true, opacity: 0.18,
        side: THREE.DoubleSide, depthWrite: false }));
    fan.rotation.x = -Math.PI / 2;
    fan.position.y = 0.25;
    g.add(fan);
  });
  current.dome.add(g);
}
$('showfov').addEventListener('change', () => {
  const f = current && current.dome.getObjectByName('fans');
  if (f) f.visible = $('showfov').checked;
});
setInterval(() => {
  $('fps').textContent = cams.length ? cams.map((c) => c.frames).join(' · ') + ' fps' : '– fps';
  // No picture for 2 s: unplugged or stuck (the camera node keeps trying to reopen it)
  for (const c of cams) {
    c.frames = 0;
    c.tile.classList.toggle('off', !c.lastFrame || performance.now() - c.lastFrame > 2000);
  }
}, 1000);

function onFaces(c, m) {
  const d = m.detections;
  c.latest = d.length && c.width ? {
    t: performance.now(),
    count: d.length,
    score: d[0].results.length ? d[0].results[0].hypothesis.score : null,
    size: d[0].bbox.size_x / c.width,
    // degrees from the dome's front, + = right
    bearing: c.yaw + (d[0].bbox.center.position.x - c.width / 2) / (c.width / 2) * c.hfov / 2,
  } : null;
  // All cameras together: the biggest face is the one R2 follows
  const now = performance.now();
  const fresh = cams.map((k) => k.latest).filter((l) => l && now - l.t < 500);
  $('faces').textContent = fresh.reduce((n, l) => n + l.count, 0);
  if (!fresh.length) { $('score').textContent = '–'; $('facex').textContent = '–'; return; }
  const best = fresh.reduce((a, b) => (b.size > a.size ? b : a));
  $('score').textContent = best.score == null ? '–' : best.score.toFixed(2);
  $('facex').textContent = (best.bearing >= 0 ? 'right ' : 'left ') + Math.abs(best.bearing).toFixed(0) + '°';
}

function onStatus(m) {
  const cls = { tracking: 'ok', 'no face': 'warn', 'track off': '', disabled: 'bad' }[m.data] ?? '';
  setPill('status', 'tracker: ' + m.data, cls);
}

function setTrack(on) {
  trackOn = on;
  $('track').innerHTML = '<i class="fa-solid fa-crosshairs"></i>Track: ' + (on ? 'ON' : 'off');
  $('track').classList.toggle('on', on);
}
$('track').addEventListener('click', () => {
  if (megaConnected) {
    // With a Mega only the controller turns tracking on (PS + L2 on the dome Nav); we can only stop it
    if (trackOn) callService('/r2/track_mode/disable', 'std_srvs/srv/Trigger', {}, () => {});
    return;
  }
  const next = !trackOn;
  send({ op: 'publish', topic: '/r2/track_mode', msg: { data: next } });
  setTrack(next);
});

// ---------- Mega: what is sent and what it answers ----------
let megaConnected = null;     // null = no bridge running (simulation)
let paused = false;
const MAX_LINES = 300;

function onConnected(m) {
  megaConnected = m.data;
  $('megastate').textContent = m.data ? 'connected' : 'not connected';
  $('track').title = m.data ? 'Turn on with PS + L2 on the dome Nav; here you can only stop it' : '';
}

function onTx(m) {
  if (m.data.startsWith('(not sent) ')) addLine(m.data.slice(11), 'unsent');
  else addLine(m.data, 'tx');
}

function addLine(text, cls) {
  if (paused) return;
  const log = $('megalog');
  const first = log.firstElementChild;
  // 15 identical ROS:DOME: lines a second: group repeats on one line with a counter
  if (first && first.dataset.text === text && first.dataset.cls === cls) {
    const n = Number(first.dataset.n) + 1;
    first.dataset.n = n;
    first.querySelector('.n').textContent = '×' + n;
    first.querySelector('.t').textContent = clock();
    return;
  }
  const div = document.createElement('div');
  div.className = cls;
  div.dataset.text = text; div.dataset.cls = cls; div.dataset.n = 1;
  div.innerHTML = '<span class="t"></span><span class="x"></span><span class="n"></span>';
  div.querySelector('.t').textContent = clock();
  div.querySelector('.x').textContent = text;
  log.prepend(div);
  while (log.childElementCount > MAX_LINES) log.lastElementChild.remove();
}

function clock() {
  const d = new Date();
  return d.toLocaleTimeString('en-GB') + '.' + String(d.getMilliseconds()).padStart(3, '0').slice(0, 1);
}

$('megapause').addEventListener('click', () => {
  paused = !paused;
  $('megapause').innerHTML = paused ? '<i class="fa-solid fa-play"></i>Resume' : '<i class="fa-solid fa-pause"></i>Pause';
  $('megapause').classList.toggle('on', paused);
});
$('megaclear').addEventListener('click', () => { $('megalog').textContent = ''; });

// ---------- dome speed and angle (estimated by the tracker node) ----------
let angleDeg = 0;
let simStopped = true;
function onSpeed(m) {
  const speed = m.data;
  // No bridge: show what it would send (protocol.dome_tick: repeat while turning, one stop, then quiet)
  if (megaConnected === null && (speed !== 0 || !simStopped)) {
    addLine(`ROS:DOME:${Math.max(-MAX_SPEED, Math.min(MAX_SPEED, speed))}`, 'sim');
  }
  simStopped = speed === 0;
  const pct = Math.max(-1, Math.min(1, speed / MAX_SPEED)) * 50;
  const fill = $('speedfill');
  fill.style.left = (pct < 0 ? 50 + pct : 50) + '%';
  fill.style.width = Math.abs(pct) + '%';
  $('speed').textContent = 'speed ' + speed;
}
$('zero').addEventListener('click', () => send({ op: 'publish', topic: '/dome/angle_reset', msg: {} }));

// ---------- 3D view ----------
const canvas = $('view3d');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
camera.position.set(4.2, 4.6, 6.4);

scene.add(new THREE.HemisphereLight(0xdde8ff, 0x202530, 1.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(4, 8, 6);
scene.add(sun);

// Chrome and metal parts need something to reflect
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;

let current = null;     // { root, dome } of the model on screen
function loadPref(key, fallback) { try { return localStorage.getItem('r2web.' + key) || fallback; } catch { return fallback; } }
function savePref(key, v) { try { localStorage.setItem('r2web.' + key, v); } catch { /* private window */ } }

for (const [key, m] of Object.entries(MODELS)) {
  const o = document.createElement('option');
  o.value = key; o.textContent = m.label;
  $('model').append(o);
}
async function showModel(key) {
  if (!MODELS[key]) key = 'simple';
  $('model').value = key;
  $('loading').style.display = 'flex';
  // ?split=0.76&pitch=-12&roll=3 try another dome cut while tuning a new model
  const tune = {};
  for (const [q, k] of [['split', 'domeFrom'], ['pitch', 'pitch'], ['roll', 'roll']]) {
    if (params.has(q)) tune[k] = Number(params.get(q));
  }
  try {
    const next = await loadModel(key, tune);
    if (current) scene.remove(current.root);
    current = next;
    scene.add(current.root);
    $('credit').innerHTML = MODELS[key].credit ? 'Model: ' + MODELS[key].credit : '';
    addFans();
    savePref('model', key);
  } catch (e) {
    console.error('model', key, e);
    $('credit').textContent = 'Could not load ' + MODELS[key].label;
  }
  $('loading').style.display = 'none';
}
$('model').addEventListener('change', async () => { await showModel($('model').value); if (params.has('tune')) { fillTune(); decorate(); } });

// ?tune=1: - / + buttons to place the dome cut by eye (on the blue line at the bottom of the dome)
const CUT = ['split', 'pitch', 'roll'];
const tv = { split: 0.75, pitch: 0, roll: 0, turn: 90 };   // what the panel shows
let tuneTurn = null;
let history = [];          // earlier cut values, for Undo / Ctrl+Z
let recutTimer = null;

const cutValues = () => Object.fromEntries(CUT.map((k) => [k, tv[k]]));
function showTune() {
  for (const row of document.querySelectorAll('.trow')) {
    $('v-' + row.dataset.k).textContent = tv[row.dataset.k].toFixed(Number(row.dataset.dec));
  }
  $('t-out').textContent = `domeFrom: ${tv.split.toFixed(3)}, pitch: ${tv.pitch.toFixed(1)}, roll: ${tv.roll.toFixed(1)}`;
  tuneTurn = tv.turn;
}
function setCut(vals) { Object.assign(tv, vals); showTune(); }
function modelCut() {
  const m = MODELS[$('model').value];
  return { split: m.domeFrom, pitch: m.pitch || 0, roll: m.roll || 0 };
}
function fillTune() {
  if (!MODELS[$('model').value].url) return;
  history = [];
  setCut(modelCut());
}
function undo() {
  if (!history.length) return;
  setCut(history.pop());
  recut();
}
function step(k, dir, dec) {
  if (CUT.includes(k)) history.push(cutValues());
  tv[k] = Number((tv[k] + dir).toFixed(dec + 1));
  if (k === 'turn') tv.turn = ((tv.turn + 540) % 360) - 180;
  showTune();
  if (CUT.includes(k)) { clearTimeout(recutTimer); recutTimer = setTimeout(recut, 80); }
}
if (params.has('tune')) {
  document.body.classList.add('tune');
  $('tune').style.display = 'flex';
  for (const row of document.querySelectorAll('.trow')) {
    const [minus, plus] = row.querySelectorAll('button');
    const s = Number(row.dataset.step), dec = Number(row.dataset.dec);
    for (const [btn, dir] of [[minus, -s], [plus, s]]) {
      // One step per click; held down, it keeps stepping
      let hold = null;
      const stop = () => { clearTimeout(hold); clearInterval(hold); hold = null; };
      btn.addEventListener('pointerdown', () => {
        step(row.dataset.k, dir, dec);
        hold = setTimeout(() => { hold = setInterval(() => step(row.dataset.k, dir, dec), 90); }, 400);
      });
      for (const ev of ['pointerup', 'pointerleave', 'pointercancel']) btn.addEventListener(ev, stop);
    }
  }
  $('t-undo').addEventListener('click', undo);
  $('t-reset').addEventListener('click', () => { history.push(cutValues()); setCut(modelCut()); recut(); });
  addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); undo(); }
  });
  $('t-plane').addEventListener('change', () => {
    const m = current && current.root.getObjectByName('cutMarker');
    if (m) m.visible = $('t-plane').checked;
  });
  $('t-hide').addEventListener('change', () => { if (current) current.dome.visible = !$('t-hide').checked; });
  showTune();
}
// The cut drawn on the model: a see-through magenta disc on the plane, with a bright rim
function cutMarker(cut) {
  const g = new THREE.Group();
  g.position.copy(cut.centre);
  g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), cut.normal);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(1.7, 64),
    new THREE.MeshBasicMaterial({ color: 0xff2bd6, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }));
  disc.rotation.x = -Math.PI / 2;
  const rim = new THREE.Mesh(new THREE.TorusGeometry(1.7, 0.02, 8, 128),
    new THREE.MeshBasicMaterial({ color: 0xff2bd6 }));
  rim.rotation.x = -Math.PI / 2;
  g.add(disc, rim);
  g.name = 'cutMarker';
  return g;
}
function decorate() {
  if (!params.has('tune') || !current || !current.cut) return;
  const marker = cutMarker(current.cut);
  marker.visible = $('t-plane').checked;
  current.root.add(marker);
  current.dome.visible = !$('t-hide').checked;
}

async function recut() {
  const key = $('model').value;
  const next = await loadModel(key, {
    domeFrom: tv.split, pitch: tv.pitch, roll: tv.roll,
  });
  if (current) scene.remove(current.root);
  current = next;
  scene.add(current.root);
  decorate();
  addFans();
}
showModel(params.get('model') || loadPref('model', 'vladimirov')).then(() => { if (params.has('tune')) { fillTune(); decorate(); } });

const floor = new THREE.Mesh(new THREE.CircleGeometry(3, 64),
  new THREE.MeshStandardMaterial({ color: 0x1b2230, roughness: 1 }));
floor.rotation.x = -Math.PI / 2;
scene.add(floor);
// Arrow on the floor: where the body faces (the dome angle is measured from it)
const arrow = new THREE.Mesh(new THREE.ConeGeometry(0.18, 0.4, 3),
  new THREE.MeshBasicMaterial({ color: 0x3b82f6 }));
arrow.rotation.x = Math.PI / 2;
arrow.position.set(0, 0.01, 2.3);
scene.add(arrow);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 2.2, 0);
controls.enablePan = false;
controls.minDistance = 4;
controls.maxDistance = 16;
// Calibration: look closely at the head
if (params.has('tune')) {
  camera.position.set(2.4, 3.9, 3.6);
  controls.target.set(0, 2.9, 0);
  controls.minDistance = 1.5;
}
controls.update();

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * renderer.getPixelRatio())) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
}

// The picture is letterboxed inside its box (object-fit: contain): put the line on the picture itself
function placeAim() {
  for (const c of cams) {
    const aim = c.tile.querySelector('.aim');
    const frac = 0.5 + (angleDeg - c.yaw) / c.hfov;      // where the simulated dome looks, in this picture
    if (!simOn || frac < 0 || frac > 1) { aim.style.display = 'none'; continue; }
    const img = c.tile.querySelector('img');
    const bw = img.clientWidth, bh = img.clientHeight;
    const ratio = img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 4 / 3;
    const w = Math.min(bw, bh * ratio);
    aim.style.display = 'block';
    aim.style.left = ((bw - w) / 2 + frac * w) + 'px';
  }
}

let shown = 0;
function frame() {
  // + = right. Ease towards the latest estimate: it arrives ~15 times a second
  let diff = ((angleDeg - shown + 540) % 360) - 180;
  shown += diff * 0.35;
  // ?turn=90 holds the dome at that angle, to check where a new model is cut
  const turn = tuneTurn ?? (params.has('turn') ? Number(params.get('turn')) : null);
  if (current) current.dome.rotation.y = -THREE.MathUtils.degToRad(turn ?? shown);
  $('angle').textContent = `${angleDeg >= 0 ? '+' : ''}${angleDeg.toFixed(0)}°`;
  // Where the simulated dome looks, on the (fixed) camera picture
  placeAim();

  resize();
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
connect();
