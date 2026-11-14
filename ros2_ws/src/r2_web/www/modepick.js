// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Console and Navigation: pick the mode PS + L2 starts, see which one is on, and stop it.
// Only the controller switches a mode on (the Mega refuses it from the Pi): picking a mode here
// gives it PS + L2 in modes.yaml (POST /api/modes/start, the same file as Setup -> Modes) and the
// Mega bridge sends the new bindings; Stop is /r2/auto_mode/disable.
import { call, subscribe } from './rosbridge.js';
import { MODES, MODE_LABELS, startMode } from './modesform.js';

const ICONS = { goto: 'fa-location-crosshairs', forward: 'fa-arrow-up', patrol: 'fa-route', follow: 'fa-shirt' };

/** el: the container. onPress (optional): a "PS + L2" button that presses it (the simulator). */
export function createModePick(el, { onPress, log = () => {} } = {}) {
  el.classList.add('modepick');
  el.innerHTML = `<span class="mp-label" title="PS + L2 on the foot controller switches this mode on (and off)"><i class="fa-solid fa-gamepad"></i>PS + L2 starts</span>
    <span class="seg mp-modes">${MODES.map((m) =>
      `<button data-mode="${m}" title="PS + L2 on the controller will start ${MODE_LABELS[m]}"><i class="fa-solid ${ICONS[m]}"></i>${MODE_LABELS[m]}</button>`).join('')}</span>
    ${onPress ? '<button class="mp-press primary" title="Simulated PS + L2 on the foot controller: on when off, off when on"><i class="fa-solid fa-play"></i>PS + L2</button>' : ''}
    <button class="mp-stop" disabled title="Switch the automatic mode off (the controller can switch it on again)"><i class="fa-solid fa-stop"></i>Stop</button>
    <span class="mp-state"></span>`;
  let start = null, auto = false, mode = '', busy = false;

  function show() {
    el.querySelectorAll('.mp-modes button').forEach((b) => {
      b.classList.toggle('on', b.dataset.mode === start);
      b.disabled = busy;
    });
    el.querySelector('.mp-stop').disabled = !auto;
    const st = el.querySelector('.mp-state');
    st.className = 'mp-state ' + (auto ? 'ok' : '');
    st.textContent = auto ? `● ${MODE_LABELS[mode] || 'automatic'} on` : start ? 'off: press PS + L2 to start' : 'off: no mode on PS + L2';
    const press = el.querySelector('.mp-press');
    if (press) press.innerHTML = auto ? '<i class="fa-solid fa-stop"></i>PS + L2' : '<i class="fa-solid fa-play"></i>PS + L2';
  }
  async function load() {
    try {
      const p = await (await fetch('api/modes', { cache: 'no-store' })).json();
      start = p.error ? null : startMode(p.modes);
      if (p.error) log(`· modes.yaml: ${p.error}`);
    } catch { /* restarting */ }
    show();
  }
  el.querySelectorAll('.mp-modes button').forEach((b) => {
    b.onclick = async () => {
      if (b.dataset.mode === start || busy) return;
      busy = true; show();
      try {
        const r = await fetch('api/modes/start', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: b.dataset.mode }) });
        const body = await r.json();
        if (r.ok) { start = body.start; log(`· PS + L2 now starts ${MODE_LABELS[start]}`); } else log(`· ${body.error}`);
      } catch (e) { log(`· could not save: ${e}`); }
      busy = false; show();
    };
  });
  el.querySelector('.mp-stop').onclick = () => call('/r2/auto_mode/disable', 'std_srvs/srv/Trigger', {});
  if (onPress) el.querySelector('.mp-press').onclick = onPress;
  subscribe('/r2/auto_mode', 'std_msgs/msg/Bool', (m) => { auto = m.data; show(); });
  subscribe('/r2/mode', 'std_msgs/msg/String', (m) => { mode = m.data; show(); });
  load();
  return { reload: load };
}
