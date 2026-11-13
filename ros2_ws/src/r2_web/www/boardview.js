// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> System, on top: the live strip (what the Pi finds: Mega, Pi, lidar, Pico board,
// cameras) and the mirror of the Pico board (its LEDs, its display pixel for pixel and its
// DISPLAY button, which works both ways). The Pico sends the mirror only while this tab asks
// for it (/pico/mirror_request every 2 s; the bridge renews MIR, the Pico stops 5 s after).
import { CONNECTOR_NAMES, LONG_PRESS_MS, fbPixels, ledsOf, pixelColor, pressKind, pwrLit, readingsByConnector, stripItems } from './boardmirror.js';
import { advertise, publish, subscribe } from './rosbridge.js';

const ASK_MS = 2000;
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const metres = (m) => (m === undefined ? '—' : m === Infinity ? 'nothing' : `${m.toFixed(2)} m`);

export function createBoardView(root) {
  root.innerHTML = `
    <div class="strip" id="bv-strip"></div>
    <div class="pcb" id="bv-pcb">
      <div class="pcb-col pcb-us">${CONNECTOR_NAMES.slice(4).map((c) => row(c, 'left')).join('')}</div>
      <div class="pcb-pico"><span class="pcb-led pico" id="bv-picoled" title="The Pico's own LED: a slow blink = waiting for the Pi; on with a short blink every second = measuring"></span><span>Pico 2</span></div>
      <div class="pcb-col pcb-vl">${CONNECTOR_NAMES.slice(0, 4).map((c) => row(c, 'right')).join('')}</div>
      <div class="pcb-ui">
        <canvas id="bv-oled" width="128" height="64" title="The board's display, as it is now"></canvas>
        <div class="pcb-btns">
          <span class="pcb-led pwr" id="bv-pwr" title="PWR: the 5 V input (USB-C or terminal). Known only while an HC-SR04 answers"></span><b>PWR</b>
          <button class="pcb-button" id="bv-btn" title="DISPLAY: click = a press; hold 3 s = off, like the real button"><i></i></button><b>DISPLAY</b>
        </div>
        <div class="pcb-hold" id="bv-hold"><i></i></div>
      </div>
      <div class="pcb-cover" id="bv-cover" hidden></div>
    </div>`;
  function row(c, side) {
    const led = `<span class="pcb-led" data-led="${c}"></span>`;
    const conn = `<span class="pcb-conn">${c}</span>`;
    const val = `<span class="pcb-val" data-val="${c}">—</span>`;
    return `<div class="pcb-row">${side === 'left' ? conn + led + val : val + led + conn}</div>`;
  }
  const $ = (id) => root.querySelector(`#${id}`);
  const oled = $('bv-oled').getContext('2d');

  let visible = false, askTimer = null;
  let pico = null, picoAt = 0, mega = false, sensors = {}, lidarDevice = false, cameras = [], piTemp = null;
  const ranges = {}, rangeSubs = new Set();
  let mirror = { leds: null, fb: null, display_on: false, supported: null };

  // ---------- the strip ----------
  function showStrip() {
    const live = pico && Date.now() - picoAt < 3000 && pico.connected;
    const items = stripItems({
      mega, pi: { temp_c: piTemp }, lidar: { ok: lidarDevice, detail: lidarDevice ? 'plugged in' : 'not connected' },
      pico: live ? pico : null, cameras,
    });
    const piece = (it) => {
      const cls = it.ok === null ? 'unknown' : it.ok ? 'ok' : 'off';
      return `<div class="piece ${cls}"><b>${esc(it.label)}</b><small>${it.ok ? '● ' : '○ '}${esc(it.detail)}</small></div>`;
    };
    const wire = (ok) => `<span class="wire ${ok ? 'ok' : 'off'}">USB</span>`;
    const [m, p, l, b, ...cams] = items;
    $('bv-strip').innerHTML = piece(m) + wire(m.ok) + piece(p) + wire(l.ok) + piece(l) + wire(b.ok) + piece(b) + cams.map(piece).join('');
  }

  // ---------- the board ----------
  function showBoard() {
    const live = pico && Date.now() - picoAt < 3000 && pico.connected;
    const leds = live ? ledsOf(mirror.leds) : null;
    const old = live && (pico.mirror_supported === false);
    const cover = !live ? 'Pico disconnected' : old ? 'Needs Pico firmware 0.3.0 (System → Pico firmware)' : '';
    $('bv-cover').hidden = !cover;
    $('bv-cover').textContent = cover;
    $('bv-pcb').classList.toggle('dead', !live || old);
    $('bv-btn').disabled = !live || old;
    for (const c of CONNECTOR_NAMES) root.querySelector(`[data-led="${c}"]`).classList.toggle('on', !!(leds && leds[c]));
    $('bv-picoled').classList.toggle('on', !!(leds && leds.PICO));
    const pwr = live ? pwrLit(pico) : null;
    $('bv-pwr').classList.toggle('on', pwr === true);
    $('bv-pwr').classList.toggle('unknown', pwr === null);
    const byConn = readingsByConnector(sensors, Object.fromEntries(Object.entries(ranges).map(([n, r]) => [n, Date.now() - r.at < 2000 ? r.range : undefined])));
    for (const c of CONNECTOR_NAMES) {
      const r = byConn[c];
      const st = r && live && pico.sensors ? pico.sensors[r.name] : null;
      root.querySelector(`[data-val="${c}"]`).textContent = !r ? '—' : st === 'ok' ? metres(r.m) : st === 'not_responding' ? 'no answer' : '—';
    }
    drawOled(live && !old ? fbPixels(mirror.fb) : null);
  }
  function drawOled(px) {
    oled.fillStyle = '#000';
    oled.fillRect(0, 0, 128, 64);
    if (!px) return;
    for (let y = 0; y < 64; y++) {
      oled.fillStyle = pixelColor(y);
      for (let x = 0; x < 128; x++) if (px[y * 128 + x]) oled.fillRect(x, y, 1, 1);
    }
  }

  // ---------- the DISPLAY button: down = a press (as the real one), held 3 s = long ----------
  let downAt = 0, holdTimer = null, holdAnim = null;
  const press = (kind) => publish('/pico/command', 'std_msgs/msg/String', { data: `PRESS ${kind}` });
  function down(e) {
    if ($('bv-btn').disabled || downAt) return;
    e.preventDefault();
    downAt = Date.now();
    $('bv-btn').classList.add('pressed');
    press('short');
    holdTimer = setTimeout(() => { if (pressKind(Date.now() - downAt) === 'long') press('long'); }, LONG_PRESS_MS);
    const bar = $('bv-hold');
    bar.classList.add('show');
    holdAnim = setInterval(() => { bar.firstElementChild.style.width = `${Math.min(100, (Date.now() - downAt) / LONG_PRESS_MS * 100)}%`; }, 50);
  }
  function up() {
    if (!downAt) return;
    downAt = 0;
    clearTimeout(holdTimer);
    clearInterval(holdAnim);
    $('bv-btn').classList.remove('pressed');
    $('bv-hold').classList.remove('show');
    $('bv-hold').firstElementChild.style.width = '0';
  }
  $('bv-btn').addEventListener('pointerdown', down);
  ['pointerup', 'pointerleave', 'pointercancel'].forEach((ev) => $('bv-btn').addEventListener(ev, up));
  function flashButton() {          // the real button was pressed (BTN)
    $('bv-btn').classList.add('pressed');
    setTimeout(() => { if (!downAt) $('bv-btn').classList.remove('pressed'); }, 250);
  }

  // ---------- sources ----------
  subscribe('/pico/mirror', 'std_msgs/msg/String', (m) => {
    let msg;
    try { msg = JSON.parse(m.data); } catch { return; }
    mirror = msg;
    if (msg.btn) flashButton();
    if (visible) showBoard();
  });
  subscribe('/mega/connected', 'std_msgs/msg/Bool', (m) => { mega = m.data; if (visible) showStrip(); });
  function subscribeRanges() {
    for (const [name, s] of Object.entries(sensors)) {
      if (!s || !s.pico || rangeSubs.has(name)) continue;
      rangeSubs.add(name);
      subscribe(`/range/${name}`, 'sensor_msgs/msg/Range', (m) => {     // rosbridge sends inf as null
        ranges[name] = { range: m.range == null ? Infinity : m.range, at: Date.now() };
      }, 200);
    }
  }
  async function loadSources() {
    try {
      const s = await (await fetch('api/sensors', { cache: 'no-store' })).json();
      sensors = s.sensors || {};
      lidarDevice = !!s.lidar_device;
      subscribeRanges();
    } catch { /* restarting */ }
    try {
      const c = await (await fetch('api/cameras', { cache: 'no-store' })).json();
      const found = new Set((c.detected || []).flatMap((d) => [d.path, d.id, d.device].map(String)));
      cameras = Object.entries(c.cameras || {}).map(([name, p]) => {
        const src = String(p.source ?? '');
        return { title: name, ok: src.includes('://') ? null : found.has(src) || src === 'auto' };
      });
    } catch { /* restarting */ }
    showStrip();
  }
  function ask() {
    if (!visible) return;
    publish('/pico/mirror_request', 'std_msgs/msg/Bool', { data: true });
    loadSources();
    askTimer = setTimeout(ask, ASK_MS);
  }

  return {
    pico(state) { pico = state; picoAt = Date.now(); if (visible) { showStrip(); showBoard(); } },
    pi(api) { piTemp = api && api.temp_c != null ? api.temp_c : piTemp; if (visible) showStrip(); },
    show() {
      visible = true;
      advertise('/pico/command', 'std_msgs/msg/String');     // ready before the first press
      clearTimeout(askTimer); ask(); showStrip(); showBoard();
    },
    hide() {
      if (visible) publish('/pico/mirror_request', 'std_msgs/msg/Bool', { data: false });
      visible = false; clearTimeout(askTimer); up();
    },
  };
}
