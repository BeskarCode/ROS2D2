// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// How the System tab writes its numbers. Pure functions: tested with node --test.

export function bytes(n) {
  if (n == null || !Number.isFinite(n)) return '–';
  for (const [u, d] of [['GB', 1e9], ['MB', 1e6], ['KB', 1e3]]) {
    if (n >= d) return `${+(n / d).toFixed(n / d >= 100 ? 0 : 1)} ${u}`;
  }
  return `${n} B`;
}

export const pct = (x) => (x == null || !Number.isFinite(x) ? '–' : `${Math.round(x)} %`);

// fraction free (or left) against its limits: below warn = 'warn', below bad = 'bad'
export const level = (fraction, warn, bad) => (fraction < bad ? 'bad' : fraction < warn ? 'warn' : 'ok');

const FLAGS = [['undervoltage_now', 'Under-voltage now'], ['throttled_now', 'Throttled now'],
  ['undervoltage_since_boot', 'Under-voltage since boot'], ['throttled_since_boot', 'Throttled since boot']];
export const throttleText = (t) => (t ? FLAGS.filter(([k]) => t[k] === true).map(([, text]) => text) : []);

export function versionText(v) {
  if (!v || !v.commit) return 'unknown';
  return `${v.commit}${v.date ? ` · ${v.date.slice(0, 10)}` : ''}${v.dirty ? ' + local changes' : ''}`;
}

// Ranges a value moves in: [upper limit, class, label], the last one open-ended.
// Pi 4/5: fine working up to ~65 °C in a box; it slows itself down (throttles) from 80 °C.
export const PI_TEMP_ZONES = [[65, 'ok', 'normal'], [80, 'warn', 'warm'], [Infinity, 'bad', 'throttling']];
// RP2350: rated to 85 °C
export const PICO_TEMP_ZONES = [[60, 'ok', 'normal'], [85, 'warn', 'warm'], [Infinity, 'bad', 'too hot']];
export const CPU_ZONES = [[70, 'ok', 'normal'], [90, 'warn', 'busy'], [Infinity, 'bad', 'saturated']];

export function zone(value, zones) {
  if (value == null || !Number.isFinite(value)) return null;
  const [, cls, label] = zones.find(([top]) => value < top);
  return { cls, label };
}

// the lowest and highest seen so far (null values leave it as it was)
export function minMax(prev, v) {
  if (v == null || !Number.isFinite(v)) return prev;
  return prev ? { min: Math.min(prev.min, v), max: Math.max(prev.max, v) } : { min: v, max: v };
}

export function uptime(s) {
  if (s == null || !Number.isFinite(s)) return '–';
  if (s < 60) return `${Math.round(s)} s`;
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h ? `${h} h ${String(m).padStart(2, '0')} min` : `${m} min`;
}

// The Pico firmware block: what GET api/firmware says, in a line
export function firmwareText(api) {
  if (!api.installed) return { cls: 'warn', text: 'Toolchain not installed on the Pi (setup/install_pico_toolchain.sh)' };
  if (api.internet === false) return { cls: 'warn', text: "No internet: can't check" };
  if (api.internet == null) return { cls: '', text: 'Not checked yet' };
  const m = api.main;
  if (api.compare === 'update' && m) return { cls: 'ok', text: `New Pico firmware: ${m.commit} ${m.subject} (${m.date.slice(0, 10)})` };
  if (api.compare === 'up_to_date') return { cls: '', text: 'Up to date' };
  if (api.compare === 'unpublished') return { cls: 'warn', text: `Pico runs an unpublished build (${api.pico_commit})` };
  return { cls: '', text: 'Unknown Pico version' };
}

// The display's buttons from what the board says it shows (DS): lit or not, and which screen
export function displayButtons(ds) {
  if (!ds || ds === 'off') return { on: false, screen: null };
  return { on: true, screen: ds === 'logo' ? 'all' : ds };
}
