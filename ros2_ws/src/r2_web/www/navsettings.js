// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Navigation page -> Settings, the parts with no page in them (node --test): the nav.yaml
// settings shown on the page, by group, and nav.yaml written back as text.
// Keys, ranges and defaults are r2_nav/nav_core.py's (DEFAULTS, RANGES).

export const GROUPS = [
  ['Safety circle', 'fa-circle-exclamation', [
    { key: 'safety_radius', label: 'safety circle', min: 0.4, max: 1.5, step: 0.01, unit: 'm', help: 'm from the body centre: R2 keeps things ahead outside it (at least 0.40: half the body is 0.36)' },
    { key: 'safety_cone_deg', label: 'circle watched ahead', min: 20, max: 90, step: 1, unit: '°', help: 'something inside the circle within this angle of ahead stops it (each side)' },
    { key: 'slow_from', label: 'slow down from', min: 0.3, max: 3, step: 0.05, unit: 'm', help: 'm beyond the circle where it starts slowing down' },
    { key: 'goal_tolerance', label: 'arrived within', min: 0.05, max: 1, step: 0.05, unit: 'm' },
  ]],
  ['Speed', 'fa-gauge', [
    { key: 'max_speed', label: 'top speed', min: 0.05, max: 0.4, step: 0.01, unit: 'm/s' },
    { key: 'max_turn_deg', label: 'top turn', min: 5, max: 34, step: 1, unit: '°/s' },
    { key: 'accel', label: 'acceleration', min: 0.05, max: 2, step: 0.05, unit: 'm/s²' },
    { key: 'decel', label: 'slowing down', min: 0.1, max: 2, step: 0.05, unit: 'm/s²', help: 'gentle slow-downs; a stop for something in the way cuts at once' },
    { key: 'brake_decel', label: 'real braking', min: 0.05, max: 2, step: 0.05, unit: 'm/s²', help: 'what R2 really stops with (measure it on the droid): sensors and lidar stop it earlier by v²/(2·this)' },
    { key: 'turn_accel_deg', label: 'turn acceleration', min: 5, max: 180, step: 1, unit: '°/s²' },
    { key: 'max_drive_power', label: 'drive power cap', min: 5, max: 127, step: 1, unit: '', help: 'Sabertooth units, like ShadowMD drivespeed' },
    { key: 'max_turn_power', label: 'turn power cap', min: 5, max: 127, step: 1, unit: '', help: 'Sabertooth units, like ShadowMD turnspeed' },
  ]],
  ['Blocked (Go to a point, Patrol)', 'fa-hand', [
    { key: 'on_blocked', label: 'when blocked', options: ['turn', 'reverse', 'wait'] },
    { key: 'allow_reverse', label: 'may back up', bool: true },
    { key: 'give_up_after', label: 'give up after', min: 1, max: 20, step: 1, unit: 'tries' },
    { key: 'wait_max_s', label: 'wait for the way', min: 0.5, max: 30, step: 0.5, unit: 's', help: 'with "when blocked: wait"' },
    { key: 'reverse_max', label: 'back up', min: 0.05, max: 1, step: 0.05, unit: 'm', help: 'with "when blocked: reverse"' },
    { key: 'stuck_after_s', label: 'a try after', min: 3, max: 60, step: 1, unit: 's', help: 'without getting 15 cm closer to the goal' },
    { key: 'free_s', label: 'clear for', min: 0.2, max: 5, step: 0.1, unit: 's', help: 'with the front clear before heading for the goal again' },
  ]],
  ['Go forward', 'fa-arrow-up', [
    { key: 'search_turn', label: 'search turn speed', min: 0.2, max: 1, step: 0.05, unit: '× top turn', help: 'boxed in, it turns on the spot this slowly' },
    { key: 'search_free', label: 'free to leave', min: 0.1, max: 1, step: 0.05, unit: 'm', help: 'm beyond the circle that must be free ahead to leave that way' },
    { key: 'search_wide_deg', label: 'search when gap beyond', min: 20, max: 90, step: 1, unit: '°', help: 'a way out further off to a side than this is searched for slowly' },
    { key: 'search_near', label: 'boxed in under', min: 0, max: 0.5, step: 0.01, unit: 'm', help: 'm beyond the circle: closer than this ahead counts as boxed in' },
    { key: 'forward_stuck_s', label: 'stuck after', min: 3, max: 30, step: 1, unit: 's', help: 'without moving 15 cm: search for a way out' },
  ]],
  ['Patrol and Free roam', 'fa-shuffle', [
    { key: 'wander.max_speed', label: 'top speed', min: 0.05, max: 0.4, step: 0.01, unit: 'm/s', help: 'slower than Go forward: it strolls' },
    { key: 'wander.radius', label: 'Patrol radius', min: 0.5, max: 10, step: 0.1, unit: 'm', help: 'round where Patrol was switched on (approximate: without wheel encoders it drifts)' },
    { key: 'wander.turn_every_s.0', label: 'new course every, from', min: 2, max: 120, step: 1, unit: 's' },
    { key: 'wander.turn_every_s.1', label: '… to', min: 2, max: 120, step: 1, unit: 's' },
    { key: 'wander.turn_deg.0', label: 'course change, from', min: 10, max: 180, step: 5, unit: '°' },
    { key: 'wander.turn_deg.1', label: '… to', min: 10, max: 180, step: 5, unit: '°' },
    { key: 'wander.pause_chance', label: 'stops to look', min: 0, max: 1, step: 0.05, unit: '', help: 'chance of stopping to look round at each new course (0-1)' },
    { key: 'wander.pause_s.0', label: 'looks round for, from', min: 0.5, max: 30, step: 0.5, unit: 's' },
    { key: 'wander.pause_s.1', label: '… to', min: 0.5, max: 30, step: 0.5, unit: 's' },
    { key: 'wander.greet_size', label: 'says hello to a face from', min: 0.02, max: 0.5, step: 0.01, unit: '× picture', help: 'a face this wide (a fraction of the picture) is close enough to say hello' },
    { key: 'wander.greet_s', label: 'hello lasts up to', min: 2, max: 60, step: 1, unit: 's' },
    { key: 'wander.greet_cooldown_s', label: 'no new hello for', min: 0, max: 300, step: 5, unit: 's' },
    { key: 'wander.blocked_s', label: 'turns away after', min: 1, max: 20, step: 0.5, unit: 's', help: 'blocked this long: a new course 120-180° away' },
    { key: 'wander.heading_home_deg', label: 'back towards the start ±', min: 0, max: 90, step: 5, unit: '°', help: 'Patrol, outside its radius: new courses point home within this' },
  ]],
  ['Sensors', 'fa-satellite-dish', [
    { key: 'filter', label: 'smooth the distance sensors', bool: true },
    { key: 'sensors_may_stop_earlier', label: "a sensor's own stop distance wins", bool: true },
  ]],
];

