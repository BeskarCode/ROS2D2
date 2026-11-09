// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// 3D view of the Navigation page: the droid (either model) moving in the odom frame, the room
// and its obstacles (in simulation), the lidar's point cloud at its height, each distance
// sensor as a cone as long as what it reads (red inside its stop distance), the safety ring,
// the goal and the heading the navigator chose. Draws only when something changed.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { loadModelMetres } from './models.js';
import { textSprite } from './label3d.js';
import { freeText } from './sensormath.js';

const COL = { rplidar_c1: '#39c5cf', vl53l0x: '#a371f7', hcsr04: '#f0b429' };
const rad = (d) => d * Math.PI / 180;
// odom/base_link (x forward, y left, z up) -> three.js (X left, Y up, Z forward)
const V = (x, y, z) => new THREE.Vector3(y, z, x);

export function createNavView3d(container) {
  container.textContent = '';
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(devicePixelRatio);
  renderer.localClippingEnabled = true;
  container.append(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#0b0f14');
  const cam = new THREE.PerspectiveCamera(45, 4 / 3, 0.01, 100);
  cam.position.set(-1.5, 3.0, -4.5);
  const orbit = new OrbitControls(cam, renderer.domElement);
  orbit.target.set(-1.2, 0.3, -2.2);
  orbit.update();
  scene.add(new THREE.HemisphereLight('#cfe3ff', '#202833', 2.2));
  const sun = new THREE.DirectionalLight('#ffffff', 1.3);
  sun.position.set(2, 5, 3);
  scene.add(sun);
  scene.add(new THREE.GridHelper(10, 20, '#2a313c', '#1a2029'));
  const floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

  const room = new THREE.Group(); scene.add(room);
  const droid = new THREE.Group(); scene.add(droid);       // at the pose; children in base_link
  const mounted = new THREE.Group(); droid.add(mounted);   // sensor cones, rebuilt with the readings
  const world = new THREE.Group(); scene.add(world);       // point cloud, goal, arrow (odom)
  let model = null, dirty = true;
  let keys = { world: '', readings: null, scan: null, goal: '', model: '', radius: -1, free: null, arrow: null };
  const opts = { follow: true, room: true };
  orbit.addEventListener('change', () => { dirty = true; });

  function dispose(g) { g.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose?.(); }); g.clear(); }

  function buildRoom(w) {
    dispose(room);
    if (!w) return;
    const wall = new THREE.MeshStandardMaterial({ color: '#30363d', transparent: true, opacity: 0.35 });
    const [x0, x1, y0, y1] = w.room;
    for (const [ax, ay, bx, by] of [[x0, y0, x1, y0], [x1, y0, x1, y1], [x1, y1, x0, y1], [x0, y1, x0, y0]]) {
      const len = Math.hypot(bx - ax, by - ay);
      const m = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.5, len), wall);
      m.position.copy(V((ax + bx) / 2, (ay + by) / 2, 0.25));
      m.rotation.y = Math.atan2(by - ay, bx - ax);
      room.add(m);
    }
    for (const o of w.obstacles) {
      const mat = new THREE.MeshStandardMaterial({ color: o.kind === 'low' ? '#f85149' : o.kind === 'post' && o.r > 0.1 ? '#8b949e' : '#6e7681' });
      const m = o.kind === 'post' ? new THREE.Mesh(new THREE.CylinderGeometry(o.r, o.r, o.height, 20), mat)
        : new THREE.Mesh(new THREE.BoxGeometry(o.h, o.height, o.w), mat);
      m.position.copy(V(o.x, o.y, o.height / 2));
      room.add(m);
    }
  }

  function buildCones(sensors, readings, stops) {
    dispose(mounted);
    for (const [name, s] of Object.entries(sensors)) {
      if (s.type === 'rplidar_c1') continue;
      const d = readings[name], stop = stops[name] || 0;
      const L = d ?? Math.min(s.range_max, 1.5), r = Math.tan(rad(s.fov_deg / 2)) * L;
      const geo = new THREE.ConeGeometry(r, L, 24, 1, true);
      geo.translate(0, -L / 2, 0);
      const hot = d != null && stop && d < stop;
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: hot ? '#f85149' : COL[s.type], transparent: true,
        opacity: d != null ? 0.3 : 0.08, side: THREE.DoubleSide, depthWrite: false, clippingPlanes: [floor] }));
      const p = rad(s.pitch_deg), y = rad(s.yaw_deg);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), V(Math.cos(p) * Math.cos(y), Math.cos(p) * Math.sin(y), -Math.sin(p)).normalize());
      m.position.copy(V(s.x, s.y, s.z));
      mounted.add(m);
    }
  }

  function buildWorld(st, lidarZ) {
    dispose(world);
    if (st.scan.length) {
      const pos = new Float32Array(st.scan.flatMap(([x, y]) => [y, lidarZ, x]));
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      world.add(new THREE.Points(g, new THREE.PointsMaterial({ color: '#39c5cf', size: 0.05 })));
    }
    if (st.goal) {
      const f = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.6, 8), new THREE.MeshBasicMaterial({ color: '#3fb950' }));
      f.position.copy(V(st.goal[0], st.goal[1], 0.3));
      world.add(f);
    }
  }

  let arrow = null, ring = null, freeRing = null;
  function draw(st) {
    if (!st.pose) return;
    const lidar = Object.values(st.sensors).find((s) => s.type === 'rplidar_c1');
    const wk = st.world ? JSON.stringify([st.world.room, st.world.obstacles]) : '';
    if (wk !== keys.world || opts.room !== keys.room) { keys.world = wk; keys.room = opts.room; buildRoom(opts.room ? st.world : null); dirty = true; }
    if (st.readings !== keys.readings) { keys.readings = st.readings; buildCones(st.sensors, st.readings, st.stops); dirty = true; }
    const gk = JSON.stringify(st.goal);
    if (st.scan !== keys.scan || gk !== keys.goal) { keys.scan = st.scan; keys.goal = gk; buildWorld(st, lidar ? lidar.z : 0.1); dirty = true; }
    // the droid at its (interpolated) pose
    const { x, y, th } = st.pose;
    if (droid.position.x !== y || droid.position.z !== x || droid.rotation.y !== th) {
      droid.position.copy(V(x, y, 0));
      droid.rotation.y = th;
      dirty = true;
      if (opts.follow) {
        const d = V(x, y, 0.3).sub(orbit.target);
        orbit.target.add(d); cam.position.add(d); orbit.update();
      }
    }
    // the free circle (green), rebuilt when it changes by a centimetre
    const fk = st.near ? [Math.round(st.near.x * 100), Math.round(st.near.y * 100)].join() : '';
    if (fk !== keys.free) {
      keys.free = fk;
      if (freeRing) {
        for (const o of freeRing.userData.extra || []) {
          droid.remove(o); if (o.material.map) o.material.map.dispose(); o.material.dispose(); if (!o.isSprite) o.geometry?.dispose();
        }
        droid.remove(freeRing); dispose(freeRing); freeRing = null;
      }
      if (fk) {
        freeRing = new THREE.Mesh(new THREE.RingGeometry(st.free - 0.015, st.free + 0.015, 96),
          new THREE.MeshBasicMaterial({ color: '#56d364', side: THREE.DoubleSide }));
        freeRing.rotation.x = -Math.PI / 2; freeRing.position.y = 0.004;
        // the size on the ring, straight ahead of R2 (in the droid group: three.js Z is forward)
        const label = textSprite(freeText(st.free)); label.position.set(0, 0.06, st.free);
        // and a line from R2 to the nearest point (base_link -> three.js: X = y, Z = x)
        const nx = st.near.y, nz = st.near.x;
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0.012, 0), new THREE.Vector3(nx, 0.012, nz)]),
          new THREE.LineBasicMaterial({ color: '#ffa657', depthTest: false }));
        const dot = new THREE.Mesh(new THREE.SphereGeometry(0.018, 16, 8), new THREE.MeshBasicMaterial({ color: '#ffa657', depthTest: false }));
        dot.position.set(nx, 0.018, nz);
        line.renderOrder = dot.renderOrder = 9;        // over the droid, however close
        freeRing.userData.extra = [label, line, dot]; droid.add(label, line, dot);
        droid.add(freeRing);
      }
      dirty = true;
    }
    // the safety ring and the heading arrow are rebuilt only when they change
    if ((st.radius || 0) !== keys.radius) {
      keys.radius = st.radius || 0;
      if (ring) { droid.remove(ring); dispose(ring); ring = null; }
      if (st.radius) {
        ring = new THREE.Mesh(new THREE.RingGeometry(st.radius - 0.01, st.radius + 0.01, 64),
          new THREE.MeshBasicMaterial({ color: '#f85149', side: THREE.DoubleSide, transparent: true, opacity: 0.8 }));
        ring.rotation.x = -Math.PI / 2; ring.position.y = 0.005;
        droid.add(ring);
      }
      dirty = true;
    }
    const moving = st.heading != null && st.state && !['idle', 'manual', 'gave up', 'arrived', 'no data'].includes(st.state);
    const ak = moving ? [st.state, st.heading.toFixed(3), (st.v || 0).toFixed(3), x.toFixed(3), y.toFixed(3)].join() : '';
    if (ak !== keys.arrow) {
      keys.arrow = ak;
      if (arrow) { scene.remove(arrow); arrow.dispose?.(); arrow = null; }
      if (moving) {
        const col = { stop: '#f85149', avoiding: '#d29922', turning: '#d29922', reversing: '#d29922', waiting: '#d29922' }[st.state] || '#3fb950';
        arrow = new THREE.ArrowHelper(V(Math.cos(st.heading), Math.sin(st.heading), 0), V(x, y, 0.02), 0.4 + 1.5 * Math.abs(st.v || 0), col, 0.15, 0.1);
        scene.add(arrow);
      }
      dirty = true;
    }
    if (dirty) { renderer.render(scene, cam); dirty = false; }
  }

  async function setModel(key) {
    if (keys.model === key) return;
    keys.model = key;
    const next = await loadModelMetres(key);
    if (keys.model !== key) return;            // another one was asked for meanwhile
    if (model) { droid.remove(model.root); dispose(model.root); }
    model = next;
    droid.add(model.root);
    dirty = true;
  }

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    cam.aspect = w / h;
    cam.updateProjectionMatrix();
    dirty = true;
  }
  new ResizeObserver(resize).observe(container);
  return { draw, setModel, resize, opts, redraw: () => { dirty = true; } };
}
