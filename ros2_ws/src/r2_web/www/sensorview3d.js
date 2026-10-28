// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The sensor setup in 3D: the droid (either model, real size), the lidar as a flat slice
// at its height, each distance sensor as a cone cut where it meets the floor, the test
// object and the lidar's live points. Draws only when something changes.
// three.js axes: X left, Y up, Z forward (toThree); metres.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { loadModelMetres } from './models.js';
import { TYPES, isLidar, reach, toThree } from './sensormath.js';

const rad = (d) => d * Math.PI / 180;
const V = (x, y, z) => new THREE.Vector3(...toThree(x, y, z));

export function createSensorView3d(container) {
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
      const T = TYPES[s.type], missing = s.found === false, on = s.name === state.selected;
      const dot = new THREE.Mesh(new THREE.SphereGeometry(on ? 0.028 : 0.02, 16, 8), new THREE.MeshBasicMaterial({ color: T.colour }));
      dot.position.copy(V(s.x, s.y, s.z));
      dyn.add(dot);
      const mat = new THREE.MeshBasicMaterial({ color: T.colour, transparent: true, opacity: missing ? 0.04 : on ? 0.3 : 0.14,
        side: THREE.DoubleSide, depthWrite: false, clippingPlanes: [floor] });
      if (isLidar(s)) dyn.add(...slice(s, mat, state.fullRange ? s.range_max : Math.min(s.range_max, 1.5)));
      else dyn.add(cone(s, mat, state.fullRange ? s.range_max : Math.min(s.range_max, Math.max(1.5, reach(s)))));
    }
    const ob = state.object, rr = Math.max(ob.size, 0.02) / 2;
    const seen = state.sensors.some((s) => state.hits[s.name] != null);
    const post = new THREE.Mesh(new THREE.CylinderGeometry(rr, rr, ob.heightTop, 24),
      new THREE.MeshStandardMaterial({ color: seen ? '#3fb950' : '#e6edf3' }));
    post.position.copy(V(ob.x, ob.y, ob.heightTop / 2));
    dyn.add(post);
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
