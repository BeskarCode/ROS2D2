// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> System: the Pi's and the Pico's versions and, while "Telemetry" is on and the tab
// is open, how busy they are, every 1-30 s (picked next to the switch). The Pi's from GET
// api/system?telemetry=1; the dome cameras' from GET api/domecams (the Pi asks each one); the
// Pico's from /pico/state, asked for with /pico/telemetry_request every 2 s whatever the period
// (the bridge sends TM 0 once the requests stop). Temperature and load show the ranges they move in.
import { CONNECTORS, OPTIONS, toYaml } from './boardform.js';
import { createBoardView } from './boardview.js';
import { publish, subscribe } from './rosbridge.js';
import { confirmDialog } from './dialog.js';
import {
  CAM_TEMP_ZONES, RSSI_ZONES, TELEMETRY_PERIODS, camLines, flashProgress, wifiRows, CPU_ZONES, PICO_TEMP_ZONES, PI_TEMP_ZONES, bytes, ringBands, ringFill, displayButtons, firmwareText, minMax, pct, throttleText,
  uptime, versionText, zone,
} from './systemfmt.js';

const $ = (id) => document.getElementById(id);
const PICO_ASK_MS = 2000;   // the bridge stops the Pico's telemetry 5 s after the last ask

export function createSystemTab() {
  const boardView = createBoardView($('sys-live'));
  let visible = false;
  let timer = null;
  let telemetry = false;
  let period = 2000;
  try {
    telemetry = localStorage.getItem('r2web.telemetry') === '1';
    const p = Number(localStorage.getItem('r2web.telemetry_ms'));
    if (TELEMETRY_PERIODS.includes(p)) period = p;
  } catch { /* private window */ }
  let pico = null, picoAt = 0;
  const seen = {};               // key -> { min, max } since the tab was first opened

  // A ring gauge: the zones' colour ranges as a faint track, the value filled in its zone's colour,
  // the number in the middle; the range seen and the limits on hover.
  const SWEEP = 270, R = 38, C = 48;
  const pt = (f) => {
    const a = ((135 + f * SWEEP) * Math.PI) / 180;
    return `${(C + R * Math.cos(a)).toFixed(2)} ${(C + R * Math.sin(a)).toFixed(2)}`;
  };
  const arc = (a, b) => `M${pt(a)} A${R} ${R} 0 ${(b - a) * SWEEP > 180 ? 1 : 0} 1 ${pt(b)}`;
  function ring(key, label, text, value, zones, lo, hi, unit, sub = '', more = '') {
    seen[key] = minMax(seen[key], value);
    const z = zone(value, zones);
    const f = ringFill(value, lo, hi);
    const bands = ringBands(zones, lo, hi).map((b) => `<path class="band ${b.cls}" d="${arc(b.from, b.to)}"/>`).join('');
    const fill = f > 0.002 ? `<path class="fill ${z ? z.cls : ''}" d="${arc(0, f)}"/>` : '';
    const s = seen[key];
    const limits = zones.slice(0, -1).map(([top, , l]) => `${l} < ${top}${unit}`).join(' · ');
    const tip = `${label}${z ? `: ${z.label}` : ''}${s ? ` · seen ${Math.round(s.min)}–${Math.round(s.max)}${unit}` : ''}${limits ? ` · ${limits}` : ''}${more ? ` · ${more}` : ''}`;
    return `<div class="ring ${z ? z.cls : ''}" title="${tip}"><svg viewBox="0 0 96 96">${bands}${fill}` +
      `<text x="48" y="54" text-anchor="middle">${text}</text></svg><div class="l">${label}</div>` +
      `${sub ? `<div class="l dim">${sub}</div>` : ''}</div>`;
  }
  const USED_SD = [[85, 'ok', 'normal'], [95, 'warn', 'filling up'], [Infinity, 'bad', 'almost full']];
  const USED_RAM = [[80, 'ok', 'normal'], [90, 'warn', 'tight'], [Infinity, 'bad', 'almost full']];

  // Telemetry off (or the source gone): the rings keep their last values, greyed, instead of vanishing
  function stale(box) {
    box.classList.add('stale');
    box.hidden = !box.innerHTML.trim();
  }

  function showPi(api) {
    $('sys-pi-version').textContent = versionText(api.version);
    const box = $('sys-pi');
    if (!telemetry || !api.disk) { stale(box); return; }
    box.hidden = false;
    const d = api.disk, m = api.mem;
    const diskFree = d.total ? d.free / d.total : 1;
    const memFree = m.total ? m.available / m.total : 1;
    const cores = api.cpu && api.cpu.length > 1 ? `cores ${api.cpu.slice(1).map((c) => Math.round(c)).join(' · ')} %` : '';
    box.className = 'rings';
    box.innerHTML =
      ring('pi-sd', 'SD free', bytes(d.free), (1 - diskFree) * 100, USED_SD, 0, 100, ' % used', `of ${bytes(d.total)}`) +
      ring('pi-ram', 'RAM free', bytes(m.available), (1 - memFree) * 100, USED_RAM, 0, 100, ' % used', `of ${bytes(m.total)}`) +
      ring('pi-cpu', 'CPU', api.cpu ? pct(api.cpu[0]) : '…', api.cpu ? api.cpu[0] : null, CPU_ZONES, 0, 100, ' %', cores) +
      ring('pi-temp', 'temperature', api.temp_c == null ? '–' : `${api.temp_c.toFixed(0)} °C`, api.temp_c, PI_TEMP_ZONES, 30, 90, ' °C');
    const warn = throttleText(api.throttled);
    $('sys-pi-warn').hidden = !warn.length;
    $('sys-pi-warn').innerHTML = warn.map((w) => `<i class="fa-solid fa-bolt"></i>${w}`).join(' · ');
  }

  // ---------- the network dome cameras (GET api/domecams: the Pi asks each one) ----------
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const lastCam = {};      // name -> its last rings and lines, shown grey when it stops answering
  function showCams(api) {
    const box = $('sys-cams');
    if (!telemetry || !api) {
      box.querySelectorAll('.camtm').forEach((el) => el.classList.add('stale'));
      $('sys-cams-h').hidden = box.hidden = !box.innerHTML.trim();
      return;
    }
    const cams = api.cameras || [];
    box.hidden = $('sys-cams-h').hidden = !cams.length;
    if (box.hidden) return;
    box.innerHTML = cams.map((c) => {
      const head = `<h4><i class="fa-solid fa-video"></i> ${esc(c.name)} <span class="sub">${esc(c.url)}</span></h4>`;
      if (!c.status) {
        return `<div class="camtm stale">${head}<p class="status bad">No answer: ${esc(c.error || '?')}</p>${lastCam[c.name] || ''}</div>`;
      }
      const s = c.status;
      const cpu = Array.isArray(s.cpu) ? s.cpu : null;
      const rssi = Number.isFinite(s.rssi) && s.rssi < 0 ? -s.rssi : null;
      const k = `cam-${c.name}`;
      const rings =
        ring(`${k}-temp`, 'chip temperature', s.temp_c == null ? '–' : `${s.temp_c.toFixed(0)} °C`, s.temp_c, CAM_TEMP_ZONES, 20, 90, ' °C') +
        ring(`${k}-c0`, 'core 0 · WiFi, web', cpu ? pct(cpu[0]) : '–', cpu ? cpu[0] : null, CPU_ZONES, 0, 100, ' %') +
        ring(`${k}-c1`, 'core 1 · finder', cpu ? pct(cpu[1]) : '–', cpu ? cpu[1] : null, CPU_ZONES, 0, 100, ' %') +
        ring(`${k}-rssi`, 'WiFi signal', rssi == null ? '–' : `${s.rssi} dBm`, rssi, RSSI_ZONES, 20, 95, ' (-dBm)');
      const lines = camLines(s, c.ms).map(([l, v, cls]) => `<dt>${esc(l)}</dt><dd class="${cls}">${esc(v)}</dd>`).join('');
      const old = s.temp_c === undefined ? '<p class="help">Update this camera&#39;s firmware to see its temperature, load and reboots.</p>' : '';
      lastCam[c.name] = `<div class="rings">${rings}</div>${old}<dl>${lines}</dl>`;
      return `<div class="camtm">${head}${lastCam[c.name]}</div>`;
    }).join('');
  }

  // ---------- R2's own WiFi: the access point's channel (GET api/wifi, POST survey / move) ----------
  function showWifi(look, what) {
    const rows = wifiRows(look);
    $('wifi-bars').innerHTML = rows.map((r) => `<div class="wifibar ${r.cls}${r.current ? ' current' : ''}">
      <b>channel ${r.ch}${r.current ? ' ●' : ''}</b><span class="track"><i style="width:${r.pct}%"></i></span>
      <span>${r.dbm <= -99 ? 'clear' : `${Math.round(r.dbm)} dBm`}</span></div>`).join('');
    const t = $('wifi-text');
    if (!look) { t.className = 'status warn'; t.textContent = what; return; }
    const best = rows.find((r) => r.best);
    t.className = `status ${best && !best.current ? 'warn' : ''}`;
    t.textContent = `On channel ${look.channel}${what ? ` · ${what}` : ''}` +
      (best && !best.current ? ` · channel ${best.ch} is quieter now: Move to the quietest` : '');
  }
  async function loadWifi() {
    try {
      const r = await (await fetch('api/wifi', { cache: 'no-store' })).json();
      showWifi(r.pick, r.pick ? 'picked when the access point started' : (r.error || 'unknown'));
    } catch { showWifi(null, 'the Pi does not answer'); }
  }
  $('wifi-check').addEventListener('click', async () => {
    $('wifi-text').textContent = 'Looking at the channels…';
    try {
      const r = await (await fetch('api/wifi/survey', { method: 'POST' })).json();
      showWifi(r.survey, r.error ? '' : 'just now');
      if (r.error) showWifi(null, r.error);
    } catch { showWifi(null, 'the Pi does not answer'); }
  });
  $('wifi-move').addEventListener('click', async () => {
    const ok = await confirmDialog({ title: "Move R2's WiFi?", icon: 'fa-wifi', ok: 'Move it',
      lines: ['R2\'s access point restarts and comes back on the quietest of channels 1, 6 and 11.'],
      warn: 'The cameras and anything else on R2\'s WiFi drop for a few seconds.' });
    if (!ok) return;
    $('wifi-text').textContent = 'Restarting the access point…';
    try {
      const r = await (await fetch('api/wifi/move', { method: 'POST' })).json();
      if (r.error) showWifi(null, r.error); else showWifi(r.pick, 'moved just now');
    } catch { showWifi(null, 'the Pi does not answer'); }
  });

  // ---------- the Pico board ----------
  function showPico() {
    if (!visible) return;
    const fresh = pico && Date.now() - picoAt < 3000 && pico.connected;
    $('sys-pico-version').textContent = !fresh ? 'not connected'
      : `${pico.firmware || '?'}${pico.commit ? ` · ${pico.commit}` : ''}`;
    const box = $('sys-pico'), note = $('sys-pico-note');
    note.hidden = true;
    if (!telemetry || !fresh) { stale(box); return; }
    if (!(pico.proto >= 2)) {
      note.hidden = false;
      note.textContent = 'Update the Pico firmware to see its telemetry.';
      box.hidden = true;
      return;
    }
    const tm = pico.telemetry;
    if (!tm) {
      note.hidden = false;
      note.textContent = 'Waiting for the Pico…';
      stale(box);
      return;
    }
    const names = Object.keys(pico.sensors || {});
    const rps = tm.rps.map((n, i) => `${names[i] || `#${i}`} ${n}/s`).join(' · ');
    box.hidden = false;
    box.className = 'rings';
    box.innerHTML =
      ring('pico-c0', 'core 0 · measuring', pct(tm.c0), tm.c0, CPU_ZONES, 0, 100, ' %') +
      ring('pico-c1', 'core 1 · display', pct(tm.c1), tm.c1, CPU_ZONES, 0, 100, ' %') +
      ring('pico-bus', 'I2C bus', pct(tm.bus), tm.bus, CPU_ZONES, 0, 100, ' %',
        `display ${pct(tm.disp)}`, `a VL53L0X waited up to ${tm.wait_ms} ms for the bus`) +
      ring('pico-temp', 'chip temperature', `${tm.temp_c.toFixed(0)} °C`, tm.temp_c, PICO_TEMP_ZONES, 10, 90, ' °C') +
      `<div class="ringtext"><b>${uptime(tm.up_s)}</b><div class="l">up</div><div class="l dim">${rps || 'no sensors'}</div></div>`;
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
  let fw = null, fwTimer = null, fwStepState = null, fwStepAt = 0;
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
    // the bar and the warning while it runs; the bar stays full (or red) at the end
    if (fw.state !== fwStepState) { fwStepState = fw.state; fwStepAt = Date.now(); }
    const showBar = busy || fw.state === 'done' || fw.state === 'failed';
    $('fw-bar').hidden = !showBar;
    $('fw-warn').hidden = !busy;
    if (busy) $('fold-board').open = true;     // never flash with the progress folded away
    if (showBar) {
      const p = fw.state === 'failed' ? 100 : flashProgress(fw.state, (Date.now() - fwStepAt) / 1000);
      $('fw-barfill').style.width = `${p}%`;
      $('fw-barpct').textContent = fw.state === 'failed' ? 'failed' : `${p} %`;
      $('fw-bar').classList.toggle('bad', fw.state === 'failed');
    }
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
  $('fw-flash').addEventListener('click', async () => {
    const m = fw && fw.main;
    const lines = [m ? `New firmware: ${m.commit} — ${m.subject}` : 'The newest firmware on GitHub (main).',
      'The Pi downloads it, builds it (a few minutes) and copies it onto the Pico.'];
    if (fw && fw.compare === 'unpublished') lines.push('The Pico runs a build that is not on GitHub: this replaces it with main.');
    const ok = await confirmDialog({ title: 'Flash the Pico board?', lines, icon: 'fa-microchip', ok: 'Flash firmware',
      warn: "Do not unplug the Pico, the Pi or R2's power until it says it is done. The Pico's sensors stop for a few seconds." });
    if (ok) fwPost('flash');
  });
  $('fw-retry').addEventListener('click', () => fwPost('retry'));

  // ---------- polling ----------
  async function poll() {
    timer = null;
    if (!visible) return;
    try {
      const api = await (await fetch(`api/system${telemetry ? '?telemetry=1' : ''}`, { cache: 'no-store' })).json();
      showPi(api);
      boardView.pi(api);
    } catch { /* restarting */ }
    if (telemetry) {
      try { showCams(await (await fetch('api/domecams', { cache: 'no-store' })).json()); } catch { showCams(null); }
    }
    showPico();
    if (visible) timer = setTimeout(poll, telemetry ? period : 5000);
  }
  // the Pico keeps sending its telemetry only while asked at least every 5 s, whatever the period
  let picoTimer = null;
  function askPico() {
    clearTimeout(picoTimer);
    picoTimer = null;
    if (!visible || !telemetry) return;
    publish('/pico/telemetry_request', 'std_msgs/msg/Bool', { data: true });
    picoTimer = setTimeout(askPico, PICO_ASK_MS);
  }
  const restart = () => { clearTimeout(timer); timer = null; askPico(); poll(); };
  const stopPico = () => publish('/pico/telemetry_request', 'std_msgs/msg/Bool', { data: false });

  function setTelemetry(on) {
    telemetry = on;
    $('sys-telemetry').checked = on;
    try { localStorage.setItem('r2web.telemetry', on ? '1' : '0'); } catch { /* private window */ }
    if (!on) { stale($('sys-pi')); stale($('sys-pico')); $('sys-pi-warn').hidden = true; showCams(null); stopPico(); }
    restart();
  }
  $('sys-telemetry').addEventListener('change', (e) => setTelemetry(e.target.checked));
  $('sys-telemetry').checked = telemetry;
  for (const id of ['fold-board']) {
    try { $(id).open = localStorage.getItem(`r2web.${id}`) === '1'; } catch { /* private window */ }
    $(id).addEventListener('toggle', () => { try { localStorage.setItem(`r2web.${id}`, $(id).open ? '1' : '0'); } catch { /* private */ } });
  }
  $('sys-every').innerHTML = TELEMETRY_PERIODS.map((ms) => `<option value="${ms}">${ms / 1000} s</option>`).join('');
  $('sys-every').value = String(period);
  $('sys-every').addEventListener('change', (e) => {
    period = Number(e.target.value);
    try { localStorage.setItem('r2web.telemetry_ms', String(period)); } catch { /* private window */ }
    restart();
  });

  return {
    show() { visible = true; restart(); loadBoard(); loadWifi(); boardEnabled(); fwPost('check'); boardView.show(); },
    hide() { if (visible && telemetry) stopPico(); visible = false; clearTimeout(timer); timer = null; clearTimeout(picoTimer); picoTimer = null; boardView.hide(); },
  };
}