export const FIELDS = GROUPS.flatMap(([, , f]) => f);
const ORDER = ['safety_radius', 'safety_cone_deg', 'slow_from', 'max_speed', 'max_turn_deg', 'accel', 'decel', 'brake_decel',
  'turn_accel_deg', 'max_drive_power', 'max_turn_power', 'goal_tolerance', 'sensors_may_stop_earlier', 'filter', 'on_blocked',
  'allow_reverse', 'give_up_after', 'wait_max_s', 'reverse_max', 'stuck_after_s', 'free_s', 'search_turn', 'search_free',
  'search_wide_deg', 'search_near', 'forward_stuck_s'];

// a decimal setting is written with its decimals (1.0, not 1): ROS fixes a parameter's type at start-up
const val = (k, v) => {
  if (typeof v !== 'number') return String(v);
  const t = String(Math.round(v * 1000) / 1000);
  const f = FIELDS.find((x) => x.key === k);
  return f && f.step < 1 && !t.includes('.') ? `${t}.0` : t;
};

// A field's key: a plain setting ('max_speed'), one in the wander block ('wander.radius') or one end of a
// [min, max] pair ('wander.turn_every_s.0')
export function getK(cfg, key) {
  return key.split('.').reduce((o, p) => (o == null ? undefined : o[p]), cfg);
}
export function setK(cfg, key, v) {
  const parts = key.split('.');
  const last = parts.pop();
  const o = parts.reduce((x, p) => x[p], cfg);
  o[last] = v;
}
/** The ROS parameter a field changes: { name, value } (a pair sends its whole [min, max]). */
export function liveParam(cfg, key) {
  const parts = key.split('.');
  if (parts.length === 3) parts.pop();
  const name = parts.join('.');
  return { name, value: getK(cfg, name) };
}

const WANDER_ORDER = ['max_speed', 'radius', 'turn_every_s', 'turn_deg', 'pause_chance', 'pause_s', 'greet_size', 'greet_s',
  'greet_cooldown_s', 'blocked_s', 'heading_home_deg', 'hello', 'idle_sounds'];
const wval = (v) => (Array.isArray(v) ? `[${v.map((x) => (typeof x === 'string' ? `"${x}"` : x)).join(', ')}]`
  : typeof v === 'string' ? `"${v}"` : String(Math.round(v * 1000) / 1000));

/** nav.yaml as text from the settings (every key, then the wander and sounds blocks). */
export function toNavYaml(cfg) {
  let out = '# R2 navigation, saved from the web console (Navigation page). Hand edits are fine too.\n';
  for (const k of ORDER) if (cfg[k] !== undefined) out += `${k}: ${val(k, cfg[k])}\n`;
  if (cfg.wander) {
    out += 'wander:\n';
    for (const k of WANDER_ORDER) if (cfg.wander[k] !== undefined) out += `  ${k}: ${wval(cfg.wander[k])}\n`;
  }
  const sounds = cfg.sounds || {};
  out += 'sounds:\n';
  for (const [ev, cmd] of Object.entries(sounds)) out += `  ${ev}: "${cmd || ''}"\n`;
  return out;
}

/** Keys whose value differs from the defaults (to show which ones the user changed). */
export function changedKeys(cfg, defaults) {
  return FIELDS.map((f) => f.key).filter((k) => getK(cfg, k) !== undefined && getK(defaults, k) !== undefined && getK(cfg, k) !== getK(defaults, k));
}
