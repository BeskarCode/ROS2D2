// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The phone view (phone.html), in the spirit of MarcDuino's R2 Touch: drive R2 with two sticks,
// play its actions and switch its modes from the phone, through the console's virtual Navs.
//
// While the page is open and on screen it is the two Navs, on (padlink.js): a locked screen, a
// hidden tab or a closed page sends nothing, and the Mega stops by itself. The Pi keeps the sticks
// within remote.yaml's limit (20 % by default) and lets one device drive at a time. Actions and modes
// press their combination, as a controller would: the Pi never switches a mode on by itself.
import { createPadLink } from './padlink.js';
import { maskOf } from './padlogic.js';
import { actionGrid, modeButtons, stickValue } from './phonelogic.js';
import { call, connect, subscribe } from './rosbridge.js';
import { confirmDialog, promptDialog } from './dialog.js';
import { toast } from './savekey.js';

const $ = (id) => document.getElementById(id);
const link = createPadLink();
let remote = { stick_limit_pct: 20, guest: false, favorites: [] };
let modes = {}, sim = false, mode = '', auto = false, track = false, heartAt = 0;

// ---------- tabs ----------
let tab = 'drive';
function showTab(name) {
  if (remote.guest && name !== 'actions') name = 'actions';
  tab = name;
  for (const t of ['drive', 'actions', 'modes']) $(`tab-${t}`).hidden = t !== name;
  document.querySelectorAll('nav.ph-tabs button').forEach((b) => b.classList.toggle('on', b.dataset.tab === name));
}
document.querySelectorAll('nav.ph-tabs button').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.tab)));

// ---------- Drive: two sticks and each Nav's buttons, held while the finger is on them ----------
const BUTTONS = [['L1', 'L1'], ['L2', 'L2'], ['PS', 'PS'], ['CROSS', '✕', 'cross'], ['CIRCLE', '○', 'circle']];
const held = { F: new Set(), D: new Set() };
const pressBits = (p) => { link.pad[p].force(maskOf(held[p])); link.kick(); };

for (const p of ['F', 'D']) {
  const box = document.querySelector(`.ph-nav[data-pad="${p}"] .ph-btns`);
  for (const [name, label, cls] of BUTTONS) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = `ph-b ${cls || ''}`;
    b.textContent = label;
    let id = null;
    b.addEventListener('pointerdown', async (e) => {
      e.preventDefault();
      if (link.owner() === 'other' || !(await link.allowed(p))) return;
      id = e.pointerId;
      b.setPointerCapture?.(id);
      held[p].add(name);
      b.classList.add('down');
      pressBits(p);
    });
    const up = (e) => {
      if (id === null || e.pointerId !== id) return;
      id = null;
      held[p].delete(name);
      b.classList.remove('down');
      pressBits(p);
    };
    b.addEventListener('pointerup', up);
    b.addEventListener('pointercancel', up);
    box.append(b);
  }

  const stick = document.querySelector(`.ph-stick[data-pad="${p}"]`), knob = stick.querySelector('.ph-knob');
  let id = null;
  const move = (e) => {
    const r = stick.getBoundingClientRect(), R = r.width / 2 - knob.offsetWidth / 2;
    let dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
    const d = Math.hypot(dx, dy);
    if (d > R) { dx *= R / d; dy *= R / d; }
    knob.style.transform = `translate(${dx}px, ${dy}px)`;
    const v = stickValue(dx, dy, R);
    link.pad[p].stick(v.x, v.y);
    link.kick();
  };
  stick.addEventListener('pointerdown', async (e) => {
    e.preventDefault();
    if (id !== null || link.owner() === 'other' || !(await link.allowed(p))) return;
    id = e.pointerId;
    stick.setPointerCapture?.(id);
    move(e);
  });
  stick.addEventListener('pointermove', (e) => { if (e.pointerId === id) move(e); });
  const end = (e) => {
    if (e.pointerId !== id) return;
    id = null;
    knob.style.transform = '';
    link.pad[p].stickUp();               // back to the centre: the Mega stops that motor
    link.kick();
  };
  stick.addEventListener('pointerup', end);
  stick.addEventListener('pointercancel', end);
}

