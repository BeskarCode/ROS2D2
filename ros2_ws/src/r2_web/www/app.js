// ROS2D2 web console: talks to ROS through rosbridge's JSON protocol over a WebSocket.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { buildR2 } from './r2model.js';

const params = new URLSearchParams(location.search);
const CAM = params.get('cam') || 'front';
const WS_URL = params.get('ws') || `ws://${location.hostname || 'localhost'}:9090`;
const MAX_SPEED = 80;          // ShadowMDLite clamps |DM:| to DOME_TRACKER_MAX_SPEED
const STALE_MS = 300;          // the Mega stops the dome after 300 ms without a speed

const $ = (id) => document.getElementById(id);
$('camname').textContent = `/cameras/${CAM}`;

// ---------- settings kept in this browser ----------
function load(key, fallback) {
  try { const v = localStorage.getItem('r2web.' + key); return v === null ? fallback : JSON.parse(v); }
  catch { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem('r2web.' + key, JSON.stringify(value)); } catch { /* private window */ }
}
const settings = { rate: load('rate', 90), invert: load('invert', false) };
$('rate').value = settings.rate;
$('invert').checked = settings.invert;
$('rate').addEventListener('change', () => { settings.rate = Number($('rate').value) || 90; save('rate', settings.rate); });
$('invert').addEventListener('change', () => { settings.invert = $('invert').checked; save('invert', settings.invert); });

// ---------- rosbridge ----------
let ws = null;
const handlers = {};
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
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.op === 'publish' && handlers[msg.topic]) handlers[msg.topic](msg.msg);
  };
  ws.onclose = () => { setPill('conn', 'no rosbridge — retrying', 'bad'); setTimeout(connect, 2000); };
  ws.onerror = () => ws.close();
}

function send(obj) { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj)); }

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

// ---------- dome speed -> estimated angle ----------
let speed = 0;
let speedAt = 0;
let angleDeg = 0;
function onSpeed(m) {
  speed = m.data;
  speedAt = performance.now();
  const pct = Math.max(-1, Math.min(1, speed / MAX_SPEED)) * 50;
  const fill = $('speedfill');
  fill.style.left = (pct < 0 ? 50 + pct : 50) + '%';
  fill.style.width = Math.abs(pct) + '%';
  $('speed').textContent = 'speed ' + speed;
}
$('zero').addEventListener('click', () => { angleDeg = 0; });

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

let last = performance.now();
function frame(now) {
  const dt = (now - last) / 1000;
  last = now;
  const live = now - speedAt < STALE_MS ? speed : 0;
  // Positive DM: turns the dome clockwise seen from above (right); "invert" if yours goes the other way
  const dir = settings.invert ? -1 : 1;
  angleDeg += dir * (live / MAX_SPEED) * settings.rate * dt;
  angleDeg = ((angleDeg + 180) % 360 + 360) % 360 - 180;
  dome.rotation.y = -THREE.MathUtils.degToRad(angleDeg);
  $('angle').textContent = `${angleDeg >= 0 ? '+' : ''}${angleDeg.toFixed(0)}°`;

  resize();
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
connect();
