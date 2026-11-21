// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The Remote window: two virtual PS3 Navs (foot and dome) to try things at home without the real
// controllers. The Mega takes them exactly as real Navs (ROS:PAD, VirtualPad.h), and a real Nav in
// use always wins. Each page imports this: it adds a "Remote" button to the header.
//
// Safety: a Nav's state goes out 20 times a second only while something is pressed; when the window
// closes, the page goes or the tab is hidden everything is let go at once, and if this page stops
// sending, the Mega lets go by itself in 0.3 s. One window at a time across the console's tabs.
import { createPad } from './padlogic.js';
import { confirmDialog } from './dialog.js';
import { ensureConnected, publish, subscribe } from './rosbridge.js';

const SEND_MS = 50;
const TOPICS = { F: '/pad/foot', D: '/pad/dome' };
const NAMES = { F: 'Foot Nav', D: 'Dome Nav' };

let win = null, btn = null, timer = null, riskOk = false;
let pads = { F: 'none', D: 'none', supported: null, mega: false };
const pad = { F: createPad(), D: createPad() };
const wasActive = { F: false, D: false };
const channel = 'BroadcastChannel' in window ? new BroadcastChannel('r2-remote') : null;
const me = Math.random().toString(36).slice(2);

function addStyle() {
  const s = document.createElement('style');
  s.textContent = `
    .r2rbtn.open { color: #fff !important; background: #1f6feb !important; border-color: #388bfd !important; }
    .r2remote { position: fixed; left: 50%; top: 110px; transform: translateX(-50%); width: min(760px, calc(100vw - 32px)); z-index: 8000;
      background: #161b22; color: #e6edf3; border: 1px solid #3a4250; border-radius: 12px; box-shadow: 0 16px 48px rgba(0,0,0,.6);
      font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
    .r2remote[hidden] { display: none; }
    .r2remote .r2r-bar { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid #2a313c; cursor: move; user-select: none; touch-action: none; }
    .r2remote .r2r-bar b { font-size: 13px; letter-spacing: 1px; text-transform: uppercase; color: #8b949e; }
    .r2remote .r2r-bar .r2r-x { margin-left: auto; background: none; border: none; color: #8b949e; font-size: 16px; cursor: pointer; }
    .r2remote .r2r-pads { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; padding: 14px; }
    @media (max-width: 640px) { .r2remote .r2r-pads { grid-template-columns: 1fr; } }
    .r2remote .r2r-pad { border: 1px solid #2a313c; border-radius: 10px; padding: 10px 12px 14px; }
    .r2remote .r2r-pad.r2r-off { opacity: .5; pointer-events: none; }
    .r2remote h4 { margin: 0 0 6px; display: flex; align-items: center; gap: 8px; font-size: 14px; }
    .r2remote .r2r-chip { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: #2a313c; color: #8b949e; font-weight: 400; }
    .r2remote .r2r-chip.r2r-virtual { color: #3fb950; background: rgba(63,185,80,.12); }
    .r2remote .r2r-chip.r2r-real { color: #ffd60a; background: rgba(255,214,10,.12); }
    .r2remote .r2r-warn { display: none; font-size: 12px; color: #ffd60a; border: 1px solid rgba(255,214,10,.5); border-radius: 6px; padding: 5px 8px; margin: 0 0 8px; }
    .r2remote .r2r-pad.r2r-real .r2r-warn { display: block; }
    .r2remote .r2r-nav { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 8px; align-items: center; justify-items: center; }
    .r2remote .r2r-shoulders, .r2remote .r2r-faces { grid-column: 1 / -1; display: flex; gap: 10px; }
    .r2remote .r2r-b { position: relative; min-width: 44px; height: 34px; padding: 0 10px; border-radius: 8px; border: 1px solid #3a4250; background: #21262d;
      color: #e6edf3; font: 600 13px system-ui; cursor: pointer; user-select: none; touch-action: none; overflow: hidden; }
    .r2remote .r2r-b.r2r-round { width: 44px; height: 44px; min-width: 0; padding: 0; border-radius: 50%; }
    .r2remote .r2r-b.r2r-down { background: #30363d; transform: scale(.96); }
    .r2remote .r2r-b.r2r-hold, .r2remote .r2r-knob.r2r-hold { background: rgba(255,214,10,.18); border-color: #ffd60a; color: #ffd60a; box-shadow: 0 0 10px rgba(255,214,10,.45); }
    .r2remote .r2r-b.r2r-hold::after { content: 'HOLD'; position: absolute; left: 0; right: 0; bottom: 1px; font-size: 8px; letter-spacing: 1px; }
    .r2remote .r2r-b .r2r-fill { position: absolute; left: 0; bottom: 0; height: 3px; width: 0; background: #ffd60a; }
    .r2remote .r2r-b.r2r-down .r2r-fill { width: 100%; transition: width .6s linear; }
    .r2remote .r2r-b.r2r-sent { background: rgba(63,185,80,.25); border-color: #3fb950; }
    .r2remote .r2r-cross { color: #7aa2ff; } .r2remote .r2r-circle { color: #ff7b7b; } .r2remote .r2r-ps { font-size: 11px; }
    .r2remote .r2r-stickbox { width: 130px; height: 130px; border-radius: 50%; background: radial-gradient(#1c2128, #0f1318); border: 1px solid #3a4250; position: relative; touch-action: none; }
    .r2remote .r2r-knob { position: absolute; left: 50%; top: 50%; width: 54px; height: 54px; margin: -27px 0 0 -27px; border-radius: 50%;
      background: radial-gradient(circle at 40% 35%, #4b5563, #1f2937); border: 1px solid #6b7280; cursor: grab; display: grid; place-items: center;
      font: 600 10px system-ui; color: #8b949e; touch-action: none; }
    .r2remote .r2r-dpad { display: grid; grid-template-columns: repeat(3, 38px); grid-template-rows: repeat(3, 34px); gap: 3px; }
    .r2remote .r2r-dpad .r2r-b { min-width: 0; width: 38px; height: 34px; padding: 0; }
    .r2remote .r2r-help { margin: 0 14px 14px; font-size: 12px; color: #8b949e; }`;
  document.head.append(s);
}

