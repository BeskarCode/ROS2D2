// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// A plain R2 from primitives, real size in metres, standing like the full model (three
// legs): the body leans back on its shoulders, the outer legs hang straight down to their
// feet, and the centre leg drops from under the body to the front foot (where the lidar is).
// The feet are the same outline the sensor setup uses for its coverage map.
// Front is +Z, up is +Y, left is +X; the feet stand on y = 0.
// Returns { root, dome }: rotate dome.rotation.y to turn the dome (about the leaning body's axis).
import * as THREE from 'three';
import { R2, toThree } from './sensormath.js';

const GREY = new THREE.MeshStandardMaterial({ color: 0xc9d1d9, roughness: 0.6 });
const BLUE = new THREE.MeshStandardMaterial({ color: 0x3b6fd8, roughness: 0.5 });
const DARK = new THREE.MeshStandardMaterial({ color: 0x30363d, roughness: 0.8 });

const SHOULDER_Y = 0.75;     // the body turns on the shoulders...
const LEAN = 15.6;           // ...and leans back this much, as in the full model
const BODY_BOTTOM = 0.26;    // upright, before leaning
const BODY_H = 0.60;

function box(w, h, d, mat, x, y, z) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  return m;
}

export function buildR2Simple() {
  const root = new THREE.Group();
  const r = R2.bodyR;

  // body and dome lean back together about the shoulder axis (X)
  const lean = new THREE.Group();
  lean.position.y = SHOULDER_Y;
  lean.rotation.x = -THREE.MathUtils.degToRad(LEAN);
  root.add(lean);
  const body = new THREE.Mesh(new THREE.CylinderGeometry(r, r, BODY_H, 48), GREY);
  body.position.y = BODY_BOTTOM + BODY_H / 2 - SHOULDER_Y;
  lean.add(body);
  const dome = new THREE.Group();
  dome.position.y = BODY_BOTTOM + BODY_H - SHOULDER_Y;
  dome.add(new THREE.Mesh(new THREE.SphereGeometry(r, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), GREY));
  const eye = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 8), DARK);   // shows where the dome looks
  const a = THREE.MathUtils.degToRad(48);
  eye.position.set(0, Math.cos(a) * r * 0.97, Math.sin(a) * r * 0.97);
  dome.add(eye);
  lean.add(dome);

  // where the bottom of the leaning body ends up: the centre leg hangs from there
  const bottom = new THREE.Vector3(0, BODY_BOTTOM - SHOULDER_Y, 0).applyEuler(lean.rotation).add(lean.position);

  for (const f of R2.feet) {
    const [fx, , fz] = toThree(f.x, f.y, 0);
    root.add(box(f.w, 0.12, f.l, DARK, fx, 0.06, fz));
    if (f.y !== 0) {
      // outer leg: straight from the shoulder hub down to its foot
      const top = SHOULDER_Y + 0.08, h = top - 0.12;
      root.add(box(0.07, h, 0.18, BLUE, fx, 0.12 + h / 2, fz + 0.02));
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.05, 24), GREY);
      hub.rotation.z = Math.PI / 2;
      hub.position.set(Math.sign(fx) * (r + 0.025), SHOULDER_Y, 0);
      root.add(hub);
    } else {
      // centre leg: from under the body down to the front foot
      const h = bottom.y - 0.12;
      root.add(box(0.12, h, 0.12, BLUE, fx, 0.12 + h / 2, (bottom.z + fz) / 2));
    }
  }
  return { root, dome };
}
