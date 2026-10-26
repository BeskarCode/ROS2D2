// A plain R2 from primitives, real size in metres: body, dome with its eye, two outer legs
// and three feet (the same outline the sensor setup uses for its coverage map).
// Front is +Z, up is +Y, left is +X; the feet stand on y = 0.
// Returns { root, dome }: rotate dome.rotation.y to turn the dome.
import * as THREE from 'three';
import { R2, toThree } from './sensormath.js';

const GREY = new THREE.MeshStandardMaterial({ color: 0xc9d1d9, roughness: 0.6 });
const BLUE = new THREE.MeshStandardMaterial({ color: 0x3b6fd8, roughness: 0.5 });
const DARK = new THREE.MeshStandardMaterial({ color: 0x30363d, roughness: 0.8 });

const BODY_BOTTOM = 0.26;
const BODY_H = 0.60;
const DOME_Y = BODY_BOTTOM + BODY_H;      // the dome's base; it spins about its centre

function box(w, h, d, mat, x, y, z) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  return m;
}

export function buildR2Simple() {
  const root = new THREE.Group();
  const r = R2.bodyR;

  const body = new THREE.Mesh(new THREE.CylinderGeometry(r, r, BODY_H, 48), GREY);
  body.position.y = BODY_BOTTOM + BODY_H / 2;
  root.add(body);

  const dome = new THREE.Group();
  dome.position.y = DOME_Y;
  dome.add(new THREE.Mesh(new THREE.SphereGeometry(r, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), GREY));
  // the radar eye shows where the dome looks
  const eye = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 8), DARK);
  const a = THREE.MathUtils.degToRad(48);
  eye.position.set(0, Math.cos(a) * r * 0.97, Math.sin(a) * r * 0.97);
  dome.add(eye);
  root.add(dome);

  for (const f of R2.feet) {
    const [fx, , fz] = toThree(f.x, f.y, 0);
    root.add(box(f.w, 0.12, f.l, DARK, fx, 0.06, fz));
    if (f.y !== 0) {
      const [lx, , lz] = toThree(f.x + 0.04, f.y * 0.92, 0);
      root.add(box(0.06, 0.75, 0.18, BLUE, lx, 0.47, lz));
    } else {
      root.add(box(0.10, 0.20, 0.12, BLUE, fx, 0.21, fz));
    }
  }
  return { root, dome };
}