const button = (b, label, cls = '') =>
  `<button type="button" class="r2r-b ${cls.split(' ').filter(Boolean).map((c) => `r2r-${c}`).join(' ')}" data-b="${b}">${label}<span class="r2r-fill"></span></button>`;
const navHtml = () => `
  <div class="r2r-shoulders">${button('L1', 'L1')}${button('L2', 'L2')}</div>
  <div class="r2r-stickbox"><div class="r2r-knob" data-b="L3">L3</div></div>
  <div class="r2r-dpad"><span></span>${button('UP', '<i class="fa-solid fa-caret-up"></i>')}<span></span>
    ${button('LEFT', '<i class="fa-solid fa-caret-left"></i>')}${button('PS', 'PS', 'round ps')}${button('RIGHT', '<i class="fa-solid fa-caret-right"></i>')}
    <span></span>${button('DOWN', '<i class="fa-solid fa-caret-down"></i>')}<span></span></div>
  <div class="r2r-faces">${button('CROSS', '✕', 'round cross')}${button('CIRCLE', '○', 'round circle')}</div>`;

function build() {
  addStyle();
  win = document.createElement('div');
  win.className = 'r2remote';
  win.hidden = true;
  win.innerHTML = `<div class="r2r-bar"><i class="fa-solid fa-gamepad"></i><b>Remote control · virtual Navs</b>
      <button class="r2r-x" type="button" title="Close: lets everything go"><i class="fa-solid fa-xmark"></i></button></div>
    <div class="r2r-pads">${['F', 'D'].map((p) => `<div class="r2r-pad" data-pad="${p}"><h4>${NAMES[p]} <span class="r2r-chip">…</span></h4>
      <div class="r2r-warn"><i class="fa-solid fa-triangle-exclamation"></i> A real ${p === 'F' ? 'foot' : 'dome'} Nav is connected: if someone moves it, it wins.</div>
      <div class="r2r-nav">${navHtml()}</div></div>`).join('')}</div>
    <p class="r2r-help"><i class="fa-solid fa-circle-info"></i> Click = press and release. <b>Hold a button 0.6 s</b> to keep it pressed (HOLD),
      then press another to send the combination. Click a held button, or press <b>Esc</b>, to let it go. Closing the window lets everything go.</p>`;
  document.body.append(win);
  win.querySelector('.r2r-x').addEventListener('click', close);
  win.querySelectorAll('.r2r-pad').forEach(wirePad);
  dragByBar();
}

