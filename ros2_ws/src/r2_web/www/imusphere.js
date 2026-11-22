// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup → IMU: the attitude sphere. The sphere is the world (sky above, floor below, a line every 10° of
// pitch, the heading every 30° round its equator) and turns the opposite way to R2, so we see the floor
// tilt and the heading go by; the arrows are R2's body (X red forward, Y green left, Z blue up) and the
// yellow one is the acceleration without gravity (what moves R2). Drag to look from another side.
// It draws only when told (set, drag, resize): nothing runs while the tab is hidden.
import * as THREE from 'three';

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888';

function skyTexture() {
  const cv = document.createElement('canvas');
  cv.width = 1024; cv.height = 512;
  const g = cv.getContext('2d');
  g.fillStyle = '#1f4e79'; g.fillRect(0, 0, 1024, 256);
  g.fillStyle = '#6b4f2a'; g.fillRect(0, 256, 1024, 256);
  g.strokeStyle = 'rgba(255,255,255,.55)'; g.lineWidth = 2;
  for (let p = -80; p <= 80; p += 10) {
    if (!p) continue;
    const y = 256 - (p / 90) * 256;
    g.beginPath(); g.moveTo(0, y); g.lineTo(1024, y); g.stroke();
  }
  g.strokeStyle = '#fff'; g.lineWidth = 5;
  g.beginPath(); g.moveTo(0, 256); g.lineTo(1024, 256); g.stroke();
  g.fillStyle = '#fff'; g.font = 'bold 26px system-ui'; g.textAlign = 'center';
  for (let h = 0; h < 360; h += 30) g.fillText(`${h}°`, ((1 - h / 360) * 1024) % 1024, 246);
  return new THREE.CanvasTexture(cv);
}

export function createImuSphere(el) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  el.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  let az = 0.6, elev = 0.35;
  const place = () => {
    const r = 6;
    camera.position.set(r * Math.cos(elev) * Math.cos(az), r * Math.cos(elev) * Math.sin(az), r * Math.sin(elev));
    camera.up.set(0, 0, 1);
    camera.lookAt(0, 0, 0);
  };
  place();
  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const sun = new THREE.DirectionalLight(0xffffff, 0.5);
  sun.position.set(3, -2, 5);
  scene.add(sun);

  const tex = skyTexture();
  const ball = new THREE.Mesh(new THREE.SphereGeometry(1.3, 64, 32), new THREE.MeshPhongMaterial({ map: tex, shininess: 20 }));
  ball.rotation.x = Math.PI / 2;            // the texture's equator on the XY plane (Z up)
  const world = new THREE.Group();
  world.add(ball);
  scene.add(world);

  const arrow = (dir, color, len = 1.9) => {
    const a = new THREE.ArrowHelper(new THREE.Vector3(...dir).normalize(), new THREE.Vector3(), len, new THREE.Color(color), 0.3, 0.16);
    scene.add(a);
    return a;
  };
  arrow([1, 0, 0], css('--red')); arrow([0, 1, 0], css('--green')); arrow([0, 0, 1], css('--blue'));
  const acc = arrow([1, 0, 0], css('--amber'), 1.6);
  acc.visible = false;

  const draw = () => renderer.render(scene, camera);
  const resize = () => {
    const w = Math.max(160, Math.min(360, el.clientWidth || 360));
    renderer.setSize(w, w);
    draw();
  };

  let drag = null;
  const down = (e) => { drag = [e.clientX, e.clientY, az, elev]; renderer.domElement.setPointerCapture(e.pointerId); };
  const move = (e) => {
    if (!drag) return;
    az = drag[2] - (e.clientX - drag[0]) / 150;
    elev = Math.max(-1.2, Math.min(1.2, drag[3] + (e.clientY - drag[1]) / 150));
    place(); draw();
  };
  const up = () => { drag = null; };
  renderer.domElement.addEventListener('pointerdown', down);
  renderer.domElement.addEventListener('pointermove', move);
  renderer.domElement.addEventListener('pointerup', up);
  renderer.domElement.style.touchAction = 'none';
  renderer.domElement.style.cursor = 'grab';
  renderer.domElement.title = 'Drag to look from another side';
  resize();

  return {
    // R2's roll, pitch, yaw in degrees; lin = acceleration without gravity in R2's axes (m/s²)
    set(roll, pitch, yaw, lin) {
      const d = THREE.MathUtils.degToRad;
      world.rotation.set(0, 0, 0);
      world.rotateZ(-d(yaw)); world.rotateY(-d(pitch)); world.rotateX(-d(roll));
      const m = Math.hypot(...lin);
      acc.visible = m > 0.05;
      if (acc.visible) { acc.setDirection(new THREE.Vector3(...lin).normalize()); acc.setLength(1.6 + m * 0.6, 0.3, 0.18); }
      draw();
    },
    resize,
    dispose() { renderer.dispose(); tex.dispose(); renderer.domElement.remove(); },
  };
}