// ---------- Actions: favourites first, then every MarcDuino action ----------
const LONG_MS = 600;
function actionButton(a, isFav) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = `ph-act ${isFav ? 'fav' : ''}`;
  const name = document.createElement('b'), small = document.createElement('small');
  name.textContent = isFav ? a.name : a.what;
  small.textContent = isFav ? `${a.what} · ${a.label}` : a.label;
  b.append(name, small);
  let timer = null, long = false;
  b.addEventListener('pointerdown', () => { long = false; timer = setTimeout(() => { long = true; toggleFav(a, isFav); }, LONG_MS); });
  const cancel = () => clearTimeout(timer);
  b.addEventListener('pointerup', cancel);
  b.addEventListener('pointercancel', cancel);
  b.addEventListener('pointerleave', cancel);
  b.addEventListener('contextmenu', (e) => e.preventDefault());
  b.addEventListener('click', () => { if (!long) run(a, b); });
  return b;
}

function renderActions() {
  const g = actionGrid(remote.favorites, $('ph-find').value, modes);
  $('ph-favs').replaceChildren(...g.favs.map((a) => actionButton(a, true)));
  $('ph-favh').hidden = !g.favs.length;
  $('ph-acts').replaceChildren(...g.rest.map((a) => actionButton(a, false)));
  if (!g.rest.length) $('ph-acts').textContent = 'Nothing matches.';
  lock(link.busy());
}
$('ph-find').addEventListener('input', renderActions);

function lock(on) {
  const off = !link.pads().mega || link.pads().supported === false;
  document.querySelectorAll('.ph-act').forEach((b) => { if (!b.dataset.nocombo) b.disabled = on || off; });
}

// One combination pressed for you, in the order the Mega reads it, then the 1.2 s pause it needs
async function run(a, el, stat = $('ph-astat')) {
  if (link.busy() || link.owner() === 'other') return;
  lock(true);
  stat.textContent = `Sending ${a.label}…`;
  const done = await link.runShortcut({ combo: a.combo, label: a.label, what: a.what }, () => {
    el.classList.add('sent');
    stat.textContent = `Sent ${a.label}: ${a.what}.`;
  });
  el.classList.remove('sent');
  if (!done && stat.textContent.startsWith('Sending')) stat.textContent = '';
  lock(false);
}

async function toggleFav(a, isFav) {
  let favorites;
  if (isFav) {
    if (!(await confirmDialog({ title: 'Remove this favourite?', icon: 'fa-star', ok: 'Remove', lines: [`${a.name}: ${a.what}`] }))) return;
    favorites = remote.favorites.filter((f) => f.combo !== a.combo);
  } else {
    const name = await promptDialog({ title: 'New favourite', icon: 'fa-star', lines: [a.what, 'Its name on the button:'],
      value: a.what.slice(0, 20), max: 20, ok: 'Add' });
    if (!name) return;
    favorites = [...remote.favorites, { combo: a.combo, name }];
  }
  await saveRemote({ ...remote, favorites });
}

// remote.yaml as text (YAML takes JSON strings, so the names go in quoted and escaped)
function remoteYaml(r) {
  const favs = r.favorites.map((f) => `  - {combo: ${f.combo}, name: ${JSON.stringify(f.name)}}`).join('\n');
  return `# ROS2D2 Remote window and phone view (saved from the web console).\n` +
    `stick_limit_pct: ${r.stick_limit_pct}\nguest: ${r.guest}\nfavorites:${favs ? `\n${favs}` : ' []'}\n`;
}
async function saveRemote(r) {
  try {
    const res = await (await fetch('api/remote', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ yaml: remoteYaml(r) }) })).json();
    if (res.error) { toast(res.error, 'bad', 5000); return; }
    remote = r;
    toast('Favourites saved on R2', 'ok', 1800);
    renderActions();
  } catch { toast('Not saved: R2 does not answer', 'bad', 5000); }
}

