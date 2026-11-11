// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> System: the Pi's software version and, while "Telemetry" is on and the tab is open,
// its SD, RAM, CPU, temperature and power warnings (GET api/system?telemetry=1 every 2 s).
import { bytes, level, pct, throttleText, versionText } from './systemfmt.js';

const $ = (id) => document.getElementById(id);
const POLL_MS = 2000;

export function createSystemTab() {
  let visible = false;
  let timer = null;
  let telemetry = false;
  try { telemetry = localStorage.getItem('r2web.telemetry') === '1'; } catch { /* private window */ }

  const stat = (label, value, cls = '', extra = '') =>
    `<div class="stat ${cls}"><div class="v">${value}</div><div class="l">${label}</div>${extra}</div>`;
  const bar = (used) => `<div class="sbar"><i style="width:${Math.max(0, Math.min(100, used * 100)).toFixed(1)}%"></i></div>`;

  function showPi(api) {
    $('sys-pi-version').textContent = versionText(api.version);
    const box = $('sys-pi');
    box.hidden = !telemetry;
    if (!telemetry || !api.disk) return;
    const d = api.disk, m = api.mem;
    const diskFree = d.total ? d.free / d.total : 1;
    const memFree = m.total ? m.available / m.total : 1;
    const cores = api.cpu ? api.cpu.slice(1).map((c, i) => `core ${i} ${pct(c)}`).join(' · ') : '';
    const t = api.temp_c;
    let o = stat('SD free', `${bytes(d.free)} <small>of ${bytes(d.total)}</small>`, level(diskFree, 0.15, 0.05), bar(1 - diskFree)) +
      stat('RAM available', `${bytes(m.available)} <small>of ${bytes(m.total)}</small>`, level(memFree, 0.20, 0.10), bar(1 - memFree)) +
      stat('CPU', api.cpu ? pct(api.cpu[0]) : '…', '', `<div class="l">${cores}</div>`) +
      stat('temperature', t == null ? '–' : `${t.toFixed(0)} °C`, t == null ? '' : t >= 80 ? 'bad' : t >= 70 ? 'warn' : '');
    box.innerHTML = o;
    const warn = throttleText(api.throttled);
    $('sys-pi-warn').hidden = !warn.length;
    $('sys-pi-warn').innerHTML = warn.map((w) => `<i class="fa-solid fa-bolt"></i>${w}`).join(' · ');
  }

  async function poll() {
    timer = null;
    if (!visible) return;
    try {
      const api = await (await fetch(`api/system${telemetry ? '?telemetry=1' : ''}`, { cache: 'no-store' })).json();
      showPi(api);
    } catch { /* restarting */ }
    if (visible && telemetry) timer = setTimeout(poll, POLL_MS);
  }
  const restart = () => { clearTimeout(timer); timer = null; poll(); };

  function setTelemetry(on) {
    telemetry = on;
    $('sys-telemetry').checked = on;
    try { localStorage.setItem('r2web.telemetry', on ? '1' : '0'); } catch { /* private window */ }
    if (!on) { $('sys-pi').hidden = true; $('sys-pi-warn').hidden = true; }
    restart();
  }
  $('sys-telemetry').addEventListener('change', (e) => setTelemetry(e.target.checked));
  $('sys-telemetry').checked = telemetry;

  return {
    show() { visible = true; restart(); },
    hide() { visible = false; clearTimeout(timer); timer = null; },
    telemetryOn: () => telemetry && visible,
  };
}
