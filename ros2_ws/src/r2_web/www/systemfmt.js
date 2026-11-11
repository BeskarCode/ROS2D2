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