// ---------- Modes ----------
function renderModes() {
  const box = $('ph-modes');
  box.replaceChildren(...modeButtons(modes, sim).map((m) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ph-act';
    const on = m.mode === 'tracking' ? track : auto && mode === m.mode;
    b.classList.toggle('on', on);
    const name = document.createElement('b'), small = document.createElement('small');
    name.textContent = m.label;
    if (m.combo) {
      small.textContent = m.mode === 'goto' ? 'simulator · to try the sensors’ layout' : (on ? 'tap to switch it off' : 'tap to switch it on');
      b.addEventListener('click', () => run({ combo: m.combo, label: m.label, what: `${m.label} on / off` }, b, $('ph-mstat')));
    } else {
      small.textContent = 'Give it a combination in Setup → Modes';
      b.disabled = true;
      b.dataset.nocombo = '1';
    }
    b.append(name, small);
    return b;
  }));
  lock(link.busy());
}

// ---------- STOP: everything let go, the mode and face tracking off ----------
$('ph-stop').addEventListener('click', async () => {
  for (const p of ['F', 'D']) held[p].clear();
  document.querySelectorAll('.ph-b.down').forEach((b) => b.classList.remove('down'));
  document.querySelectorAll('.ph-knob').forEach((k) => { k.style.transform = ''; });
  link.releaseAll();
  link.kick();                                       // still on: the Navs at rest
  await Promise.all([call('/r2/auto_mode/disable', 'std_srvs/srv/Trigger', {}),
    call('/r2/track_mode/disable', 'std_srvs/srv/Trigger', {})]);
  toast('Stopped: everything let go, mode and face tracking off', 'warn', 2500);
});

// ---------- status ----------
function showStatus() {
  const p = link.pads();
  const rosOk = Date.now() - heartAt < 3000;
  $('ph-ros').className = rosOk ? 'ok' : 'bad';
  $('ph-mega').className = p.mega ? 'ok' : 'bad';
  const other = link.owner() === 'other';
  document.body.classList.toggle('ph-other', other);
  $('ph-other').hidden = !other;
  const why = !p.mega ? 'No Mega: nothing to send to.' : p.supported === false ? 'This Mega firmware has no virtual Navs (ENABLE_VIRTUAL_PAD).' : '';
  $('ph-nomega').hidden = !why;
  $('ph-nomega').textContent = why;
  const lim = p.limit ?? remote.stick_limit_pct;
  $('ph-limit').textContent = `Speed limited to ${lim} % of the controller's.` +
    (p.F === 'real' || p.D === 'real' ? ' A real Nav is on: if someone moves it, it wins.' : '');
  lock(link.busy());
}
link.onPads(showStatus);
setInterval(showStatus, 1000);

// ---------- loading ----------
async function load() {
  try {
    const r = await (await fetch('api/remote', { cache: 'no-store' })).json();
    remote = r.remote;
  } catch { /* the defaults */ }
  try {
    const m = await (await fetch('api/modes', { cache: 'no-store' })).json();
    if (!m.error) modes = m.modes;
  } catch { /* none yet */ }
  document.querySelector('nav.ph-tabs button[data-tab="drive"]').hidden = remote.guest;
  document.querySelector('nav.ph-tabs button[data-tab="modes"]').hidden = remote.guest;
  showTab(remote.guest ? 'actions' : tab);
  renderActions();
  renderModes();
  showStatus();
}

connect(() => { load(); });
subscribe('/web/heartbeat', 'std_msgs/msg/String', () => { heartAt = Date.now(); });
subscribe('/r2/mode', 'std_msgs/msg/String', (m) => { mode = m.data; renderModes(); });
subscribe('/r2/auto_mode', 'std_msgs/msg/Bool', (m) => { auto = m.data; renderModes(); });
subscribe('/r2/track_mode', 'std_msgs/msg/Bool', (m) => { track = m.data; renderModes(); });
subscribe('/sim/world', 'std_msgs/msg/String', () => { if (!sim) { sim = true; renderModes(); } }, 5000);
subscribe('/r2/modes/reload', 'std_msgs/msg/Empty', () => load());
link.start();                                        // the two Navs are on while this page is on screen
