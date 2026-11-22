// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The header's status pills, the same on every page (statuspills.js decides what they say). Each page
// imports this: it puts them right after the section links and keeps them up to date from ROS.
import { connect, subscribe } from './rosbridge.js';
import { statusPills } from './statuspills.js';

const st = { ros: null, mega: null, pico: null, picoAt: null, scanAt: null, cams: {}, auto: false, mode: '', track: false, pads: null };
let box = null, heartAt = 0, started = false;

function render() {
  if (!box) return;
  const now = Date.now();
  st.ros = heartAt ? now - heartAt < 3000 : st.ros;
  box.replaceChildren(...statusPills(st, now).map((p) => {
    const el = document.createElement(p.href ? 'a' : 'span');
    el.className = `pill ${p.cls}`;
    el.title = p.title;
    if (p.href) { el.href = p.href; el.style.textDecoration = 'none'; }
    const i = document.createElement('i');
    i.className = `fa-solid ${p.icon}`;
    el.append(i, document.createTextNode(p.text));     // text goes in as text
    return el;
  }));
}

function start() {
  const nav = document.querySelector('header nav.modes');
  if (!nav || started) return;
  started = true;
  box = document.createElement('span');
  box.className = 'pills';
  nav.after(box);
  render();
  connect(() => { if (!heartAt) heartAt = Date.now(); render(); });   // the shared socket; the heartbeat keeps it honest
  subscribe('/web/heartbeat', 'std_msgs/msg/String', () => { heartAt = Date.now(); });
  subscribe('/mega/connected', 'std_msgs/msg/Bool', (m) => { st.mega = m.data; render(); });
  subscribe('/pico/state', 'std_msgs/msg/String', (m) => {
    try { st.pico = JSON.parse(m.data); st.picoAt = Date.now(); } catch { /* ignore */ }
  }, 1000);
  subscribe('/scan', 'sensor_msgs/msg/LaserScan', () => { st.scanAt = Date.now(); }, 2000);
  subscribe('/r2/auto_mode', 'std_msgs/msg/Bool', (m) => { st.auto = m.data; render(); });
  subscribe('/r2/mode', 'std_msgs/msg/String', (m) => { st.mode = m.data; render(); });
  subscribe('/mega/pads', 'std_msgs/msg/String', (m) => {
    try { st.pads = JSON.parse(m.data); } catch { return; }
    render();
  });
  subscribe('/r2/track_mode', 'std_msgs/msg/Bool', (m) => { st.track = m.data; render(); });
  fetch('api/cameras', { cache: 'no-store' }).then((r) => r.json()).then((c) => {
    for (const name of Object.keys(c.cameras || {})) {
      st.cams[name] = 0;
      subscribe(`/cameras/${name}/camera_info`, 'sensor_msgs/msg/CameraInfo', () => { st.cams[name] = Date.now(); }, 2000);
    }
    render();
  }).catch(() => {});
  setInterval(render, 1000);       // ages the "seen lately" ones
  // nothing heard after a while is "nothing there", not "not known yet"
  setTimeout(() => { for (const k of ['picoAt', 'scanAt']) if (st[k] == null) st[k] = 0; render(); }, 8000);
}

start();
