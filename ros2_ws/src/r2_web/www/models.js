// The R2 models the viewer can show. Each one becomes { root, dome }: root stands on
// y = 0, about 3.8 units tall; turning dome.rotation.y turns the dome.
//
// The downloaded models have no separate dome, so it is cut out along a plane: at
// `domeFrom` (a fraction of the height, from the feet) on the body's axis, tilted by
// `pitch` / `roll` degrees when the model's head leans. The dome then turns around the
// plane's normal, i.e. around its own axis.
import * as THREE from 'three';
import { GLTFLoader } from './vendor/loaders/GLTFLoader.js';
import { MeshoptDecoder } from './vendor/libs/meshopt_decoder.module.js';
import { buildR2 } from './r2model.js';

const HEIGHT = 3.8;

export const MODELS = {
  simple: { label: 'Simple' },
  vladimirov: {
    label: 'R2-D2 · ivan.vladimirov08',
    url: 'models/r2d2-vladimirov.glb',
    // The head leans: cut along the blue line at the bottom of the dome
    domeFrom: 0.762,
    pitch: -12.6,
    roll: 3.4,
    yaw: 0,
    credit: '"R2-D2" (<a href="https://sketchfab.com/3d-models/r2-d2-0f9760c4e566442ca80e2fcf7e2faa0d" ' +
            'target="_blank" rel="noopener">Sketchfab</a>) by ivan.vladimirov08, ' +
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
  // Body axis: the round body, fitted just below the dome (leaves the legs out)
  const meshes = [];
  scene.traverse((obj) => {
    if (!obj.isMesh) return;
    const geo = toFloatTriangles(obj.geometry);
    geo.applyMatrix4(new THREE.Matrix4().multiplyMatrices(norm, obj.matrixWorld));
    meshes.push([obj, geo]);
  });
  const cutY = HEIGHT * spec.domeFrom;
  const axis = bodyAxis(meshes.map(([, g]) => g), cutY);
  const origin = new THREE.Vector3(axis.x, cutY, axis.z);
  const deg = THREE.MathUtils.degToRad;
  const normal = new THREE.Vector3(Math.sin(deg(spec.roll || 0)), 1, Math.sin(deg(spec.pitch || 0))).normalize();

  const paint = Object.fromEntries(Object.entries(spec.paint || {})
    .map(([part, p]) => [part, new THREE.MeshStandardMaterial(p)]));
  const bodyParts = [];
  const domeParts = [];
  for (const [obj, geo] of meshes) {
    const [below, above] = cutByPlane(geo, origin, normal);
    if (below) bodyParts.push(new THREE.Mesh(below, paint.body || obj.material));
    if (above) domeParts.push(new THREE.Mesh(above, paint.dome || obj.material));
  }

  // Spin about the centre of the dome's own base: the outline the cut left on the plane.
  // With a leaning head that centre is not on the body's vertical axis.
  const centre = cutCentre(domeParts, origin, normal) || origin;

  // tilt: sits on the cut, its Y along the plane's normal; dome (inside) spins about that Y
  const tilt = new THREE.Group();
  tilt.position.copy(centre);
  tilt.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
  const dome = new THREE.Group();
  tilt.add(dome);
  const toLocal = new THREE.Matrix4().compose(centre, tilt.quaternion, new THREE.Vector3(1, 1, 1)).invert();
  domeParts.forEach((m) => { m.geometry.applyMatrix4(toLocal); dome.add(m); });

  const root = new THREE.Group();
  bodyParts.forEach((m) => root.add(m));
  root.add(tilt);
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

// The dome turns around the body's axis. A box around the parts is not enough: legs,
// holoprojectors and other bits sticking out pull it off-centre and the dome wobbles.
// So fit a circle (least squares) to the vertices in a band just below the cut, then
// fit again without the points far from that circle (the legs' shoulders).
function bodyAxis(geos, cutY) {
  const pts = [];
  for (const g of geos) {
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const y = p.getY(i);
      if (y > cutY - HEIGHT * 0.12 && y < cutY - HEIGHT * 0.02) pts.push([p.getX(i), p.getZ(i)]);
    }
  }
  let fit = fitCircle(pts);
  for (let k = 0; k < 2 && fit; k++) {
    const near = pts.filter(([x, z]) => Math.abs(Math.hypot(x - fit.x, z - fit.z) - fit.r) < fit.r * 0.12);
    fit = fitCircle(near) || fit;
  }
  return fit ? new THREE.Vector3(fit.x, 0, fit.z) : new THREE.Vector3();
}

// Centre of the circle the cut left on the dome: vertices lying on the plane, fitted in
// the plane's own 2D coordinates.
function cutCentre(domeParts, origin, normal) {
  const u = new THREE.Vector3(1, 0, 0).projectOnPlane(normal).normalize();
  const w = new THREE.Vector3().crossVectors(normal, u);
  const eps = HEIGHT * 1e-4;
  const pts = [];
  const v = new THREE.Vector3();
  for (const m of domeParts) {
    const p = m.geometry.attributes.position;
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i).sub(origin);
      if (Math.abs(v.dot(normal)) < eps) pts.push([v.dot(u), v.dot(w)]);
    }
  }
  let fit = fitCircle(pts);
  for (let k = 0; k < 2 && fit; k++) {
    const near = pts.filter(([a, b]) => Math.abs(Math.hypot(a - fit.x, b - fit.z) - fit.r) < fit.r * 0.12);
    fit = fitCircle(near) || fit;
  }
  if (!fit) return null;
  return origin.clone().addScaledVector(u, fit.x).addScaledVector(w, fit.z);
}

