// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> System: the Pi's and the Pico's versions and, while "Telemetry" is on and the tab
// is open, how busy they are. The Pi's from GET api/system?telemetry=1 every 2 s; the Pico's
// from /pico/state, asked for with /pico/telemetry_request every 2 s (the bridge sends TM 0
// once the requests stop). Temperature and load show the ranges they move in.
import { CONNECTORS, OPTIONS, toYaml } from './boardform.js';
import { createBoardView } from './boardview.js';
import { publish, subscribe } from './rosbridge.js';
import {
  CPU_ZONES, PICO_TEMP_ZONES, PI_TEMP_ZONES, bytes, displayButtons, firmwareText, level, minMax, pct, throttleText,
  uptime, versionText, zone,
} from './systemfmt.js';

const $ = (id) => document.getElementById(id);
const POLL_MS = 2000;

export function createSystemTab() {
  const boardView = createBoardView($('sys-live'));
  let visible = false;
  let timer = null;
  let telemetry = false;
  try { telemetry = localStorage.getItem('r2web.telemetry') === '1'; } catch { /* private window */ }
  let pico = null, picoAt = 0;
  const seen = {};               // key -> { min, max } since the tab was first opened

  const stat = (label, value, cls = '', extra = '') =>
    `<div class="stat ${cls}"><div class="v">${value}</div><div class="l">${label}</div>${extra}</div>`;
  const bar = (used) => `<div class="sbar"><i style="width:${Math.max(0, Math.min(100, used * 100)).toFixed(1)}%"></i></div>`;

  // A value on its scale [lo, hi]: the zones coloured, the range seen shaded, a mark where it is
  function gauge(key, value, zones, lo, hi, unit) {
    seen[key] = minMax(seen[key], value);
    const z = zone(value, zones);
    const at = (v) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
    let from = lo;
    const bands = zones.map(([top, cls]) => {
      const a = at(from), b = at(Math.min(top, hi));
      from = top;
      return `<span class="z ${cls}" style="left:${a}%;width:${Math.max(0, b - a)}%"></span>`;
    }).join('');
    const s = seen[key];
    const range = s ? `<span class="seen" style="left:${at(s.min)}%;width:${Math.max(at(s.max) - at(s.min), 0.8)}%"></span>` : '';
    const mark = value == null ? '' : `<span class="mark" style="left:${at(value)}%"></span>`;
    const limits = zones.slice(0, -1).map(([top, , label]) => `${label} &lt; ${top}${unit}`).join(' · ');
    return { cls: z ? z.cls : '', html: `<div class="gauge">${bands}${range}${mark}</div>` +
      `<div class="l">${z ? `<b class="${z.cls}">${z.label}</b> · ` : ''}` +
      `${s ? `seen ${Math.round(s.min)}–${Math.round(s.max)}${unit}` : ''}</div><div class="l dim">${limits}</div>` };
  }

  function showPi(api) {
    $('sys-pi-version').textContent = versionText(api.version);
    const box = $('sys-pi');
    box.hidden = !telemetry;
    if (!telemetry || !api.disk) return;
    const d = api.disk, m = api.mem;
    const diskFree = d.total ? d.free / d.total : 1;
    const memFree = m.total ? m.available / m.total : 1;
    const cores = api.cpu ? api.cpu.slice(1).map((c, i) => `core ${i} ${pct(c)}`).join(' · ') : '';
    const cpu = gauge('pi-cpu', api.cpu ? api.cpu[0] : null, CPU_ZONES, 0, 100, ' %');
    const t = gauge('pi-temp', api.temp_c, PI_TEMP_ZONES, 30, 90, ' °C');
    box.innerHTML =
      stat('SD free', `${bytes(d.free)} <small>of ${bytes(d.total)}</small>`, level(diskFree, 0.15, 0.05), bar(1 - diskFree)) +
      stat('RAM available', `${bytes(m.available)} <small>of ${bytes(m.total)}</small>`, level(memFree, 0.20, 0.10), bar(1 - memFree)) +
      stat('CPU', api.cpu ? pct(api.cpu[0]) : '…', cpu.cls, `<div class="l">${cores}</div>${cpu.html}`) +
      stat('temperature', api.temp_c == null ? '–' : `${api.temp_c.toFixed(0)} °C`, t.cls, t.html);
    const warn = throttleText(api.throttled);
    $('sys-pi-warn').hidden = !warn.length;
    $('sys-pi-warn').innerHTML = warn.map((w) => `<i class="fa-solid fa-bolt"></i>${w}`).join(' · ');
  }

  // ---------- the Pico board ----------
  function showPico() {
    if (!visible) return;
    const fresh = pico && Date.now() - picoAt < 3000 && pico.connected;
    $('sys-pico-version').textContent = !fresh ? 'not connected'
      : `${pico.firmware || '?'}${pico.commit ? ` · ${pico.commit}` : ''}`;
    const box = $('sys-pico'), note = $('sys-pico-note');
    box.hidden = note.hidden = true;
    if (!telemetry || !fresh) return;
    if (!(pico.proto >= 2)) {
      note.hidden = false;
      note.textContent = 'Update the Pico firmware to see its telemetry.';
      return;
    }
    const tm = pico.telemetry;
    if (!tm) {
      note.hidden = false;
      note.textContent = 'Waiting for the Pico…';
      return;
    }
    const names = Object.keys(pico.sensors || {});
    const rps = tm.rps.map((n, i) => `${names[i] || `#${i}`} ${n}/s`).join(' · ');
    const c0 = gauge('pico-c0', tm.c0, CPU_ZONES, 0, 100, ' %');
    const c1 = gauge('pico-c1', tm.c1, CPU_ZONES, 0, 100, ' %');
    const bus = gauge('pico-bus', tm.bus, CPU_ZONES, 0, 100, ' %');
    const t = gauge('pico-temp', tm.temp_c, PICO_TEMP_ZONES, 10, 90, ' °C');
    box.hidden = false;
    box.innerHTML =
      stat('core 0 · measuring', pct(tm.c0), c0.cls, c0.html) +
      stat('core 1 · display and LEDs', pct(tm.c1), c1.cls, c1.html) +
      stat('I2C bus taken', pct(tm.bus), bus.cls,
        `<div class="l">${pct(tm.disp)} by the display · a VL waited up to ${tm.wait_ms} ms</div>${bus.html}`) +
      stat('chip temperature', `${tm.temp_c.toFixed(0)} °C`, t.cls, t.html) +
      stat('up', uptime(tm.up_s), '', `<div class="l">${rps || 'no sensors'}</div><div class="l dim">readings per second</div>`);
  }
  subscribe('/pico/state', 'std_msgs/msg/String', (m) => {
    try { pico = JSON.parse(m.data); picoAt = Date.now(); } catch { return; }
    boardView.pico(pico);
    showPico();
    boardEnabled();
  });

  // ---------- the Pico board's settings (pico_board.yaml) and actions ----------
  let board = null;
  const sel = (id, key) => {
    $(id).innerHTML = OPTIONS[key].map(([v, t]) => `<option value="${v}">${t}</option>`).join('');
  };
  sel('brd-timeout', 'display_timeout_s');
  sel('brd-bright', 'brightness');
  sel('brd-leds', 'leds');
  $('brd-screen').innerHTML = '<option value="all">every sensor</option>' +
    CONNECTORS.map((c) => `<option value="${c}">${c}</option>`).join('');
  $('brd-identify').innerHTML = CONNECTORS.map((c) => `<button data-c="${c}" title="Blink ${c}'s LED on the board for 5 s, to find the connector">${c}</button>`).join('');

  function boardEnabled() {
    const live = pico && Date.now() - picoAt < 3000 && pico.connected;
    const old = live && pico.settings_supported === false;
    const why = !live ? 'The Pico is not connected.' : old ? 'Update the Pico firmware to use this.' : '';
    $('brd-why').textContent = why;
    $('brd-why').hidden = !why;
    document.querySelectorAll('#sys-board button, #sys-board select').forEach((c) => {
      c.disabled = !!why && !(c.tagName === 'SELECT' && c.id !== 'brd-screen' && !old);   // settings can be saved while it is unplugged
    });
    // the display's buttons follow what the board says it shows (DS)
    const d = displayButtons(live ? pico.display : null);
    $('brd-on').classList.toggle('lit', d.on);
    $('brd-off').classList.toggle('lit', live && !d.on);
    if (d.screen && document.activeElement !== $('brd-screen')) $('brd-screen').value = d.screen;
  }
  async function loadBoard() {
    try { board = await (await fetch('api/pico_board', { cache: 'no-store' })).json(); } catch { return; }
    const s = board.settings || { display_timeout_s: 30, brightness: 2, leds: 'auto' };
    $('brd-timeout').value = s.display_timeout_s;
    $('brd-bright').value = s.brightness;
    $('brd-leds').value = s.leds;
    $('brd-file').textContent = board.error ? `${board.file}: ${board.error}` : board.file;
  }
  async function saveBoard() {
    const s = { display_timeout_s: Number($('brd-timeout').value), brightness: Number($('brd-bright').value), leds: $('brd-leds').value };
    let res;
    try { res = await (await fetch('api/pico_board', { method: 'POST', body: JSON.stringify({ yaml: toYaml(s) }) })).json(); } catch { res = { error: 'the Pi does not answer' }; }
    $('brd-file').textContent = res.error ? `Not saved: ${res.error}` : `Saved in ${res.file}: the Pico has it now.`;
  }
  ['brd-timeout', 'brd-bright', 'brd-leds'].forEach((id) => $(id).addEventListener('change', saveBoard));
  const command = (line) => publish('/pico/command', 'std_msgs/msg/String', { data: line });
  const displayOn = () => command($('brd-screen').value === 'all' ? 'DISP on' : `DISP on ${$('brd-screen').value}`);
  $('brd-on').addEventListener('click', displayOn);
  $('brd-screen').addEventListener('change', displayOn);      // picking a screen shows it at once
  $('brd-off').addEventListener('click', () => command('DISP off'));
  $('brd-identify').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) command(`ID ${b.dataset.c}`); });

  // ---------- the Pico firmware: check GitHub, build and flash it on the Pi ----------
  let fw = null, fwTimer = null;
  const BUSY = ['starting', 'pulling', 'compiling', 'releasing', 'flashing', 'waiting'];
  function showFirmware() {
    if (!fw) return;
    const busy = BUSY.includes(fw.state);
    const t = firmwareText(fw);
    $('fw-text').className = `status ${t.cls}`;
    $('fw-text').textContent = t.text;
    $('fw-step').hidden = !(busy || fw.state === 'done' || fw.state === 'failed');
    $('fw-step').className = `status ${fw.state === 'failed' ? 'bad' : fw.state === 'done' ? 'ok' : 'warn'}`;
    // text from the Pi and the Pico goes in as text, never as HTML; only the spinner is markup
    const step = $('fw-step');
    step.replaceChildren();
    if (busy) {
      const spin = document.createElement('i');
      spin.className = 'fa-solid fa-spinner fa-spin';
      step.append(spin);
    }
    step.append(busy ? `${fw.step_text}…` : fw.state === 'failed' ? `Failed: ${fw.error}`
      : fw.state === 'done' ? `Flashed: the Pico runs ${fw.pico_commit}` : '');
    $('fw-check').disabled = busy || !fw.installed;
    $('fw-flash').disabled = busy || !fw.installed;
    $('fw-retry').hidden = !fw.can_retry;
    $('fw-log').textContent = fw.log.join('\n');
    $('fw-logbox').hidden = !fw.log.length;
    clearTimeout(fwTimer);
    if (busy && visible) fwTimer = setTimeout(loadFirmware, 1000);
  }
  async function loadFirmware() {
    try { fw = await (await fetch('api/firmware', { cache: 'no-store' })).json(); } catch { return; }
    showFirmware();
  }
  async function fwPost(what) {
    let res;
    try { res = await (await fetch(`api/firmware/${what}`, { method: 'POST' })).json(); } catch { res = { error: 'the Pi does not answer' }; }
    if (res.error) {
      const why = { busy: 'Already busy flashing.', blocked: 'Stop the automatic mode first.', 'not installed': 'Run setup/install_pico_toolchain.sh on the Pi first.' };
      $('fw-step').hidden = false;
      $('fw-step').className = 'status bad';
      $('fw-step').textContent = why[res.error] || res.error;
      return;
    }
    if (what === 'check') { fw = res; showFirmware(); } else loadFirmware();
  }
  $('fw-check').addEventListener('click', () => { $('fw-text').textContent = 'Checking GitHub…'; fwPost('check'); });
  $('fw-flash').addEventListener('click', () => {
    const m = fw && fw.main;
    const what = m ? `${m.commit} (${m.subject})` : "main's latest";
    const other = fw && fw.compare === 'unpublished' ? '\n\nThe Pico runs a build that is not on GitHub: this replaces it with main.' : '';
    if (!window.confirm(`Flash the Pico with ${what}?\n\nThe Pi pulls it, builds it (a few minutes) and copies it; the Pico's sensors stop for a few seconds.${other}`)) return;
    fwPost('flash');
  });
  $('fw-retry').addEventListener('click', () => fwPost('retry'));

  // ---------- polling ----------
  async function poll() {
    timer = null;
    if (!visible) return;
    if (telemetry) publish('/pico/telemetry_request', 'std_msgs/msg/Bool', { data: true });
    try {
      const api = await (await fetch(`api/system${telemetry ? '?telemetry=1' : ''}`, { cache: 'no-store' })).json();
      showPi(api);
      boardView.pi(api);
    } catch { /* restarting */ }
    showPico();
    if (visible) timer = setTimeout(poll, telemetry ? POLL_MS : 5000);
  }
  const restart = () => { clearTimeout(timer); timer = null; poll(); };
  const stopPico = () => publish('/pico/telemetry_request', 'std_msgs/msg/Bool', { data: false });

  function setTelemetry(on) {
    telemetry = on;
    $('sys-telemetry').checked = on;
    try { localStorage.setItem('r2web.telemetry', on ? '1' : '0'); } catch { /* private window */ }
    if (!on) { $('sys-pi').hidden = true; $('sys-pi-warn').hidden = true; stopPico(); }
    restart();
  }
  $('sys-telemetry').addEventListener('change', (e) => setTelemetry(e.target.checked));
  $('sys-telemetry').checked = telemetry;

  return {
    show() { visible = true; restart(); loadBoard(); boardEnabled(); fwPost('check'); boardView.show(); },
    hide() { if (visible && telemetry) stopPico(); visible = false; clearTimeout(timer); timer = null; boardView.hide(); },
  };
}
