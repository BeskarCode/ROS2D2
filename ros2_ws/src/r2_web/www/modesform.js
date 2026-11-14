// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> Modes, the parts with no page in them (tested with node --test): the controller
// combinations each mode can take, modes.yaml as text, and a colour picked on the camera.
// Names and order are r2_nav/modes.py's (and the firmware's ROS_COMBO_NAMES).

export const MODES = ['goto', 'forward', 'patrol', 'follow'];
export const MODE_LABELS = { goto: 'Go to a point', forward: 'Go forward', patrol: 'Patrol', follow: 'Follow a colour' };

const DIRS = ['UP', 'DOWN', 'LEFT', 'RIGHT'];
export const COMBOS = [
  'FOOT_PS_L2',
  ...DIRS.flatMap((d) => ['', '_CROSS', '_CIRCLE', '_L1', '_PS', '_L3'].map((s) => `FOOT_${d}${s}`)),
  ...DIRS.flatMap((d) => ['', '_CROSS', '_CIRCLE', '_L1', '_PS', '_L3', '_L2', '_L2_CROSS', '_L2_CIRCLE']
    .map((s) => `DOME_${d}${s}`)),
];
// PS + L2 on the dome controller is face tracking: never a mode's combo
export const FACE_TRACKING = 'DOME_PS_L2';
// The combo that has always started the autonomous mode: it plays no MarcDuino action
export const AUTO_COMBO = 'FOOT_PS_L2';

const ARROWS = { UP: '↑', DOWN: '↓', LEFT: '←', RIGHT: '→' };
const BUTTONS = { CROSS: 'Cross', CIRCLE: 'Circle', L1: 'L1', L2: 'L2', L3: 'L3', PS: 'PS' };

// 'FOOT_UP_PS' -> 'Foot ↑ + PS', 'DOME_LEFT_L2_CROSS' -> 'Dome ← + L2 + Cross'
export function comboLabel(name) {
  const [nav, ...rest] = name.split('_');
  const parts = rest.map((p) => ARROWS[p] || BUTTONS[p] || p);
  return `${nav[0]}${nav.slice(1).toLowerCase()} ${parts.join(' + ')}`;
}

// Does giving this combo to a mode take a MarcDuino action away from it?
export const losesAction = (combo) => combo != null && combo !== AUTO_COMBO;

// The combos `mode` can choose: the ones another mode already has come back with `taken_by`
// set (shown, not choosable); face tracking never comes back.
export function comboChoices(cfg, mode, combos = COMBOS) {
  const owner = {};
  for (const m of MODES) if (m !== mode && cfg[m] && cfg[m].combo) owner[cfg[m].combo] = m;
  return combos.filter((c) => c !== FACE_TRACKING)
    .map((name) => ({ name, label: comboLabel(name), taken_by: owner[name] || null }));
}

// The order the settings are written in; anything else in a block goes after them
const FIELDS = {
  goto: ['combo', 'sound_on', 'sound_off'],
  forward: ['combo', 'sound_on', 'sound_off'],
  patrol: ['combo', 'sound_on', 'sound_off'],
  follow: ['combo', 'sound_on', 'sound_off', 'sound_lost', 'camera', 'color', 'hue_tol', 'light_tol',
           'area_ref', 'distance', 'max_speed', 'search_s'],
};
const NOTES = {
  color: 'OpenCV h 0-179, s and v 0-255, picked on the camera',
  hue_tol: '2-40', light_tol: '10-120 (s and v)',
  area_ref: 'fraction of the picture it filled when picked',
  distance: 'm, 0.8-4', max_speed: 'm/s, 0.05-0.4', search_s: 's searching with the dome, 0-20',
};

function value(v) {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'string') return /^[A-Za-z][A-Za-z0-9_]*$/.test(v) && !/^(null|true|false|yes|no|on|off|y|n)$/i.test(v)
    ? v : JSON.stringify(v);
  if (typeof v === 'number') return Number.isFinite(v) ? String(Math.round(v * 1e6) / 1e6) : 'null';
  if (typeof v === 'boolean') return String(v);
  if (typeof v === 'object') return `{${Object.entries(v).map(([k, x]) => `${k}: ${value(x)}`).join(', ')}}`;
  return JSON.stringify(v);
}

// The whole modes.yaml, as the page saves it
export function toYaml(cfg) {
  let out = '# ROS2D2 modes, saved from the web console (Setup -> Modes). Hand edits are fine too:\n' +
            '# the page reads this same file. combo: a name from r2_nav/modes.py or null; DOME_PS_L2 is face tracking.\n';
  for (const m of MODES) {
    const block = cfg[m] || {};
    out += `${m}:\n`;
    const keys = [...FIELDS[m].filter((k) => k in block), ...Object.keys(block).filter((k) => !FIELDS[m].includes(k))];
    for (const k of keys) out += `  ${k}: ${value(block[k])}${NOTES[k] ? `   # ${NOTES[k]}` : ''}\n`;
  }
  return out;
}

const copy = (o) => JSON.parse(JSON.stringify(o));

// /marker/pick_result -> the follow colour and how big it looked (a copy of cfg; cfg is kept)
export function pickToColor(result, cfg) {
  const out = copy(cfg);
  out.follow = out.follow || {};
  out.follow.color = { h: Math.round(result.h), s: Math.round(result.s), v: Math.round(result.v) };
  const area = Math.round(Number(result.area) * 1e5) / 1e5;
  out.follow.area_ref = area > 0 && area <= 1 ? area : null;
  return out;
}

// An OpenCV colour (h 0-179, s and v 0-255) as [r, g, b], for the swatch of a saved colour
export function hsvToRgb({ h, s, v }) {
  const H = (h * 2) % 360, S = s / 255, V = v / 255;
  const f = (n) => { const k = (n + H / 60) % 6; return V - V * S * Math.max(0, Math.min(k, 4 - k, 1)); };
  return [f(5), f(3), f(1)].map((x) => Math.round(x * 255));
}

/** The mode PS + L2 (foot Nav) starts, from /api/modes' modes, or null when none has it. */
export function startMode(modes) {
  return MODES.find((m) => modes && modes[m] && modes[m].combo === AUTO_COMBO) || null;
}
