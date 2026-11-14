// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Navigation page -> Settings, the parts with no page in them (node --test): the nav.yaml
// settings shown on the page, by group, and nav.yaml written back as text.
// Keys, ranges and defaults are r2_nav/nav_core.py's (DEFAULTS, RANGES).

export const GROUPS = [
  ['Safety circle', 'fa-circle-exclamation', [
    { key: 'safety_radius', label: 'safety circle', min: 0.25, max: 1.5, step: 0.01, unit: 'm', help: 'm from the body centre: R2 keeps things ahead outside it' },
    { key: 'safety_cone_deg', label: 'circle watched ahead', min: 20, max: 90, step: 1, unit: '°', help: 'something inside the circle within this angle of ahead stops it (each side)' },
    { key: 'slow_from', label: 'slow down from', min: 0.1, max: 3, step: 0.05, unit: 'm', help: 'm beyond the circle where it starts slowing down' },
    { key: 'goal_tolerance', label: 'arrived within', min: 0.05, max: 1, step: 0.05, unit: 'm' },
  ]],
  ['Speed', 'fa-gauge', [
    { key: 'max_speed', label: 'top speed', min: 0.05, max: 0.4, step: 0.01, unit: 'm/s' },
    { key: 'max_turn_deg', label: 'top turn', min: 5, max: 34, step: 1, unit: '°/s' },
    { key: 'accel', label: 'acceleration', min: 0.05, max: 2, step: 0.05, unit: 'm/s²' },
    { key: 'turn_accel_deg', label: 'turn acceleration', min: 5, max: 180, step: 1, unit: '°/s²' },
    { key: 'max_drive_power', label: 'drive power cap', min: 5, max: 127, step: 1, unit: '', help: 'Sabertooth units, like ShadowMD drivespeed' },
    { key: 'max_turn_power', label: 'turn power cap', min: 5, max: 127, step: 1, unit: '', help: 'Sabertooth units, like ShadowMD turnspeed' },
  ]],
  ['Blocked (Go to a point, Patrol)', 'fa-hand', [
    { key: 'on_blocked', label: 'when blocked', options: ['turn', 'reverse', 'wait'] },
    { key: 'allow_reverse', label: 'may back up', bool: true },
    { key: 'give_up_after', label: 'give up after', min: 1, max: 20, step: 1, unit: 'tries' },
  ]],
  ['Go forward', 'fa-arrow-up', [
    { key: 'search_turn', label: 'search turn speed', min: 0.2, max: 1, step: 0.05, unit: '× top turn', help: 'boxed in, it turns on the spot this slowly' },
    { key: 'search_free', label: 'free to leave', min: 0.1, max: 1, step: 0.05, unit: 'm', help: 'm beyond the circle that must be free ahead to leave that way' },
    { key: 'search_wide_deg', label: 'search when gap beyond', min: 20, max: 90, step: 1, unit: '°', help: 'a way out further off to a side than this is searched for slowly' },
    { key: 'search_near', label: 'boxed in under', min: 0, max: 0.5, step: 0.01, unit: 'm', help: 'm beyond the circle: closer than this ahead counts as boxed in' },
    { key: 'forward_stuck_s', label: 'stuck after', min: 3, max: 30, step: 1, unit: 's', help: 'without moving 15 cm: search for a way out' },
  ]],
  ['Sensors', 'fa-satellite-dish', [
    { key: 'filter', label: 'smooth the distance sensors', bool: true },
    { key: 'sensors_may_stop_earlier', label: "a sensor's own stop distance wins", bool: true },
  ]],
];

export const FIELDS = GROUPS.flatMap(([, , f]) => f);
const ORDER = ['safety_radius', 'safety_cone_deg', 'slow_from', 'max_speed', 'max_turn_deg', 'accel', 'turn_accel_deg',
  'max_drive_power', 'max_turn_power', 'goal_tolerance', 'sensors_may_stop_earlier', 'filter', 'on_blocked', 'allow_reverse',
  'give_up_after', 'search_turn', 'search_free', 'search_wide_deg', 'search_near', 'forward_stuck_s'];

// a decimal setting is written with its decimals (1.0, not 1): ROS fixes a parameter's type at start-up
const val = (k, v) => {
  if (typeof v !== 'number') return String(v);
  const t = String(Math.round(v * 1000) / 1000);
  const f = FIELDS.find((x) => x.key === k);
  return f && f.step < 1 && !t.includes('.') ? `${t}.0` : t;
};

/** nav.yaml as text from the settings (every key, then the sounds block). */
export function toNavYaml(cfg) {
  let out = '# R2 navigation, saved from the web console (Navigation page). Hand edits are fine too.\n';
  for (const k of ORDER) if (cfg[k] !== undefined) out += `${k}: ${val(k, cfg[k])}\n`;
  const sounds = cfg.sounds || {};
  out += 'sounds:\n';
  for (const [ev, cmd] of Object.entries(sounds)) out += `  ${ev}: "${cmd || ''}"\n`;
  return out;
}

/** Keys whose value differs from the defaults (to show which ones the user changed). */
export function changedKeys(cfg, defaults) {
  return FIELDS.map((f) => f.key).filter((k) => cfg[k] !== undefined && defaults[k] !== undefined && cfg[k] !== defaults[k]);
}