// The first action on a slot with a real Nav connected asks first, once per opening of the window
async function allowed(p) {
  if (pads[p] !== 'real' || riskOk) return true;
  const ok = await confirmDialog({
    title: 'A real controller is connected', icon: 'fa-triangle-exclamation', ok: 'Send anyway',
    lines: [`The real ${p === 'F' ? 'foot' : 'dome'} Nav is on. What you send now acts on R2 as if pressed on it.`],
    warn: 'If someone moves the real controller, it wins and this window is ignored.',
  });
  if (ok) riskOk = true;
  return ok;
}

function render(padEl) {
  const p = padEl.dataset.pad;
  const held = pad[p].held();
  padEl.querySelectorAll('[data-b]').forEach((b) => b.classList.toggle('r2r-hold', held.has(b.dataset.b)));
}

function wirePad(padEl) {
  const p = padEl.dataset.pad;
  padEl.querySelectorAll('.r2r-b').forEach((el) => {
    const b = el.dataset.b;
    let pressed = false;
    el.addEventListener('pointerdown', async (e) => {
      e.preventDefault();
      if (!(await allowed(p))) return;
      pressed = true;
      el.setPointerCapture?.(e.pointerId);
      pad[p].down(b, performance.now());
      if (!pad[p].held().has(b)) el.classList.add('r2r-down');
    });
    const end = () => {
      if (!pressed) return;
      pressed = false;
      el.classList.remove('r2r-down');
      const { action } = pad[p].up(b, performance.now());
      if (action === 'tap' || action === 'combo') { el.classList.add('r2r-sent'); setTimeout(() => el.classList.remove('r2r-sent'), 300); }
      render(padEl);
      kick();
    };
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
  });

  // the stick: drag it; a click without moving is L3
  const box = padEl.querySelector('.r2r-stickbox'), knob = padEl.querySelector('.r2r-knob');
  let drag = false, moved = false;
  knob.addEventListener('pointerdown', async (e) => {
    e.preventDefault();
    if (!(await allowed(p))) return;
    drag = true; moved = false;
    knob.setPointerCapture?.(e.pointerId);
  });
  knob.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const r = box.getBoundingClientRect(), R = r.width / 2 - 27;
    let dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
    const d = Math.hypot(dx, dy);
    if (d < 4 && !moved) return;
    moved = true;
    if (d > R) { dx *= R / d; dy *= R / d; }
    knob.style.transform = `translate(${dx}px, ${dy}px)`;
    pad[p].stick(Math.round(128 + 127 * dx / R), Math.round(128 + 127 * dy / R));
    kick();
  });
  const stickEnd = () => {
    if (!drag) return;
    drag = false;
    knob.style.transform = '';
    if (!moved) { const t = performance.now(); pad[p].down('L3', t); pad[p].up('L3', t + 1); }
    else pad[p].stickUp();
    render(padEl);
    kick();
  };
  knob.addEventListener('pointerup', stickEnd);
  knob.addEventListener('pointercancel', stickEnd);
}

function send(p, s) {
  publish(TOPICS[p], 'std_msgs/msg/String', { data: JSON.stringify(s) });
}

