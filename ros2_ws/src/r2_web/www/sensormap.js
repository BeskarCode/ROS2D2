// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Top-down map of the droid and its sensors, in metres, front up (SVG). Sensors and the
// test object are dragged with the mouse; they never leave the view (one outside after
// zooming in is drawn on the edge, where it can be picked up again).
import { R2, TYPES, isLidar, reach, toMap, fromMap } from './sensormath.js';

const rad = (d) => d * Math.PI / 180;
const ZOOM0 = 1.6;

export function createSensorMap(svg, { onMove, onSelect, onObject }) {
  let v = ZOOM0;          // half the view, metres
  let last = null;
  let drag = null;        // sensor name, or 'object'

  const clamp = (x, y) => { const m = v * 0.96; return [Math.max(-m, Math.min(m, x)), Math.max(-m, Math.min(m, y))]; };
  // ROS point -> map point, kept in view
  const at = (x, y) => clamp(...toMap(x, y));

  function fan(s, R) {
    // the cone as a polygon: no arc flags to get wrong with the mirrored axes
    const h = Math.min(s.fov_deg, 359.9);
    const n = Math.max(8, Math.round(h / 4));
    const pts = [toMap(s.x, s.y)];
    for (let i = 0; i <= n; i++) {
      const a = rad(s.yaw_deg - h / 2 + (h * i) / n);
      pts.push(toMap(s.x + Math.cos(a) * R, s.y + Math.sin(a) * R));
    }
    return pts.map((p) => p.map((c) => c.toFixed(4)).join(' ')).join(' L');
  }

  function draw(state) {
    last = state;
    svg.setAttribute('viewBox', `${-v} ${-v} ${2 * v} ${2 * v}`);
    const sw = v / 400;
    let o = '';
    for (let m = 0.5; m <= Math.min(v * 1.5, 12); m += 0.5) {
      o += `<circle r="${m}" fill="none" stroke="#1f2630" stroke-width="${sw}"/>`;
      if (Math.abs(m % 1) < 1e-9) o += `<text x="${m * 0.71 + sw * 3}" y="${-m * 0.71}" fill="#4a5361" font-size="${v / 28}">${m} m</text>`;
    }
    for (const s of state.sensors) {
      const T = TYPES[s.type], missing = s.found === false, on = s.name === state.selected;
      const R = state.fullRange ? reach(s) : Math.min(reach(s), 1.5);
      o += `<path d="M${fan(s, R)} Z" fill="${T.colour}" fill-opacity="${missing ? 0.04 : on ? 0.28 : 0.13}" ` +
           `stroke="${T.colour}" stroke-width="${sw * (on ? 2 : 1)}"${missing ? ` stroke-dasharray="${sw * 6} ${sw * 6}"` : ''}/>`;
    }
    // what each sensor measures now: its fan filled up to the reading
    for (const s of state.sensors) {
      const r = state.readings && state.readings[s.name];
      if (r == null || !Number.isFinite(r)) continue;
      const T = TYPES[s.type];
      o += `<path d="M${fan(s, Math.min(r, reach(s)))} Z" fill="${T.colour}" fill-opacity="0.4" ` +
           `stroke="${T.colour}" stroke-width="${sw * 2.5}"/>`;
    }
    if (state.showGaps && state.cov) {
      for (const [x, y, e] of state.cov.gaps) {
        const [sx, sy] = toMap(x, y);
        o += `<circle cx="${sx.toFixed(3)}" cy="${sy.toFixed(3)}" r="${sw * 2.2}" fill="#f85149" fill-opacity="${e <= 0.5 ? 0.75 : 0.35}"/>`;
      }
    }
    if (state.scan) {
      for (const [x, y] of state.scan) {
        const [sx, sy] = toMap(x, y);
        o += `<circle cx="${sx.toFixed(3)}" cy="${sy.toFixed(3)}" r="${sw * 2}" fill="#39c5cf"/>`;
      }
    }
    // the droid
    for (const f of R2.feet) {
      const [x1, y1] = toMap(f.x + f.l / 2, f.y + f.w / 2);
      o += `<rect x="${x1}" y="${y1}" width="${f.w}" height="${f.l}" rx="0.02" fill="#202833" stroke="#8b949e" stroke-width="${sw}"/>`;
    }
    o += `<circle r="${R2.bodyR}" fill="#161b22" stroke="#8b949e" stroke-width="${sw * 1.5}"/>` +
         `<path d="M0 ${-R2.bodyR + 0.01} l-0.03 0.05 h0.06 z" fill="#e6edf3"/>` +
         `<text y="${v / 60}" text-anchor="middle" font-size="${v / 22}" fill="#8b949e">R2</text>`;
    // test object and who sees it
    const ob = state.object;
    const [ox, oy] = at(ob.x, ob.y);
    for (const s of state.sensors) {
      if (state.hits[s.name] == null) continue;
      const [x, y] = toMap(s.x, s.y);
      o += `<line x1="${x}" y1="${y}" x2="${ox}" y2="${oy}" stroke="#3fb950" stroke-width="${sw * 1.5}" stroke-dasharray="${sw * 5} ${sw * 4}"/>`;
    }
    // sensors on top, so they can always be grabbed
    for (const s of state.sensors) {
      const T = TYPES[s.type], on = s.name === state.selected;
      const [x, y] = at(s.x, s.y);
      const [dx, dy] = toMap(Math.cos(rad(s.yaw_deg)), Math.sin(rad(s.yaw_deg)));
      o += `<g data-name="${s.name}" style="cursor:grab"><circle cx="${x}" cy="${y}" r="${sw * (on ? 9 : 7)}" fill="#0d1117" ` +
           `stroke="${T.colour}" stroke-width="${sw * 2.5}"/><line x1="${x}" y1="${y}" x2="${x + dx * sw * 16}" y2="${y + dy * sw * 16}" ` +
           `stroke="${T.colour}" stroke-width="${sw * (isLidar(s) ? 3.5 : 2.5)}"/></g>`;
    }
    const seen = state.sensors.some((s) => state.hits[s.name] != null);
    o += `<g data-name="" data-object="1" style="cursor:grab"><circle cx="${ox}" cy="${oy}" r="${Math.max(ob.size / 2, sw * 7)}" ` +
         `fill="${seen ? '#3fb950' : '#e6edf3'}" fill-opacity=".9" stroke="#0d1117" stroke-width="${sw}"/></g>`;
    svg.innerHTML = o;
  }

  function toRos(ev) {
    const pt = svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    const [sx, sy] = clamp(p.x, p.y);
    const r = fromMap(sx, sy);
    return { x: Math.round(r.x * 200) / 200, y: Math.round(r.y * 200) / 200 };   // 5 mm steps
  }
  svg.addEventListener('pointerdown', (ev) => {
    const g = ev.target.closest('g[data-name]');
    if (!g) return;
    ev.preventDefault();
    getSelection().removeAllRanges();
    drag = g.dataset.object ? 'object' : g.dataset.name;
    if (drag !== 'object') onSelect(drag);
    svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener('pointermove', (ev) => {
    if (!drag) return;
    const p = toRos(ev);
    // a sensor named after where it sits may get a new name while it moves: keep following it
    if (drag === 'object') onObject(p.x, p.y); else drag = onMove(drag, p.x, p.y) || drag;
  });
  const end = () => { drag = null; };
  for (const e of ['pointerup', 'pointercancel', 'lostpointercapture']) svg.addEventListener(e, end);

  return {
    draw,
    zoom(f) { v = Math.max(0.6, Math.min(13, v * f)); if (last) draw(last); },
    reset() { v = ZOOM0; },
  };
}