function fitCircle(pts) {
  if (pts.length < 8) return null;
  let n = 0, sx = 0, sz = 0, sxx = 0, szz = 0, sxz = 0, sxr = 0, szr = 0, sr = 0;
  for (const [x, z] of pts) {
    const r = x * x + z * z;
    n++; sx += x; sz += z; sxx += x * x; szz += z * z; sxz += x * z; sxr += x * r; szr += z * r; sr += r;
  }
  // Circle x^2 + z^2 = 2ax + 2bz + c: normal equations of the linear least squares
  const A = new THREE.Matrix3().set(2 * sxx, 2 * sxz, sx, 2 * sxz, 2 * szz, sz, 2 * sx, 2 * sz, n);
  if (Math.abs(A.determinant()) < 1e-12) return null;
  const sol = new THREE.Vector3(sxr, szr, sr).applyMatrix3(A.invert());
  return { x: sol.x, z: sol.y, r: Math.sqrt(sol.z + sol.x * sol.x + sol.y * sol.y) };
}

// Split a non-indexed geometry at a plane. Triangles that cross it are clipped (cut in
// two at the plane, attributes interpolated), so the cut is a clean line even when one
// long triangle runs from the body into the dome.
function cutByPlane(geo, origin, normal) {
  const names = Object.keys(geo.attributes);
  const attrs = names.map((n) => geo.attributes[n]);
  const pos = geo.attributes.position;
  const out = [names.map(() => []), names.map(() => [])];   // [below, above][attribute] -> numbers

  const vertex = (i) => attrs.map((a) => Array.from(a.array.subarray(i * a.itemSize, (i + 1) * a.itemSize)));
  const lerp = (va, vb, t) => va.map((arr, k) => arr.map((x, c) => x + (vb[k][c] - x) * t));
  const emit = (side, tri) => tri.forEach((v) => v.forEach((arr, k) => out[side][k].push(...arr)));

  for (let i = 0; i < pos.count; i += 3) {
    const v = [vertex(i), vertex(i + 1), vertex(i + 2)];
    const y = v.map((vv) => {
      const [px, py, pz] = vv[names.indexOf('position')];
      return (px - origin.x) * normal.x + (py - origin.y) * normal.y + (pz - origin.z) * normal.z;
    });
    const above = y.map((d) => d > 0);
    const nAbove = above.filter(Boolean).length;
    if (nAbove === 0 || nAbove === 3) { emit(nAbove ? 1 : 0, v); continue; }
    // Rotate so the lone vertex (alone on its side) comes first, keeping the winding
    const lone = above.findIndex((a) => (nAbove === 1 ? a : !a));
    const a = v[lone], b = v[(lone + 1) % 3], c = v[(lone + 2) % 3];
    const ya = y[lone], yb = y[(lone + 1) % 3], yc = y[(lone + 2) % 3];
    const ab = lerp(a, b, ya / (ya - yb));
    const ac = lerp(a, c, ya / (ya - yc));
    const loneSide = nAbove === 1 ? 1 : 0;
    emit(loneSide, [a, ab, ac]);
    emit(1 - loneSide, [ab, b, c]);
    emit(1 - loneSide, [ab, c, ac]);
  }

  return out.map((lists) => {
    if (!lists[0].length) return null;
    const g = new THREE.BufferGeometry();
    names.forEach((n, k) => g.setAttribute(n, new THREE.BufferAttribute(new Float32Array(lists[k]), attrs[k].itemSize)));
    return g;
  });
}