// 20 times a second while a Nav is active; one rest packet when it stops; nothing at rest
function step() {
  const t = performance.now();
  let any = false;
  for (const p of ['F', 'D']) {
    if (pad[p].tick(t).length) render(win.querySelector(`.r2r-pad[data-pad="${p}"]`));
    const active = pad[p].active(t);
    if (active || wasActive[p]) send(p, pad[p].state(t));
    wasActive[p] = active;
    any = any || active;
  }
  if (!any) { clearInterval(timer); timer = null; }
}
function kick() { if (!timer && win && !win.hidden) timer = setInterval(step, SEND_MS); step(); }

function releaseAll() {
  for (const p of ['F', 'D']) {
    const had = pad[p].active(performance.now()) || wasActive[p];
    pad[p].reset();
    wasActive[p] = false;
    if (had) send(p, pad[p].state(0));
  }
  if (win) win.querySelectorAll('.r2r-pad').forEach(render);
  clearInterval(timer); timer = null;
}

function showStatus() {
  if (!win) return;
  for (const p of ['F', 'D']) {
    const el = win.querySelector(`.r2r-pad[data-pad="${p}"]`), chip = el.querySelector('.r2r-chip');
    let text = 'virtual', cls = 'virtual', off = false;
    if (!pads.mega) { text = 'no Mega'; cls = ''; off = true; }
    else if (pads.supported === false) { text = 'this firmware has no virtual Nav'; cls = ''; off = true; }
    else if (pads.supported === null) { text = 'asking the Mega…'; cls = ''; }
    else if (pads[p] === 'real') { text = 'real Nav connected'; cls = 'real'; }
    chip.textContent = text;
    chip.className = `r2r-chip ${cls ? `r2r-${cls}` : ''}`;
    el.classList.toggle('r2r-off', off);
    el.classList.toggle('r2r-real', pads[p] === 'real' && !off);
  }
}

function open() {
  if (!win) build();
  ensureConnected();
  win.hidden = false;
  btn.classList.add('open');
  riskOk = false;
  showStatus();
  channel?.postMessage({ open: me });     // one window at a time across tabs
}

function close() {
  releaseAll();
  if (win) win.hidden = true;
  btn?.classList.remove('open');
  riskOk = false;
}

function dragByBar() {
  const bar = win.querySelector('.r2r-bar');
  let on = false, sx, sy, ox, oy;
  bar.addEventListener('pointerdown', (e) => {
    if (e.target.closest('.r2r-x')) return;
    on = true;
    const r = win.getBoundingClientRect();
    sx = e.clientX; sy = e.clientY; ox = r.left; oy = r.top;
    win.style.transform = 'none'; win.style.left = `${ox}px`;
    bar.setPointerCapture(e.pointerId);
  });
  bar.addEventListener('pointermove', (e) => {
    if (!on) return;
    win.style.left = `${ox + e.clientX - sx}px`;
    win.style.top = `${Math.max(0, oy + e.clientY - sy)}px`;
  });
  bar.addEventListener('pointerup', () => { on = false; });
}

// --- page hooks ---------------------------------------------------------------------------
const nav = document.querySelector('nav.modes');
if (nav) {
  btn = document.createElement('a');
  btn.href = '#';
  btn.className = 'r2rbtn';
  btn.title = 'Two virtual PS3 Navs: try things without the real controllers (a real Nav in use always wins)';
  btn.innerHTML = '<i class="fa-solid fa-gamepad"></i>Remote';
  btn.addEventListener('click', (e) => { e.preventDefault(); if (win && !win.hidden) close(); else open(); });
  nav.append(btn);
}
subscribe('/mega/pads', 'std_msgs/msg/String', (m) => {
  try { pads = { ...pads, ...JSON.parse(m.data) }; } catch { return; }
  showStatus();
});
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || !win || win.hidden || document.querySelector('dialog[open]')) return;
  for (const p of ['F', 'D']) pad[p].esc();
  win.querySelectorAll('.r2r-pad').forEach(render);
  kick();
});
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') releaseAll(); });
window.addEventListener('pagehide', releaseAll);
channel?.addEventListener('message', (e) => { if (e.data?.open && e.data.open !== me && win && !win.hidden) close(); });
