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

/** A ring gauge's coloured zones as fractions of the ring: [{from, to, cls}], clipped to [lo, hi]. */
export function ringBands(zones, lo, hi) {
  const at = (v) => Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  let from = 0;
  return zones.map(([top, cls]) => {
    const band = { from, to: at(Math.min(top, hi)), cls };
    from = band.to;
    return band;
  }).filter((b) => b.to > b.from);
}

/** Where a value sits on a ring gauge, 0..1 (0 when unknown). */
export function ringFill(value, lo, hi) {
  if (value == null || !Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, (value - lo) / (hi - lo)));
}

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

// ---------- the network (ESP32) dome cameras: GET api/domecams ----------
// ESP32-P4: rated to 85 °C ambient; the chip sensor reads above the air around it
export const CAM_TEMP_ZONES = [[65, 'ok', 'normal'], [80, 'warn', 'warm'], [Infinity, 'bad', 'too hot']];
// WiFi signal as dBm below zero (bigger = weaker), so the ring fills as it gets worse
export const RSSI_ZONES = [[67, 'ok', 'good'], [77, 'warn', 'weak'], [Infinity, 'bad', 'very weak']];
// The telemetry refresh the console offers (ms); the Pico is still asked every 2 s in between
export const TELEMETRY_PERIODS = [1000, 2000, 5000, 10000, 30000];

// Why the WiFi last dropped (wifi_err_reason_t), the usual ones in words
const WIFI_REASONS = {
  1: 'unspecified', 2: 'authentication expired', 3: 'left (auth)', 4: 'inactive too long', 5: 'AP full',
  8: 'left', 15: 'handshake timed out', 200: 'lost the AP (beacons)', 201: 'AP not found',
  202: 'authentication failed', 203: 'association failed', 204: 'handshake timed out',
  205: 'connection failed', 206: 'AP reset', 207: 'roaming',
};
export function wifiReason(code) {
  if (!code) return 'never dropped';
  return `${WIFI_REASONS[code] || 'reason'} (${code})`;
}

/** The text lines under a dome camera's rings: [label, value, cls] from its /status. */
export function camLines(s, ms) {
  const lines = [
    ['up', `${uptime(s.uptime_s)} · start #${s.boots ?? '?'} · last: ${s.reset_reason || '?'}`,
      ['crash', 'watchdog', 'brownout', 'power glitch', 'CPU lockup'].some((w) => (s.reset_reason || '').includes(w)) ? 'bad' : ''],
    ['WiFi', `${s.ip || '?'} · ${s.wifi_reconnects ?? '?'} drops · last: ${wifiReason(s.wifi_last_reason)}${ms != null ? ` · answers in ${ms} ms` : ''}`,
      s.wifi_reconnects > 0 ? 'warn' : ''],
    ['finding', s.detect === 2 ? `colour · ${s.faces_fps ?? 0} /s` : s.detect === 1 ? `faces · ${s.faces_fps ?? 0} /s · scores ${s.score1}/${s.score2}` : 'nothing',
      s.detect === 1 && s.faces_fps < 10 ? 'warn' : ''],
    ['clients', `faces ${s.faces_clients ?? 0} · video ${s.stream_clients ?? 0}`, ''],
    ['memory', `${bytes(s.heap)} internal · ${bytes(s.psram_free)} PSRAM free`, s.heap < 40000 ? 'warn' : ''],
    ['firmware', `${s.fw || '?'}${s.built ? ` · built ${s.built}` : ''} · ${s.sensor || 'no camera'} ${s.sensor_mode || ''}`.trim(), ''],
  ];
  return lines;
}

// ---------- flashing the Pico from the console: how far it has gone, 0-100 ----------
// Each step owns a slice of the bar; inside the long ones (the build takes minutes on the Pi) the
// bar creeps on with the time spent, never reaching the next slice until the step really ends.
const FLASH_STEPS = { starting: [0, 3, 5], pulling: [3, 10, 30], compiling: [10, 80, 240], releasing: [80, 85, 5],
  flashing: [85, 93, 15], waiting: [93, 99, 20] };
export function flashProgress(state, secs) {
  if (state === 'done') return 100;
  const s = FLASH_STEPS[state];
  if (!s) return 0;
  const [from, to, expect] = s;
  const f = 1 - Math.exp(-Math.max(0, secs) / expect);   // fast at first, slower as it goes past the usual time
  return Math.round(from + (to - from) * 0.95 * f);
}

// ---------- R2's own WiFi (the AP): how busy channels 1, 6 and 11 are (GET api/wifi, POST survey) ----------
// busy_dbm: every neighbour's signal added up, weighted by how much it overlaps that channel
// (setup/r2-wifi-channel); -100 = nothing at all. The bar grows with it: -100 empty, -30 full.
export function wifiRows(look) {
  if (!look || !look.busy_dbm) return [];
  return [1, 6, 11].map((ch) => {
    const dbm = Number(look.busy_dbm[ch] ?? look.busy_dbm[String(ch)] ?? -100);
    return {
      ch, dbm,
      pct: Math.round(Math.max(0, Math.min(100, (dbm + 100) / 70 * 100))),
      cls: dbm < -75 ? 'ok' : dbm < -50 ? 'warn' : 'bad',
      current: look.channel === ch,
      best: look.best === ch,
    };
  });
}
