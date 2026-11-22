// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The Remote window: two virtual PS3 Navs (foot and dome) to try things at home without the real
// controllers. The Mega takes them exactly as real Navs (ROS:PAD, VirtualPad.h), and a real Nav in
// use always wins. Each page imports this: it adds a "Remote" button to the header.
//
// Like a real Nav, each one's state goes out all the time while the window is open (20 a second,
// at rest too): the Mega takes 300 ms of silence as "controller lost" and switches tracking and the
// modes off. So closing the window, leaving the page or hiding the tab is switching the controllers
// off: everything is let go and the Mega stops the motors by itself. One window at a time across tabs;
// the sending itself (and the one-page-at-a-time rule with the phone view) is padlink.js.
import { shortcutList } from './shortcuts.js';
import { createPadLink } from './padlink.js';
import { closeWarning } from './padlogic.js';
import { confirmDialog } from './dialog.js';
import { subscribe } from './rosbridge.js';

const NAMES = { F: 'Foot Nav', D: 'Dome Nav' };

let win = null, btn = null;
const link = createPadLink({ onTick: markHolds });
const pad = link.pad;
const channel = 'BroadcastChannel' in window ? new BroadcastChannel('r2-remote') : null;
const me = Math.random().toString(36).slice(2);
const running = { track: false, auto: false, mode: '' };     // what closing the window would switch off
subscribe('/r2/track_mode', 'std_msgs/msg/Bool', (m) => { running.track = m.data; });
subscribe('/r2/auto_mode', 'std_msgs/msg/Bool', (m) => { running.auto = m.data; });
subscribe('/r2/mode', 'std_msgs/msg/String', (m) => { running.mode = m.data; });

