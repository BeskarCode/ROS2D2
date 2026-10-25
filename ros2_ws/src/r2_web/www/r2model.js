// A simple R2 built from primitives. Front is +Z, up is +Y, the dome turns around Y.
// Returns { root, dome }: rotate dome.rotation.y to turn the dome.
import * as THREE from 'three';

const WHITE = new THREE.MeshStandardMaterial({ color: 0xe8ecf0, roughness: 0.55, metalness: 0.05 });
const BLUE = new THREE.MeshStandardMaterial({ color: 0x1f4fa8, roughness: 0.5, metalness: 0.1 });
const SILVER = new THREE.MeshStandardMaterial({ color: 0xc9ced6, roughness: 0.25, metalness: 0.85 });
const DARK = new THREE.MeshStandardMaterial({ color: 0x15171c, roughness: 0.3, metalness: 0.2 });
const EYE = new THREE.MeshStandardMaterial({ color: 0x050608, roughness: 0.05, metalness: 0.6 });
const RED = new THREE.MeshStandardMaterial({ color: 0xff3030, emissive: 0xaa0000, emissiveIntensity: 1.2 });
const LIGHTBLUE = new THREE.MeshStandardMaterial({ color: 0x40a0ff, emissive: 0x1060ff, emissiveIntensity: 1.2 });

const BODY_R = 1.0;
const BODY_H = 1.6;

// A thin box lying on a sphere of radius r, centred at polar angle (from +Y) and azimuth (from +Z)
function onSphere(r, polarDeg, azimuthDeg, w, h, mat, depth = 0.04) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, depth), mat);
  const pol = THREE.MathUtils.degToRad(polarDeg);
  const az = THREE.MathUtils.degToRad(azimuthDeg);
  const dir = new THREE.Vector3(Math.sin(pol) * Math.sin(az), Math.cos(pol), Math.sin(pol) * Math.cos(az));
  m.position.copy(dir.clone().multiplyScalar(r));
  m.lookAt(dir.clone().multiplyScalar(r * 2));
  return m;
}

// The same on the body cylinder, at height y and azimuth (from +Z)
function onCylinder(r, y, azimuthDeg, w, h, mat, depth = 0.04) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, depth), mat);
  const az = THREE.MathUtils.degToRad(azimuthDeg);
  m.position.set(Math.sin(az) * r, y, Math.cos(az) * r);
  m.rotation.y = az;
  return m;
}

function buildDome() {
  const dome = new THREE.Group();
  const shell = new THREE.Mesh(
    new THREE.SphereGeometry(BODY_R, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), SILVER);
  dome.add(shell);

  // Ring of blue panels around the lower dome, wider gap at the front for the eye
  for (const az of [-150, -110, -70, 70, 110, 150, 180]) {
    dome.add(onSphere(BODY_R, 72, az, 0.28, 0.24, BLUE));
  }
  // Upper panels
  for (const az of [-135, -45, 45, 135]) {
    dome.add(onSphere(BODY_R, 38, az, 0.22, 0.18, BLUE));
  }
  // Radar eye: the "face" of the dome, so its direction is obvious
  const eye = new THREE.Mesh(new THREE.SphereGeometry(0.17, 24, 16), EYE);
  const eyeDir = new THREE.Vector3(0, Math.cos(THREE.MathUtils.degToRad(48)), Math.sin(THREE.MathUtils.degToRad(48)));
  eye.position.copy(eyeDir.multiplyScalar(BODY_R * 0.93));
  dome.add(eye);
  dome.add(onSphere(BODY_R, 48, 0, 0.42, 0.42, BLUE, 0.02));
  // Front logic displays and PSIs
  dome.add(onSphere(BODY_R, 70, 0, 0.36, 0.12, DARK));
  dome.add(onSphere(BODY_R, 68, -28, 0.1, 0.1, RED));
  dome.add(onSphere(BODY_R, 68, 28, 0.1, 0.1, LIGHTBLUE));
  // Holoprojectors: top, front and rear
  for (const [pol, az] of [[10, 0], [62, 18], [62, 180]]) {
    const holo = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.14, 16), DARK);
    const p = THREE.MathUtils.degToRad(pol);
    const a = THREE.MathUtils.degToRad(az);
    const dir = new THREE.Vector3(Math.sin(p) * Math.sin(a), Math.cos(p), Math.sin(p) * Math.cos(a));
    holo.position.copy(dir.clone().multiplyScalar(BODY_R + 0.03));
    holo.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    dome.add(holo);
  }
  return dome;
}

function buildBody() {
  const body = new THREE.Group();
  body.add(new THREE.Mesh(new THREE.CylinderGeometry(BODY_R, BODY_R * 0.98, BODY_H, 48), WHITE));
  // Front panels
  body.add(onCylinder(BODY_R, 0.45, 0, 0.5, 0.35, BLUE));
  body.add(onCylinder(BODY_R, 0.0, -18, 0.18, 0.5, BLUE));
  body.add(onCylinder(BODY_R, 0.0, 18, 0.18, 0.5, BLUE));
  body.add(onCylinder(BODY_R, -0.5, 0, 0.6, 0.18, SILVER));
  // Side and rear vents
  for (const az of [90, -90, 180]) {
    body.add(onCylinder(BODY_R, 0.25, az, 0.3, 0.7, BLUE));
  }
  // Dome ring
  const ring = new THREE.Mesh(new THREE.CylinderGeometry(BODY_R * 1.01, BODY_R * 1.01, 0.08, 48), SILVER);
  ring.position.y = BODY_H / 2 - 0.04;
  body.add(ring);
  return body;
}

function buildLeg(side) {
  const leg = new THREE.Group();
  const strut = new THREE.Mesh(new THREE.BoxGeometry(0.22, 1.9, 0.45), WHITE);
  strut.position.y = -0.35;
  leg.add(strut);
  const panel = new THREE.Mesh(new THREE.BoxGeometry(0.03, 1.1, 0.26), BLUE);
  panel.position.set(side * 0.125, -0.25, 0);
  leg.add(panel);
  const shoulder = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.08, 24), SILVER);
  shoulder.rotation.z = Math.PI / 2;
  shoulder.position.set(side * 0.13, 0.45, 0);
  leg.add(shoulder);
  const foot = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.35, 0.7), WHITE);
  foot.position.set(0, -1.45, 0.05);
  leg.add(foot);
  leg.position.set(side * (BODY_R + 0.13), 0, -0.05);
  return leg;
}

export function buildR2() {
  const root = new THREE.Group();
  const body = buildBody();
  root.add(body);

  const dome = buildDome();
  dome.position.y = BODY_H / 2;
  root.add(dome);

  root.add(buildLeg(1), buildLeg(-1));
  const centre = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.5, 0.5), WHITE);
  centre.position.set(0, -BODY_H / 2 - 0.4, 0);
  root.add(centre);
  const centreFoot = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.3, 0.6), WHITE);
  centreFoot.position.set(0, -BODY_H / 2 - 0.85, 0.05);
  root.add(centreFoot);

  // Stand the feet on y = 0
  root.position.y = 1.95;
  return { root, dome };
}
