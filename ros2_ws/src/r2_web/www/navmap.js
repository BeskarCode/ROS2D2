// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Top-down map of the Navigation page (canvas, odom frame: x right, y up on screen).
// Draws the room (in simulation), the droid at its pose, the safety circle, each distance
// sensor's beam as long as its reading, the lidar's points, the goal, the chosen heading and
// the trail. Click the floor = goal; drag an obstacle = move it; right-click = remove it.
import { R2 } from './sensormath.js';

const COL = { rplidar_c1: '#39c5cf', vl53l0x: '#a371f7', hcsr04: '#f0b429' };
const rad = (d) => d * Math.PI / 180;

export function createNavMap(cv, { onGoal, onMove, onSelect, onRemove }) {
  const g = cv.getContext('2d');
  let view = { x0: -3.2, x1: 3.2, y0: -2.13, y1: 2.13 };
  let last = null;
  const S = () => cv.width / (view.x1 - view.x0);
  const P = (x, y) => [(x - view.x0) * S(), (view.y1 - y) * S()];
  const W = (px, py) => [view.x0 + px / S(), view.y1 - py / S()];

  function fit(world) {
    const [x0, x1, y0, y1] = world ? world.room : [-3, 3, -2, 2];
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const half = Math.max((x1 - x0) / 2 + 0.2, ((y1 - y0) / 2 + 0.2) * 1.5);
    view = { x0: cx - half, x1: cx + half, y0: cy - half / 1.5, y1: cy + half / 1.5 };
  }

  const toOdom = (pose, f, l) => [pose.x + f * Math.cos(pose.th) - l * Math.sin(pose.th),
                                  pose.y + f * Math.sin(pose.th) + l * Math.cos(pose.th)];

  function draw(st) {
    last = st;
    fit(st.world);
    g.clearRect(0, 0, cv.width, cv.height);
    g.strokeStyle = '#1a2029'; g.lineWidth = 1;
    for (let x = Math.ceil(view.x0 * 2) / 2; x <= view.x1; x += 0.5) { g.beginPath(); g.moveTo(...P(x, view.y0)); g.lineTo(...P(x, view.y1)); g.stroke(); }
    for (let y = Math.ceil(view.y0 * 2) / 2; y <= view.y1; y += 0.5) { g.beginPath(); g.moveTo(...P(view.x0, y)); g.lineTo(...P(view.x1, y)); g.stroke(); }
    if (st.world) {
      const [x0, x1, y0, y1] = st.world.room;
      g.strokeStyle = '#8b949e'; g.lineWidth = 3; g.strokeRect(...P(x0, y1), (x1 - x0) * S(), (y1 - y0) * S());
      for (const o of st.world.obstacles) {
        const sel = o.id === st.selected;
        g.fillStyle = o.kind === 'low' ? 'rgba(248,81,73,.35)' : '#2b3340';
        g.strokeStyle = sel ? '#3b82f6' : o.kind === 'low' ? '#f85149' : '#8b949e'; g.lineWidth = sel ? 3 : 1.5;
        if (o.kind === 'post') { g.beginPath(); g.arc(...P(o.x, o.y), Math.max(o.r * S(), 4), 0, 7); g.fill(); g.stroke(); }
        else { const [x, y] = P(o.x - o.w / 2, o.y + o.h / 2); g.fillRect(x, y, o.w * S(), o.h * S()); g.strokeRect(x, y, o.w * S(), o.h * S()); }
      }
    }
    if (st.showTrail && st.trail.length > 1) {
      g.strokeStyle = 'rgba(59,130,246,.5)'; g.lineWidth = 2; g.beginPath(); g.moveTo(...P(...st.trail[0]));
      for (const t of st.trail) g.lineTo(...P(...t));
      g.stroke();
    }
    if (st.goal) {
      const [gx, gy] = P(...st.goal);
      g.strokeStyle = '#3fb950'; g.lineWidth = 2; g.beginPath(); g.arc(gx, gy, 12, 0, 7); g.stroke();
      g.beginPath(); g.moveTo(gx, gy); g.lineTo(gx, gy - 26); g.stroke(); g.fillStyle = '#3fb950'; g.fillRect(gx, gy - 26, 14, 9);
    }
    const pose = st.pose;
    if (!pose) return;
    // distance sensors: a beam as long as what it reads (red inside its stop distance)
    if (st.showRays) {
      for (const [name, s] of Object.entries(st.sensors)) {
        if (s.type === 'rplidar_c1') continue;
        const d = st.readings[name], stop = st.stops[name] || 0;
        const floor = s.pitch_deg > 30;
        const len = floor ? 0.2 : d ?? Math.min(s.range_max, 1.5);
        const [sx, sy] = toOdom(pose, s.x, s.y);
        const a = pose.th + rad(s.yaw_deg), h = rad(s.fov_deg) / 2;
        g.fillStyle = (d != null && stop && d < stop ? '#f85149' : COL[s.type]) + (d != null && !floor ? '55' : '22');
        g.beginPath(); g.moveTo(...P(sx, sy)); g.arc(...P(sx, sy), len * S(), -(a + h), -(a - h)); g.closePath(); g.fill();
      }
    }
    g.fillStyle = '#39c5cf';
    for (const [x, y] of st.scan) { g.beginPath(); g.arc(...P(x, y), 2.3, 0, 7); g.fill(); }
    // the safety circle and the droid
    if (st.radius) {
      g.setLineDash([8, 6]); g.strokeStyle = 'rgba(248,81,73,.8)'; g.lineWidth = 2;
      g.beginPath(); g.arc(...P(pose.x, pose.y), st.radius * S(), 0, 7); g.stroke(); g.setLineDash([]);
    }
    g.save(); g.translate(...P(pose.x, pose.y)); g.rotate(-pose.th);
    g.fillStyle = '#202833'; g.strokeStyle = '#8b949e'; g.lineWidth = 1.5;
    for (const f of R2.feet) {
      g.fillRect((f.x - f.l / 2) * S(), (-f.y - f.w / 2) * S(), f.l * S(), f.w * S());
      g.strokeRect((f.x - f.l / 2) * S(), (-f.y - f.w / 2) * S(), f.l * S(), f.w * S());
    }
    g.fillStyle = '#161b22'; g.beginPath(); g.arc(0, 0, R2.bodyR * S(), 0, 7); g.fill(); g.stroke();
    g.fillStyle = '#e6edf3'; g.beginPath(); g.moveTo(R2.bodyR * S() - 4, 0); g.lineTo(R2.bodyR * S() - 16, -7); g.lineTo(R2.bodyR * S() - 16, 7); g.fill();
    g.restore();
    if (st.heading != null && st.state && !['idle', 'manual', 'gave up', 'arrived', 'no data'].includes(st.state)) {
      const [x0, y0] = P(pose.x, pose.y), L = 30 + 160 * Math.abs(st.v || 0);
      g.strokeStyle = { stop: '#f85149', avoiding: '#d29922', turning: '#d29922', reversing: '#d29922', waiting: '#d29922' }[st.state] || '#3fb950';
      g.lineWidth = 4; g.beginPath(); g.moveTo(x0, y0);
      const x1 = x0 + L * Math.cos(st.heading), y1 = y0 - L * Math.sin(st.heading);
      g.lineTo(x1, y1); g.stroke(); g.beginPath(); g.arc(x1, y1, 5, 0, 7); g.fillStyle = g.strokeStyle; g.fill();
    }
  }

  // ---------- mouse ----------
  let drag = null, moved = false;
  const evW = (e) => { const r = cv.getBoundingClientRect(); return W((e.clientX - r.left) * cv.width / r.width, (e.clientY - r.top) * cv.height / r.height); };
  const hit = (x, y) => (last && last.world ? last.world.obstacles.find((o) => (o.kind === 'post'
    ? Math.hypot(x - o.x, y - o.y) < Math.max(o.r, 0.08) : Math.abs(x - o.x) < o.w / 2 && Math.abs(y - o.y) < o.h / 2)) : null);
  cv.addEventListener('contextmenu', (e) => e.preventDefault());
  cv.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    const [x, y] = evW(e);
    const o = hit(x, y);
    moved = false;
    if (e.button === 2) { if (o) onRemove(o.id); return; }
    onSelect(o ? o.id : null);
    if (o) { drag = o; cv.setPointerCapture(e.pointerId); }
  });
  cv.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const [x, y] = evW(e);
    drag.x = x; drag.y = y; moved = true;
    onMove(drag.id, x, y, false);
  });
  cv.addEventListener('pointerup', (e) => {
    if (drag && moved) onMove(drag.id, drag.x, drag.y, true);
    else if (!drag && e.button === 0) onGoal(...evW(e));
    drag = null;
  });
  return { draw };
}