function addStyle() {
  const s = document.createElement('style');
  s.textContent = `
    .r2rbtn.open { color: #fff !important; background: var(--blue) !important; border-color: var(--blue) !important; }
    .r2remote { position: fixed; left: 50%; top: 110px; transform: translateX(-50%); width: min(760px, calc(100vw - 32px)); z-index: 8000;
      background: var(--panel); color: var(--text); border: 1px solid var(--line2); border-radius: 12px; box-shadow: 0 16px 48px rgba(0,0,0,.6);
      font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
    .r2remote[hidden] { display: none; }
    .r2remote .r2r-bar { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid var(--line); cursor: move; user-select: none; touch-action: none; }
    .r2remote .r2r-bar b { font-size: var(--fs); letter-spacing: 1px; text-transform: uppercase; color: var(--muted); }
    .r2remote .r2r-bar .r2r-x { margin-left: auto; background: none; border: none; color: var(--muted); font-size: 16px; cursor: pointer; }
    .r2remote .r2r-pads { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; padding: 14px; }
    @media (max-width: 640px) { .r2remote .r2r-pads { grid-template-columns: 1fr; } }
    .r2remote .r2r-pad { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px 14px; }
    .r2remote .r2r-pad.r2r-off { opacity: .5; pointer-events: none; }
    .r2remote h4 { margin: 0 0 6px; display: flex; align-items: center; gap: 8px; font-size: var(--fs); }
    .r2remote .r2r-chip { font-size: var(--fs-s); padding: 1px 8px; border-radius: 999px; background: var(--line); color: var(--muted); font-weight: 400; }
    .r2remote .r2r-chip.r2r-virtual { color: var(--green); background: rgba(63,185,80,.12); }
    .r2remote .r2r-chip.r2r-real { color: #ffd60a; background: rgba(255,214,10,.12); }
    .r2remote .r2r-warn { display: none; font-size: var(--fs-s); color: #ffd60a; border: 1px solid rgba(255,214,10,.5); border-radius: 6px; padding: 5px 8px; margin: 0 0 8px; }
    .r2remote .r2r-pad.r2r-real .r2r-warn { display: block; }
    .r2remote .r2r-nav { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 8px; align-items: center; justify-items: center; }
    .r2remote .r2r-shoulders, .r2remote .r2r-faces { grid-column: 1 / -1; display: flex; gap: 10px; }
    .r2remote .r2r-b { position: relative; min-width: 44px; height: 34px; padding: 0 10px; border-radius: 8px; border: 1px solid var(--line2); background: #21262d;
      color: var(--text); font: 600 13px system-ui; cursor: pointer; user-select: none; touch-action: none; overflow: hidden; }
    .r2remote .r2r-b.r2r-round { width: 44px; height: 44px; min-width: 0; padding: 0; border-radius: 50%; }
    .r2remote .r2r-b.r2r-down { background: #30363d; transform: scale(.96); }
    .r2remote .r2r-b.r2r-hold, .r2remote .r2r-knob.r2r-hold { background: rgba(255,214,10,.18); border-color: #ffd60a; color: #ffd60a; box-shadow: 0 0 10px rgba(255,214,10,.45); }
    .r2remote .r2r-b.r2r-hold::after { content: 'HOLD'; position: absolute; left: 0; right: 0; bottom: 1px; font-size: 8px; letter-spacing: 1px; }
    .r2remote .r2r-b .r2r-fill { position: absolute; left: 0; bottom: 0; height: 3px; width: 0; background: #ffd60a; }
    .r2remote .r2r-b.r2r-down .r2r-fill { width: 100%; transition: width .6s linear; }
    .r2remote .r2r-b.r2r-sent { background: rgba(63,185,80,.25); border-color: var(--green); }
    .r2remote .r2r-cross { color: #7aa2ff; } .r2remote .r2r-circle { color: #ff7b7b; } .r2remote .r2r-ps { font-size: var(--fs-s); }
    .r2remote .r2r-stickbox { width: 130px; height: 130px; border-radius: 50%; background: radial-gradient(#1c2128, #0f1318); border: 1px solid var(--line2); position: relative; touch-action: none; }
    .r2remote .r2r-knob { position: absolute; left: 50%; top: 50%; width: 54px; height: 54px; margin: -27px 0 0 -27px; border-radius: 50%;
      background: radial-gradient(circle at 40% 35%, #4b5563, #1f2937); border: 1px solid #6b7280; cursor: grab; display: grid; place-items: center;
      font: 600 10px system-ui; color: var(--muted); touch-action: none; }
    .r2remote .r2r-dpad { display: grid; grid-template-columns: repeat(3, 38px); grid-template-rows: repeat(3, 34px); gap: 3px; }
    .r2remote .r2r-dpad .r2r-b { min-width: 0; width: 38px; height: 34px; padding: 0; }
    .r2remote .r2r-help { margin: 0 14px 14px; font-size: var(--fs-s); color: var(--muted); }
    .r2remote .r2r-other { display: none; margin: 8px 14px 0; padding: 6px 10px; border-radius: 6px; font-size: var(--fs-s);
      color: var(--amber); border: 1px solid var(--amber); }
    .r2remote.r2r-isother .r2r-other { display: block; }
    .r2remote.r2r-isother .r2r-pads, .r2remote.r2r-isother .r2r-slist { opacity: .45; pointer-events: none; }
    .r2remote .r2r-tabs { display: flex; gap: 4px; padding: 8px 14px 0; }
    .r2remote .r2r-tabs button { background: transparent; border: 1px solid transparent; color: var(--muted); border-radius: 6px;
      padding: 5px 12px; font: inherit; font-size: var(--fs); cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
    .r2remote .r2r-tabs button:hover { background: var(--line); color: var(--text); }
    .r2remote .r2r-tabs button.r2r-on { background: var(--line); border-color: var(--line2); color: var(--text); }
    .r2remote .r2r-short { padding: 10px 14px 14px; }
    .r2remote .r2r-sfind { width: 100%; box-sizing: border-box; margin: 0 0 8px; background: var(--bg); color: var(--text);
      border: 1px solid var(--line2); border-radius: 6px; padding: 6px 10px; font: inherit; font-size: var(--fs); }
    .r2remote .r2r-slist { max-height: min(52vh, 420px); overflow: auto; display: grid; gap: 4px; }
    .r2remote .r2r-sgroup { font-size: var(--fs-s); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 8px 0 2px; }
    .r2remote .r2r-srow { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: center; text-align: left;
      background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; color: var(--text); font: inherit;
      font-size: var(--fs); cursor: pointer; }
    .r2remote .r2r-srow:hover:not(:disabled) { border-color: var(--blue); }
    .r2remote .r2r-srow:disabled { opacity: .5; cursor: default; }
    .r2remote .r2r-srow.r2r-sent { border-color: var(--green); background: rgba(63,185,80,.12); }
    .r2remote .r2r-srow .r2r-keys { color: var(--muted); font-size: var(--fs-s); white-space: nowrap; }
    .r2remote .r2r-sstat { min-height: 1.3em; margin: 8px 0 0; font-size: var(--fs-s); color: var(--muted); }`;
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
    <div class="r2r-tabs"><button type="button" class="r2r-on" data-tab="pads"><i class="fa-solid fa-gamepad"></i>Controllers</button>
      <button type="button" data-tab="short" title="Every combination that does something, sent for you with one click"><i class="fa-solid fa-bolt"></i>Shortcuts</button></div>
    <p class="r2r-other"><i class="fa-solid fa-mobile-screen"></i> Another device is driving R2 (the phone view, or a Remote
      in another browser). This window takes over when it has been quiet for a second.</p>
    <div class="r2r-tab" data-tab="pads">
    <div class="r2r-pads">${['F', 'D'].map((p) => `<div class="r2r-pad" data-pad="${p}"><h4>${NAMES[p]} <span class="r2r-chip">…</span></h4>
      <div class="r2r-warn"><i class="fa-solid fa-triangle-exclamation"></i> A real ${p === 'F' ? 'foot' : 'dome'} Nav is connected: if someone moves it, it wins.</div>
      <div class="r2r-nav">${navHtml()}</div></div>`).join('')}</div>
    <p class="r2r-help"><i class="fa-solid fa-circle-info"></i> Click = press and release. <b>Hold a button 0.6 s</b> to keep it pressed (HOLD),
      then press another to send the combination. Click a held button, or press <b>Esc</b>, to let it go. Closing the window lets everything go.</p>
    </div>
    <div class="r2r-tab r2r-short" data-tab="short" hidden>
      <input class="r2r-sfind" type="search" placeholder="Find: holo, song, panel, Patrol…" aria-label="Find a shortcut">
      <div class="r2r-slist"></div>
      <p class="r2r-sstat"></p>
      <p class="r2r-help" style="margin:4px 0 0"><i class="fa-solid fa-circle-info"></i> One click presses the whole combination on the two Navs, in the
        order the Mega needs. The actions are ShadowMD Lite's default MarcDuino map; a combination given to a mode (Setup → Modes) starts the
        mode instead. Free combinations are not listed.</p>
    </div>`;
  document.body.append(win);
  win.querySelector('.r2r-x').addEventListener('click', closeAsked);
  win.querySelectorAll('.r2r-pad').forEach(wirePad);
  win.querySelectorAll('.r2r-tabs button').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.tab)));
  win.querySelector('.r2r-sfind').addEventListener('input', renderShortcuts);
  dragByBar();
}

const allowed = (p) => link.allowed(p);
const kick = () => link.kick();

// A button held long enough became HOLD while still pressed: mark it now (padlink's tick)
function markHolds(p, names) {
  if (!win) return;
  const padEl = win.querySelector(`.r2r-pad[data-pad="${p}"]`);
  names.forEach((b) => padEl.querySelector(`[data-b="${b}"]`)?.classList.remove('r2r-down'));
  render(padEl);
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
      kick();                       // tick while pressed: the HOLD lights up at 0.6 s, before letting go
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

// --- Shortcuts -------------------------------------------------------------------------------
let shortcuts = shortcutList({});

function showTab(name) {
  win.querySelectorAll('.r2r-tabs button').forEach((b) => b.classList.toggle('r2r-on', b.dataset.tab === name));
  win.querySelectorAll('.r2r-tab').forEach((t) => { t.hidden = t.dataset.tab !== name; });
  if (name === 'short') loadShortcuts();
}

async function loadShortcuts() {
  try {
    const p = await (await fetch('api/modes', { cache: 'no-store' })).json();
    if (!p.error) shortcuts = shortcutList(p.modes || {});
  } catch { /* restarting: the MarcDuino ones still work */ }
  renderShortcuts();
}

const GROUPS = { mode: 'Automatic modes', tracking: 'Face tracking', marcduino: 'MarcDuino actions' };

function renderShortcuts() {
  const list = win.querySelector('.r2r-slist');
  const q = win.querySelector('.r2r-sfind').value.trim().toLowerCase();
  const pads = link.pads();
  const off = !pads.mega || pads.supported === false;
  list.replaceChildren();
  let group = null;
  for (const sc of shortcuts) {
    if (q && !`${sc.what} ${sc.label}`.toLowerCase().includes(q)) continue;
    if (sc.kind !== group) {
      group = sc.kind;
      const h = document.createElement('div');
      h.className = 'r2r-sgroup';
      h.textContent = GROUPS[group];
      list.append(h);
    }
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'r2r-srow';
    row.disabled = off || link.busy();
    row.dataset.combo = sc.combo;
    const what = document.createElement('span'), keys = document.createElement('span');
    what.textContent = sc.what;
    keys.className = 'r2r-keys';
    keys.textContent = sc.label;
    row.append(what, keys);
    row.addEventListener('click', () => runShortcut(sc, row));
    list.append(row);
  }
  if (!list.children.length) list.textContent = 'Nothing matches.';
  const stat = win.querySelector('.r2r-sstat');
  if (off && !link.busy()) stat.textContent = !pads.mega ? 'No Mega: nothing to send to.' : 'This Mega firmware has no virtual Nav.';
}

function lockShortcuts(on) {
  const pads = link.pads();
  win.querySelectorAll('.r2r-srow').forEach((r) => { r.disabled = on || !pads.mega || pads.supported === false; });
}

async function runShortcut(sc, row) {
  if (link.busy()) return;
  const stat = win.querySelector('.r2r-sstat');
  lockShortcuts(true);
  stat.textContent = `Sending ${sc.label}…`;
  const done = await link.runShortcut(sc, () => {
    row.classList.add('r2r-sent');
    stat.textContent = `Sent ${sc.label}: ${sc.what}.`;
  });
  row.classList.remove('r2r-sent');
  if (!done && stat.textContent.startsWith('Sending')) stat.textContent = '';
  lockShortcuts(false);
}

function showStatus() {
  if (!win) return;
  const pads = link.pads();
  win.classList.toggle('r2r-isother', link.owner() === 'other');
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
  if (!win.querySelector('.r2r-tab[data-tab="short"]').hidden) renderShortcuts();
}

function open() {
  if (!win) build();
  win.hidden = false;
  btn.classList.add('open');
  link.start();                     // the two Navs are "switched on" while the window is open
  showStatus();
  channel?.postMessage({ open: me });     // one window at a time across tabs
}

// Closing by hand (the X or the Remote button): if a mode or face tracking runs on a virtual Nav,
// say that closing switches it off (the Mega takes the quiet Nav as a lost controller) and ask.
async function closeAsked() {
  const off = closeWarning(link.pads(), running);
  if (off) {
    const ok = await confirmDialog({
      title: 'Close the Remote?', icon: 'fa-triangle-exclamation', ok: 'Close',
      lines: [`It runs on the virtual Navs: ${off.join(' and ')}.`,
        'Closing the window switches the virtual Navs off, and the Mega switches that off with them, as when a real controller is lost.'],
      warn: 'Keep the window open (it can be dragged aside) while it should keep going.',
    });
    if (!ok) return;
  }
  close();
}

function close() {
  link.stop();
  if (win) {
    win.hidden = true;
    win.querySelectorAll('.r2r-pad').forEach(render);
    win.querySelectorAll('.r2r-srow.r2r-sent').forEach((r) => r.classList.remove('r2r-sent'));
  }
  btn?.classList.remove('open');
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
  btn.addEventListener('click', (e) => { e.preventDefault(); if (win && !win.hidden) closeAsked(); else open(); });
  nav.append(btn);
}
link.onPads(() => showStatus());
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || !win || win.hidden || document.querySelector('dialog[open]')) return;
  for (const p of ['F', 'D']) pad[p].esc();
  win.querySelectorAll('.r2r-pad').forEach(render);
  kick();
});
channel?.addEventListener('message', (e) => { if (e.data?.open && e.data.open !== me && win && !win.hidden) close(); });
