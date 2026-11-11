// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> System: the Pi's and the Pico's versions and, while "Telemetry" is on and the tab
// is open, how busy they are. The Pi's from GET api/system?telemetry=1 every 2 s; the Pico's
// from /pico/state, asked for with /pico/telemetry_request every 2 s (the bridge sends TM 0
// once the requests stop). Temperature and load show the ranges they move in.
import { publish, subscribe } from './rosbridge.js';
import {
  CPU_ZONES, PICO_TEMP_ZONES, PI_TEMP_ZONES, bytes, level, minMax, pct, throttleText, uptime, versionText, zone,
} from './systemfmt.js';

const $ = (id) => document.getElementById(id);
const POLL_MS = 2000;

export function createSystemTab() {
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
    showPico();
  });

  // ---------- polling ----------
  async function poll() {
    timer = null;
    if (!visible) return;
    if (telemetry) publish('/pico/telemetry_request', 'std_msgs/msg/Bool', { data: true });
    try {
      const api = await (await fetch(`api/system${telemetry ? '?telemetry=1' : ''}`, { cache: 'no-store' })).json();
      showPi(api);
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
    show() { visible = true; restart(); },
    hide() { if (visible && telemetry) stopPico(); visible = false; clearTimeout(timer); timer = null; },
  };
}
