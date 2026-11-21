// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The console's two virtual PS3 Navs on the wire, shared by the Remote window and the phone view.
//
// Between start() and stop() each Nav's state goes out 20 times a second, at rest too, like a real
// Nav: the Mega takes 300 ms of silence as "let go" and 2 s as "controller lost" (it stops the feet
// and the dome and switches the modes off). A hidden tab or a page being left sends nothing, so that
// is switching the controllers off too. Each page says who it is ("id"): the Mega bridge lets one
// page drive at a time (the owner, on /mega/pads) and keeps the sticks within its limit.
import { createPad, maskOf, ownerState } from './padlogic.js';
import { GAP_MS, HOLD_MS, PRE_MS, stepsFor } from './shortcuts.js';
import { confirmDialog } from './dialog.js';
import { ensureConnected, publish, subscribe } from './rosbridge.js';

const SEND_MS = 50;
const TOPICS = { F: '/pad/foot', D: '/pad/dome' };

export { ownerState };

export function createPadLink({ onTick = () => {} } = {}) {
  const me = Math.random().toString(36).slice(2, 10);
  const pad = { F: createPad(), D: createPad() };
  const wasActive = { F: false, D: false };
  const listeners = [];
  let pads = { F: 'none', D: 'none', supported: null, mega: false, owner: null, limit: null };
  let on = false, timer = null, riskOk = false;
  let shortTimers = [], busy = false, finish = null;

  const send = (p, s) => publish(TOPICS[p], 'std_msgs/msg/String', { data: JSON.stringify({ id: me, ...s }) });

  function step() {
    const t = performance.now();
    for (const p of ['F', 'D']) {
      const now = pad[p].tick(t);
      if (now.length) onTick(p, now);
      if (pads.mega && pads.supported !== false) send(p, pad[p].state(t));   // at rest too, as a real Nav
      wasActive[p] = pad[p].active(t);
    }
  }
  function kick() {
    if (!on || document.visibilityState === 'hidden') return;
    if (!timer) timer = setInterval(step, SEND_MS);
    step();
  }

  // Everything let go at once (and the Mega told), a shortcut halfway too
  function releaseAll() {
    shortTimers.forEach(clearTimeout);
    shortTimers = [];
    if (busy) { busy = false; finish?.(false); finish = null; }
    for (const p of ['F', 'D']) {
      const had = pad[p].active(performance.now()) || wasActive[p];
      pad[p].reset();
      wasActive[p] = false;
      if (had) send(p, pad[p].state(0));
    }
    clearInterval(timer);
    timer = null;
  }

  // The first action on a slot with a real Nav connected asks first, once per start()
  async function allowed(p) {
    if (pads[p] !== 'real' || riskOk) return true;
    const ok = await confirmDialog({
      title: 'A real controller is connected', icon: 'fa-triangle-exclamation', ok: 'Send anyway',
      lines: [`The real ${p === 'F' ? 'foot' : 'dome'} Nav is on. What you send now acts on R2 as if pressed on it.`],
      warn: 'If someone moves the real controller, it wins and this is ignored.',
    });
    if (ok) riskOk = true;
    return ok;
  }

  // A combination pressed for you: modifiers first, then the arrow (or L2) with them, then let go
  // and wait (the sketch takes it on the first loop its arrow is down, and wants a second without
  // arrows before the next). onSent runs when it has been let go; true at the end, false if refused
  // or stopped halfway.
  async function runShortcut(sc, onSent = () => {}) {
    if (busy) return false;
    const st = stepsFor(sc.combo);
    for (const p of ['F', 'D']) if (st.then[p].length && !(await allowed(p))) return false;
    busy = true;
    const at = (ms, fn) => shortTimers.push(setTimeout(fn, ms));
    const press = (part) => { for (const p of ['F', 'D']) pad[p].force(maskOf(part[p])); kick(); };
    return new Promise((resolve) => {
      finish = resolve;
      press(st.first);
      at(PRE_MS, () => press(st.then));
      at(PRE_MS + HOLD_MS, () => { press({ F: [], D: [] }); onSent(); });
      at(PRE_MS + HOLD_MS + GAP_MS, () => { busy = false; shortTimers = []; finish = null; resolve(true); });
    });
  }

  subscribe('/mega/pads', 'std_msgs/msg/String', (m) => {
    try { pads = { ...pads, ...JSON.parse(m.data) }; } catch { return; }
    listeners.forEach((fn) => fn(pads));
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') releaseAll();
    else kick();                                  // back on the tab: the Navs are on again
  });
  window.addEventListener('pagehide', releaseAll);

  return {
    pad, me,
    start() { ensureConnected(); on = true; riskOk = false; kick(); },
    stop() { releaseAll(); on = false; riskOk = false; },
    kick, releaseAll, allowed, runShortcut,
    busy: () => busy,
    pads: () => pads,
    owner: () => ownerState(pads, me),
    onPads(fn) { listeners.push(fn); fn(pads); },
  };
}
