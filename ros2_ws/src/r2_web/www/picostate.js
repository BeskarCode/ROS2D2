// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// What the console says about the Pico and its sensors, from /pico/state (r2_pico_bridge)
// and /range/<name>. Pure functions: tested with node --test.
//   state:   the /pico/state JSON, or null if none has arrived
//   ageMs:   how long ago that state arrived (the bridge sends it every second)
//   reading: { range (m, Infinity = nothing in range), ageMs } or null
const STATE_STALE_MS = 3000;     // no state for this long = no bridge running
const READING_STALE_MS = 500;    // the Pico sends readings every 50 ms

const fresh = (state, ageMs) => state && ageMs <= STATE_STALE_MS;
const metres = (r) => (Number.isFinite(r) ? `${r.toFixed(2)} m` : 'nothing in range');

export function picoPill(state, ageMs) {
  if (!fresh(state, ageMs)) return { cls: 'wait', text: 'Pico: no bridge' };
  if (!state.connected) return { cls: 'bad', text: 'Pico: disconnected' };
  if (state.config_error) return { cls: 'bad', text: 'Pico: config error' };
  return { cls: 'ok', text: `Pico: connected${state.firmware ? ` · ${state.firmware}` : ''}` };
}

export function sensorBadge(name, state, reading, ageMs, simulated) {
  if (simulated) return { cls: 'sim', text: reading ? `simulated · ${metres(reading.range)}` : 'simulated' };
  if (!fresh(state, ageMs)) return { cls: 'wait', text: 'waiting for the Pico' };
  if (!state.connected) return { cls: 'bad', text: 'Pico disconnected' };
  if (state.config_error) return { cls: 'bad', text: 'Pico config error' };
  const s = state.sensors[name];
  if (s === 'not_responding') return { cls: 'off', text: 'not responding' };
  if (s !== 'ok') return { cls: 'wait', text: 'starting…' };
  if (!reading || reading.ageMs > READING_STALE_MS) return { cls: 'wait', text: 'no reading' };
  return { cls: 'ok', text: metres(reading.range) };
}
