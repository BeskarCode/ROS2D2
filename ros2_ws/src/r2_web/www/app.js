// ROS2D2 web console: talks to ROS through rosbridge's JSON protocol over a WebSocket.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { buildR2 } from './r2model.js';

const params = new URLSearchParams(location.search);
const CAM = params.get('cam') || 'front';
const WS_URL = params.get('ws') || `ws://${location.hostname || 'localhost'}:9090`;
const MAX_SPEED = 80;          // ShadowMDLite clamps |DM:| to DOME_TRACKER_MAX_SPEED
const TRACKER = '/dome_tracker';
const DETECTOR = `/cameras/${CAM}/face_detector`;

const $ = (id) => document.getElementById(id);
$('camname').textContent = `/cameras/${CAM}`;

// ---------- node parameters, changed live through rosbridge ----------
// rcl_interfaces/msg/ParameterValue types: 1 bool, 3 double
const PTYPE = { bool: [1, 'bool_value'], double: [3, 'double_value'] };
let hfov = 60;

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
      return [n, v.type === 1 ? v.bool_value : v.type === 2 ? v.integer_value : v.double_value];
    }))));
}

function readParams() {
  getParams(TRACKER, ['deg_per_s_at_80', 'simulate', 'camera_hfov_deg'], (v) => {
    $('rate').value = v.deg_per_s_at_80;
    $('simulate').checked = v.simulate;
    hfov = v.camera_hfov_deg;
    showSim(v.simulate);
  });
  getParams(DETECTOR, ['pixelate'], (v) => { $('pixelate').checked = v.pixelate; });
}

function showSim(on) { $('simpill').hidden = !on; $('aim').style.display = on ? 'block' : 'none'; }

$('rate').addEventListener('change', () => {
  const v = Number($('rate').value);
  if (v > 0) setParam(TRACKER, 'deg_per_s_at_80', 'double', v);
});
$('simulate').addEventListener('change', () => {
  setParam(TRACKER, 'simulate', 'bool', $('simulate').checked);
  showSim($('simulate').checked);
});
$('pixelate').addEventListener('change', () => setParam(DETECTOR, 'pixelate', 'bool', $('pixelate').checked));

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
    subscribe(`/cameras/${CAM}/faces/image/compressed`, 'sensor_msgs/msg/CompressedImage', onImage, 50);
    subscribe(`/cameras/${CAM}/faces`, 'vision_msgs/msg/Detection2DArray', onFaces);
    subscribe(`/cameras/${CAM}/camera_info`, 'sensor_msgs/msg/CameraInfo', onInfo, 2000);
    subscribe('/dome/speed_cmd', 'std_msgs/msg/Int16', onSpeed);
    subscribe('/dome_tracker/status', 'std_msgs/msg/String', onStatus);
    subscribe('/r2/track_mode', 'std_msgs/msg/Bool', (m) => setTrack(m.data));
    // latch: the tracker's subscription is transient-local, a volatile publisher would not match
    send({ op: 'advertise', topic: '/r2/track_mode', type: 'std_msgs/msg/Bool', latch: true });
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

function setPill(id, text, cls) { const el = $(id); el.textContent = text; el.className = 'pill ' + cls; }

// ---------- camera and faces ----------
let width = null;
let frames = 0;
function onImage(m) {
  $('video').src = `data:image/${m.format.includes('png') ? 'png' : 'jpeg'};base64,${m.data}`;
  frames++;
}
setInterval(() => { $('fps').textContent = `${frames} fps`; frames = 0; }, 1000);

function onInfo(m) { width = m.width; }

function onFaces(m) {
  const d = m.detections;
  $('faces').textContent = d.length;
  if (!d.length) { $('score').textContent = '–'; $('facex').textContent = '–'; return; }
  const best = d[0];        // the detector puts the face R2 follows first
  $('score').textContent = best.results.length ? best.results[0].hypothesis.score.toFixed(2) : '–';
  if (width) {
    const err = (best.bbox.center.position.x - width / 2) / (width / 2);   // -1 left .. +1 right
    $('facex').textContent = (err > 0 ? 'right ' : 'left ') + Math.round(Math.abs(err) * 100) + '%';
  }
}

function onStatus(m) {
  const cls = { tracking: 'ok', 'no face': 'warn', 'track off': '', disabled: 'bad' }[m.data] ?? '';
  setPill('status', 'tracker: ' + m.data, cls);
}

function setTrack(on) {
  trackOn = on;
  $('track').textContent = 'Track: ' + (on ? 'ON' : 'off');
  $('track').classList.toggle('on', on);
}
$('track').addEventListener('click', () => {
  const next = !trackOn;
  send({ op: 'publish', topic: '/r2/track_mode', msg: { data: next } });
  setTrack(next);
});

// ---------- dome speed and angle (estimated by the tracker node) ----------
let angleDeg = 0;
function onSpeed(m) {
  const speed = m.data;
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

const { root, dome } = buildR2();
scene.add(root);

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
controls.update();

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * renderer.getPixelRatio())) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
}

let shown = 0;
function frame() {
  // + = right. Ease towards the latest estimate: it arrives ~15 times a second
  let diff = ((angleDeg - shown + 540) % 360) - 180;
  shown += diff * 0.35;
  dome.rotation.y = -THREE.MathUtils.degToRad(shown);
  $('angle').textContent = `${angleDeg >= 0 ? '+' : ''}${angleDeg.toFixed(0)}°`;
  // Where the simulated dome looks, on the (fixed) camera picture
  $('aim').style.left = Math.max(0, Math.min(100, 50 + angleDeg / (hfov / 2) * 50)) + '%';

  resize();
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
connect();
