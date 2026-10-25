// The R2 models the viewer can show. Each one becomes { root, dome }: root stands on
// y = 0, about 3.8 units tall, front towards +Z; dome turns around Y at the body's axis.
//
// The downloaded models have no separate dome, so it is cut out by height: every
// triangle above `domeFrom` (a fraction of the height, from the feet) goes to the dome.
import * as THREE from 'three';
import { GLTFLoader } from './vendor/loaders/GLTFLoader.js';
import { MeshoptDecoder } from './vendor/libs/meshopt_decoder.module.js';
import { buildR2 } from './r2model.js';

const HEIGHT = 3.8;

export const MODELS = {
  simple: { label: 'Simple' },
  lazcano: {
    label: 'R2D2 · AlexisVLazcano',
    url: 'models/r2d2-lazcano.glb',
    domeFrom: 0.755,
    yaw: 0,
    // The download has one plain white material: paint body and dome apart so the turn shows
    paint: {
      body: { color: 0xc4c9d0, roughness: 0.75, metalness: 0.05 },
      dome: { color: 0xb8c0cc, roughness: 0.25, metalness: 0.9 },
    },
    credit: '"R2D2" (<a href="https://skfb.ly/RQUY" target="_blank" rel="noopener">skfb.ly/RQUY</a>) by AlexisVLazcano, ' +
            '<a href="http://creativecommons.org/licenses/by-nc/4.0/" target="_blank" rel="noopener">CC BY-NC 4.0</a>',
  },
  remezyuk: {
    label: 'HW13 R2D2 · Dmitriy Remezyuk',
    url: 'models/r2d2-remezyuk.glb',
    domeFrom: 0.79,
    yaw: 0,
    credit: '"HW13 R2D2 HP" (<a href="https://sketchfab.com/3d-models/hw13-r2d2-hp-b3a67b640fef4b4680c5ad398ee9418f" ' +
            'target="_blank" rel="noopener">Sketchfab</a>) by Dmitriy_Remezyuk, ' +
            '<a href="http://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>',
  },
};

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);

export async function loadModel(key, overrides = {}) {
  const spec = { ...MODELS[key], ...overrides };
  if (!spec.url) return buildR2();
  const gltf = await loader.loadAsync(spec.url);
  return splitDome(gltf.scene, spec);
}

// Bake every mesh into world space, normalise size and position, then cut each mesh
// into a body part and a dome part by triangle height.
function splitDome(scene, spec) {
  scene.rotation.y = THREE.MathUtils.degToRad(spec.yaw || 0);
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(scene);
  const size = box.getSize(new THREE.Vector3());
  const k = HEIGHT / size.y;
  const norm = new THREE.Matrix4()
    .makeScale(k, k, k)
    .multiply(new THREE.Matrix4().makeTranslation(-(box.min.x + box.max.x) / 2, -box.min.y, -(box.min.z + box.max.z) / 2));
  const cutY = HEIGHT * spec.domeFrom;

  const paint = Object.fromEntries(Object.entries(spec.paint || {})
    .map(([part, p]) => [part, new THREE.MeshStandardMaterial(p)]));
  const bodyParts = [];
  const domeParts = [];
  scene.traverse((obj) => {
    if (!obj.isMesh) return;
    const geo = toFloatTriangles(obj.geometry);
    geo.applyMatrix4(new THREE.Matrix4().multiplyMatrices(norm, obj.matrixWorld));
    const [below, above] = cutByHeight(geo, cutY);
    if (below) bodyParts.push(new THREE.Mesh(below, paint.body || obj.material));
    if (above) domeParts.push(new THREE.Mesh(above, paint.dome || obj.material));
  });

  // The dome is round: the middle of its parts is the axis it turns around
  const domeBox = new THREE.Box3();
  domeParts.forEach((m) => { m.geometry.computeBoundingBox(); domeBox.union(m.geometry.boundingBox); });
  const axis = domeBox.isEmpty() ? new THREE.Vector3() : domeBox.getCenter(new THREE.Vector3());

  const root = new THREE.Group();
  const dome = new THREE.Group();
  dome.position.set(axis.x, 0, axis.z);
  bodyParts.forEach((m) => root.add(m));
  domeParts.forEach((m) => { m.position.set(-axis.x, 0, -axis.z); dome.add(m); });
  root.add(dome);
  return { root, dome };
}

// Plain float, non-indexed, non-interleaved copy: meshopt stores positions quantized
// (normalised integers), which would clip once the world transform is baked in.
const GET = ['getX', 'getY', 'getZ', 'getW'];
function toFloatTriangles(src) {
  const out = new THREE.BufferGeometry();
  const index = src.index;
  const count = index ? index.count : src.attributes.position.count;
  for (const [name, a] of Object.entries(src.attributes)) {
    if (!['position', 'normal', 'uv', 'color'].includes(name)) continue;
    const arr = new Float32Array(count * a.itemSize);
    for (let i = 0; i < count; i++) {
      const v = index ? index.getX(i) : i;
      for (let c = 0; c < a.itemSize; c++) arr[i * a.itemSize + c] = a[GET[c]](v);
    }
    out.setAttribute(name, new THREE.BufferAttribute(arr, a.itemSize));
  }
  return out;
}

function cutByHeight(geo, cutY) {
  const pos = geo.attributes.position;
  const names = Object.keys(geo.attributes);
  const keep = [[], []];   // triangle starts below / above
  for (let i = 0; i < pos.count; i += 3) {
    const cy = (pos.getY(i) + pos.getY(i + 1) + pos.getY(i + 2)) / 3;
    keep[cy > cutY ? 1 : 0].push(i);
  }
  return keep.map((starts) => {
    if (!starts.length) return null;
    const out = new THREE.BufferGeometry();
    for (const name of names) {
      const a = geo.attributes[name];
      const arr = new a.array.constructor(starts.length * 3 * a.itemSize);
      let o = 0;
      for (const s of starts) {
        for (let v = 0; v < 3; v++) {
          for (let c = 0; c < a.itemSize; c++) arr[o++] = a.array[(s + v) * a.itemSize + c];
        }
      }
      out.setAttribute(name, new THREE.BufferAttribute(arr, a.itemSize));
    }
    return out;
  });
}
