// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> System, on the left (on top when narrow): the live strip (what the Pi finds: Mega, Pi, lidar, Pico board,
// cameras) and the mirror of the Pico board (its LEDs, its display pixel for pixel and its
// DISPLAY button, which works both ways). The Pico sends the mirror only while this tab asks
// for it (/pico/mirror_request every 2 s; the bridge renews MIR, the Pico stops 5 s after).
import { CONNECTOR_NAMES, LONG_PRESS_MS, fbPixels, isLive, ledsOf, pixelColor, pressKind, pwrLit, readingsByConnector, stripItems } from './boardmirror.js';
import { advertise, publish, subscribe } from './rosbridge.js';

const ASK_MS = 2000;
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const metres = (m) => (m === undefined ? '—' : m === Infinity ? 'nothing' : `${m.toFixed(2)} m`);

// The board drawn to scale from the PCB (80 x 90 mm, origin top left, KiCad coordinates in mm):
// each part sits where it is on the real board, the display at its real size.
const W = 80, H = 90;
const at = (x, y) => `left:${(x / W * 100).toFixed(3)}%;top:${(y / H * 100).toFixed(3)}%`;
const box = (x0, y0, x1, y1) => `${at(x0, y0)};width:${((x1 - x0) / W * 100).toFixed(3)}%;height:${((y1 - y0) / H * 100).toFixed(3)}%`;
const PITCH = 2.54;
// a pin header lying flat: first pin at (x, y), the others to the right
function header(x, y, pins, labels, above = false) {
  const x0 = x - PITCH / 2, x1 = x + (pins - 1) * PITCH + PITCH / 2;
  const holes = Array.from({ length: pins }, () => '<i></i>').join('');
  const text = labels.map((l) => `<span>${l}</span>`).join('');
  return `<div class="pcb-hdr" style="${box(x0, y - PITCH / 2, x1, y + PITCH / 2)}">${holes}</div>`
    + `<div class="pcb-pins" style="${above ? box(x0, y - PITCH / 2 - 2.6, x1, y - PITCH / 2 - 0.3) : box(x0, y + PITCH / 2 + 0.3, x1, y + PITCH / 2 + 2.6)}">${text}</div>`;
}
const US_Y = { US1: 12, US2: 22, US3: 32, US4: 42, US5: 52 };   // US1-5 at x 3, their LEDs at x 21
const VL_Y = { VL1: 12, VL2: 24, VL3: 39, VL4: 51 };            // VL1-4 at x 55, their LEDs at x 72.6
function boardHtml() {
  const us = Object.entries(US_Y).map(([c, y]) =>
    `<b class="pcb-name" style="${at(2, y - 4.4)}">${c}</b>`
    + `<span class="pcb-val" data-val="${c}" style="${at(9, y - 4.2)}">—</span>`
    + header(3, y, 4, ['5V', 'TR', 'EC', 'G'])
    + `<span class="pcb-led" data-led="${c}" style="${at(21, y)}"></span>`).join('');
  const vl = Object.entries(VL_Y).map(([c, y]) =>
    `<b class="pcb-name" style="${at(54, y - 4.4)}">${c}</b>`
    + `<span class="pcb-val" data-val="${c}" style="${at(60.5, y - 4.2)}">—</span>`
    + header(55, y, 6, ['3V3', 'G', 'SCL', 'SDA', '–', 'XS'])
    + `<span class="pcb-led" data-led="${c}" style="${at(72.6, y)}"></span>`).join('');
  const holes = [[3.5, 3.5], [76.5, 3.5], [3.5, 86.5], [76.5, 86.5]]
    .map(([x, y]) => `<span class="pcb-hole" style="${at(x, y)}"></span>`).join('');
  return holes + us + vl
    // the Pico 2 (21 x 51 mm) on its two sockets, USB at the top; its own LED next to the USB
    + `<div class="pcb-pico" style="${box(29.5, 2.1, 50.5, 53.1)}"><small>USB</small><span>Pico 2</span></div>`
    + `<span class="pcb-led pico" id="bv-picoled" style="${at(36.5, 5)}" title="The Pico's own LED: a slow blink = waiting for the Pi; on with a short blink every second = measuring"></span>`
    // power: terminal block, USB-C, PWR LED (D4)
    + `<div class="pcb-term" style="${box(1.5, 56.5, 11.5, 67.5)}"><i></i><i></i></div>`
    + `<b class="pcb-txt" style="${at(13, 58.6)}">+5V</b><b class="pcb-txt" style="${at(13, 63.8)}">GND</b>`
    + `<div class="pcb-usbc" style="${box(0, 71.5, 6, 79.5)}"></div><b class="pcb-txt" style="${at(2.5, 81)}">USB-C 5V</b>`
    + `<span class="pcb-led pwr" id="bv-pwr" style="${at(40.8, 59.5)}" title="PWR: the 5 V input (USB-C or terminal). Known only while an HC-SR04 answers"></span>`
    + `<b class="pcb-txt" style="${at(42.3, 58.6)}">PWR</b>`
    // QWIIC (J3) and EXP (J4)
    + `<div class="pcb-qwiic" style="${box(34.2, 62.8, 39.8, 66.2)}"></div><b class="pcb-txt" style="${at(41, 64)}">QWIIC</b>`
    + `<b class="pcb-txt" style="${at(26.7, 65.8)}">EXP</b>`
    + header(27.5, 69, 6, ['5V', 'G', '3V3', 'SCL', 'SDA', 'RUN'])
    // the logo and the DISPLAY button (SW1)
    + `<img class="pcb-logo" src="img/pcb-logo.png" alt="" style="${box(15.5, 72.5, 27.5, 84.5)}">`
    + `<b class="pcb-txt" style="${at(36.6, 75)}">SW1</b>`
    + `<button class="pcb-button" id="bv-btn" style="${box(35.2, 76.2, 40.8, 81.8)}" title="DISPLAY: click = a press; hold 3 s = off, like the real button"><i></i></button>`
    + `<b class="pcb-txt" style="${at(35.3, 82.8)}">DISPLAY</b>`
    + `<div class="pcb-hold" id="bv-hold" style="${box(33, 85.6, 43, 86.4)}"><i></i></div>`
    // the 0.96" SSD1306 module on J2: its board, its glass and the 21.74 x 10.86 mm screen
    + `<div class="pcb-oledmod" style="${box(45.5, 60.5, 73, 88.5)}"></div>`
    + header(54.69, 62, 4, ['G', 'V', 'SCL', 'SDA'], true)
    + `<div class="pcb-glass" style="${box(46.1, 67.2, 72.4, 84.4)}"></div>`
    + `<canvas id="bv-oled" width="128" height="64" style="${box(48.38, 70.4, 70.12, 81.26)}" title="The board's display, as it is now"></canvas>`
    + `<b class="pcb-txt foot" style="${at(13, 87.6)}">ROS2D2 · NandoMadrid · rev A</b>`;
}

export function createBoardView(root) {
  root.innerHTML = `
    <div class="strip" id="bv-strip"></div>
    <div class="pcb" id="bv-pcb">${boardHtml()}<div class="pcb-cover" id="bv-cover" hidden></div></div>`;
  const $ = (id) => root.querySelector(`#${id}`);
  const oled = $('bv-oled').getContext('2d');

  let visible = false, askTimer = null;
  let pico = null, picoAt = 0, mega = false, sensors = {}, lidarDevice = false, cameras = [], piTemp = null;
  const ranges = {}, rangeSubs = new Set();
  let mirror = { leds: null, fb: null, display_on: false, supported: null };

  // ---------- the strip ----------
  function showStrip() {
    const live = isLive(pico, picoAt, Date.now());
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
    const live = isLive(pico, picoAt, Date.now());
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
    showBoard();            // with no news from the Pi (bridge or socket gone) it goes grey, nothing stale
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
    // No "false" on leaving: another tab may still be looking. The bridge stops 5 s after the last request.
    hide() { visible = false; clearTimeout(askTimer); up(); },
  };
}
