// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The sensor setup in 3D: the droid (either model, real size), the lidar as a flat slice
// at its height, each distance sensor as a cone cut where it meets the floor, the test
// object and the lidar's live points. Draws only when something changes.
// three.js axes: X left, Y up, Z forward (toThree); metres.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { loadModelMetres } from './models.js';
import { TYPES, freeText, isLidar, reach, toThree } from './sensormath.js';
import { textSprite } from './label3d.js';

const rad = (d) => d * Math.PI / 180;
// its type's look, in its grey when it is not responding (state.colours, from sensors.js)
const look = (s, state) => ({ ...TYPES[s.type], colour: (state.colours && state.colours[s.name]) || TYPES[s.type].colour });
const V = (x, y, z) => new THREE.Vector3(...toThree(x, y, z));

export function createSensorView3d(container, { onHover = () => {} } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(devicePixelRatio);
  renderer.localClippingEnabled = true;
  container.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#0b0f14');
  const cam = new THREE.PerspectiveCamera(45, 1, 0.01, 100);
  cam.position.set(-1.9, 1.9, 2.3);          // in front of R2, to its right, above
  const orbit = new OrbitControls(cam, renderer.domElement);
  orbit.target.set(0, 0.35, 0.3);
  orbit.update();
  scene.add(new THREE.HemisphereLight('#cfe3ff', '#202833', 2.2));
  const sun = new THREE.DirectionalLight('#ffffff', 1.4);
  sun.position.set(1, 4, 2);
  scene.add(sun);
  scene.add(new THREE.GridHelper(6, 12, '#2a313c', '#1a2029'));
  for (const m of [0.5, 1, 1.5, 2]) {
    const ring = new THREE.Mesh(new THREE.RingGeometry(m - 0.004, m + 0.004, 96),
      new THREE.MeshBasicMaterial({ color: '#2a313c', side: THREE.DoubleSide }));
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.001;
    scene.add(ring);
  }
  const floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  let model = null;
  const dyn = new THREE.Group();
  scene.add(dyn);

  const render = () => renderer.render(scene, cam);
  orbit.addEventListener('change', render);

  function cone(s, mat, R) {
    const r = Math.tan(rad(s.fov_deg / 2)) * R;
    const g = new THREE.ConeGeometry(r, R, 40, 1, true);
    g.translate(0, -R / 2, 0);               // apex at the sensor, opening along -Y
    const m = new THREE.Mesh(g, mat);
    const p = rad(s.pitch_deg), y = rad(s.yaw_deg);
    const dir = V(Math.cos(p) * Math.cos(y), Math.cos(p) * Math.sin(y), -Math.sin(p)).normalize();
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), dir);
    m.position.copy(V(s.x, s.y, s.z));
    return m;
  }

  function slice(s, mat, R) {
    // CircleGeometry laid flat maps angle phi to (cos phi, 0, -sin phi); a yaw of t
    // (ROS, + left) points at (sin t, 0, cos t), i.e. phi = t - 90 deg
    const h = rad(Math.min(s.fov_deg, 359.9));
    const g = new THREE.CircleGeometry(R, 96, rad(s.yaw_deg - 90) - h / 2, h);
    const out = [new THREE.Mesh(g, mat),
      new THREE.LineSegments(new THREE.EdgesGeometry(g), new THREE.LineBasicMaterial({ color: TYPES[s.type].colour, transparent: true, opacity: 0.6 }))];
    for (const m of out) { m.rotation.x = -Math.PI / 2; m.position.copy(V(s.x, s.y, s.z)); }
    return out;
  }

  function draw(state) {
    dyn.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
    dyn.clear();
    for (const s of state.sensors) {
      const T = look(s, state), missing = s.found === false, on = s.name === state.selected, hov = s.name === state.hovered;
      const dot = new THREE.Mesh(new THREE.SphereGeometry(hov ? 0.04 : on ? 0.028 : 0.02, 16, 8),
        new THREE.MeshBasicMaterial({ color: hov ? '#e6edf3' : T.colour }));
      dot.position.copy(V(s.x, s.y, s.z));
      dot.userData.sensor = s.name;
      dot.userData.dot = true;
      dyn.add(dot);
      if (state.hidden && state.hidden.has(s.name)) continue;
      const mat = new THREE.MeshBasicMaterial({ color: T.colour, transparent: true, opacity: hov ? 0.42 : missing ? 0.04 : on ? 0.3 : 0.14,
        side: THREE.DoubleSide, depthWrite: false, clippingPlanes: [floor] });
      const beam = isLidar(s) ? slice(s, mat, state.fullRange ? s.range_max : Math.min(s.range_max, 1.5))
        : [cone(s, mat, state.fullRange ? s.range_max : Math.min(s.range_max, Math.max(1.5, reach(s))))];
      for (const m of beam) m.userData.sensor = s.name;
      dyn.add(...beam);
    }
    const ob = state.object;     // null: no test object
    if (ob) {
      const rr = Math.max(ob.size, 0.02) / 2;
      const seen = state.sensors.some((s) => state.hits[s.name] != null);
      const post = new THREE.Mesh(new THREE.CylinderGeometry(rr, rr, ob.heightTop, 24),
        new THREE.MeshStandardMaterial({ color: seen ? '#3fb950' : '#e6edf3' }));
      post.position.copy(V(ob.x, ob.y, ob.heightTop / 2));
      dyn.add(post);
    }
    if (state.near) {
      const free = state.near.r;
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([V(0, 0, 0.012), V(state.near.x, state.near.y, 0.012)]),
        new THREE.LineBasicMaterial({ color: '#ffa657', depthTest: false }));
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.018, 16, 8), new THREE.MeshBasicMaterial({ color: '#ffa657', depthTest: false }));
      dot.position.copy(V(state.near.x, state.near.y, 0.018));
      line.renderOrder = dot.renderOrder = 9;          // over the droid, however close
      dyn.add(line, dot);
      const ring = new THREE.Mesh(new THREE.RingGeometry(free - 0.015, free + 0.015, 96),
        new THREE.MeshBasicMaterial({ color: '#56d364', side: THREE.DoubleSide }));
      ring.rotation.x = -Math.PI / 2; ring.position.y = 0.004;
      dyn.add(ring);
      const label = textSprite(freeText(free));
      label.position.copy(V(free, 0, 0.06));             // on the ring, straight ahead
      dyn.add(label);
    }
    if (state.scan && state.scan.length) {
      const lidar = state.sensors.find(isLidar);
      const z = lidar ? lidar.z : 0.1;
      const pos = new Float32Array(state.scan.flatMap(([x, y]) => toThree(x, y, z)));
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      dyn.add(new THREE.Points(g, new THREE.PointsMaterial({ color: '#39c5cf', size: 0.025 })));
    }
    render();
  }

  // the sensor under the mouse: its dot first (small, so it wins), else the nearest beam.
  // Not while orbiting (a button held down).
  const ray = new THREE.Raycaster();
  renderer.domElement.addEventListener('pointermove', (ev) => {
    if (ev.buttons) return;
    const r = renderer.domElement.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1), cam);
    const hits = ray.intersectObjects(dyn.children.filter((o) => o.userData.sensor && o.isMesh), false);
    const hit = hits.find((h) => h.object.userData.dot) || hits[0];
    onHover(hit ? hit.object.userData.sensor : null, ev.clientX, ev.clientY);
  });
  renderer.domElement.addEventListener('pointerleave', () => onHover(null));

  async function setModel(key) {
    const next = await loadModelMetres(key);
    if (model) scene.remove(model.root);
    model = next;
    scene.add(model.root);
    render();
  }

  function resize() {
    const w = container.clientWidth, h = container.clientHeight || w;
    if (!w) return;
    renderer.setSize(w, h, false);
    cam.aspect = w / h;
    cam.updateProjectionMatrix();
    render();
  }
  new ResizeObserver(resize).observe(container);

  return { draw, setModel, resize };
}
