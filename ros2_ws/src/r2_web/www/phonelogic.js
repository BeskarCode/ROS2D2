// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The phone view without the page (tested with node --test, test/phonelogic.test.mjs): a finger on a
// stick as the Nav's 0..255, which mode buttons to show, and the grid of actions.
import { MD_ACTIONS, shortcutList } from './shortcuts.js';
import { FACE_TRACKING, MODES, MODE_LABELS, comboLabel } from './modesform.js';

// The finger dx, dy pixels from the stick's centre, on a stick of `radius` pixels -> the Nav's
// x, y (128 = centre). Kept inside the circle; a finger up (dy < 0) is the stick forward (small y),
// as on a PS3 Nav. The Mega bridge then keeps it within the limit (20 % by default).
export function stickValue(dx, dy, radius) {
  const d = Math.hypot(dx, dy);
  if (d > radius) { dx *= radius / d; dy *= radius / d; }
  const v = (u) => Math.max(0, Math.min(255, Math.round(128 + 127 * u / radius)));
  return { x: v(dx), y: v(dy) };
}

// One button per mode (modes.yaml's combo, or null: it cannot be started from here), then face
// tracking. Go to a point only in the simulator: on the droid, without wheel encoders, it drifts
// (it is there to try the sensors' layout).
export function modeButtons(modes, sim) {
  const out = [];
  for (const m of MODES) {
    if (m === 'goto' && !sim) continue;
    out.push({ mode: m, label: MODE_LABELS[m], combo: (modes && modes[m] && modes[m].combo) || null });
  }
  out.push({ mode: 'tracking', label: 'Face tracking', combo: FACE_TRACKING });
  return out;
}

// The Actions tab: the favourites first (with the names given to them), then every MarcDuino action
// that is not one of them, found by `query`. A combination given to a mode starts the mode instead
// of its action, so it is not offered here (it is in Modes).
export function actionGrid(favorites, query, modes = {}) {
  const known = Object.fromEntries(shortcutList(modes).map((s) => [s.combo, s]));
  const favs = (favorites || []).filter((f) => known[f.combo])
    .map((f) => ({ combo: f.combo, name: f.name, what: known[f.combo].what, label: known[f.combo].label }));
  const mine = new Set(favs.map((f) => f.combo));
  const q = (query || '').trim().toLowerCase();
  const rest = Object.keys(MD_ACTIONS)
    .filter((c) => known[c] && known[c].kind === 'marcduino' && !mine.has(c))
    .map((c) => ({ combo: c, label: comboLabel(c), what: MD_ACTIONS[c] }))
    .filter((a) => !q || `${a.what} ${a.label}`.toLowerCase().includes(q));
  return { favs, rest };
}
