// Setup -> Sensors: place the lidar and the distance sensors on the droid, see what they
// cover and what they miss, and save sensors.yaml (the TF follows at once on the Pi).
// Sensors are kept as in sensors.yaml (metres, degrees, ROS axes: + yaw = left).
import { MODELS } from './models.js';
import { call, subscribe } from './rosbridge.js';
import { createSensorMap } from './sensormap.js';
import { createSensorView3d } from './sensorview3d.js';
import { R2, TYPES, coverage, defaultName, isLidar, sees, sideText, uniqueName } from './sensormath.js';

const $ = (id) => document.getElementById(id);
const OBJECTS = {
  chair: { label: 'chair leg Ø4 cm', size: 0.04, heightTop: 0.75 },
  person: { label: 'person Ø30 cm', size: 0.30, heightTop: 1.7 },
  wall: { label: 'wall-ish Ø60 cm', size: 0.60, heightTop: 1.0 },
  box: { label: 'low box 10 cm', size: 0.30, heightTop: 0.10 },
};
const OBJECT0 = { x: 0.7, y: 0.35 };
// The order the fields are written in (anything else found in the file is kept after them)
const FIELDS = ['type', 'port', 'x', 'y', 'z', 'yaw_deg', 'pitch_deg', 'fov_deg', 'range_min', 'range_max', 'stop_distance', 'pico'];
const PINS = { vl53l0x: ['xshut'], hcsr04: ['trig', 'echo'] };
const r3 = (n) => Math.round(n * 1000) / 1000;

export function createSensorsTab({ status }) {
  let sensors = [];        // [{ name, nameEdited, found, ...fields }]
  let loaded = { file: '', saved: false, yaml: '', lidar_device: false };
  let changed = false;
  let locked = false;       // sensors.yaml is broken: fix it in the File tab first
  let selected = null;
  let simulated = false;
  let object = { ...OBJECT0, ...OBJECTS.chair };
  let errorCb = () => {};
  let visible = false;
  let scan = null;          // live lidar points in base_link: [[x, y]]
  let scanHz = 0;
  let scanAt = 0;

  const map = createSensorMap($('smap'), {
    onSelect: (name) => { selected = name; renderList(); redraw(); },
    onMove: (name, x, y) => {
      if (locked) return name;
      const s = sensors.find((t) => t.name === name);
      Object.assign(s, { x, y });
      const old = s.name;
      rename(s);
      const card = document.querySelector(`#slist .sensor[data-name="${old}"]`);
      if (card) {
        card.dataset.name = s.name;
        card.querySelector('.sub').textContent = s.name;
        card.querySelector('input.name').value = s.name;
        card.querySelector('.pos').textContent = posText(s);
      }
      touched();
      return s.name;
    },
    onObject: (x, y) => { Object.assign(object, { x, y }); redraw(); },
  });
  const view3d = createSensorView3d($('view3d'));

  // ---------- load ----------
  async function load() {
    let api;
    try { api = await (await fetch('api/sensors', { cache: 'no-store' })).json(); } catch { return; }
    loaded = api;
    changed = false;
    locked = !!api.error;
    $('s-add').disabled = locked;
    $('s-locked').hidden = !locked;
    if (visible) $('save').disabled = locked;
    sensors = Object.entries(api.sensors).map(([name, s]) => ({ ...s, name, found: null }));
    for (const s of sensors) s.nameEdited = s.name !== defaultName(s, taken(s));
    if (!sensors.some((s) => s.name === selected)) selected = sensors[0] ? sensors[0].name : null;
    renderList();
    redraw();
    if (api.error) {
      status(`sensors.yaml: ${api.error}. Fix it in the File tab.`, 'bad');
      errorCb();
    }
    await checkLidar();       // through rosbridge: may take a moment, or not answer
    renderList();
    redraw();
  }

  // The lidar: plugged in (its device exists), simulated (fake_lidar running) or offline.
  // The Pico sensors wait for the Pico (step 2 of the project).
  async function checkLidar() {
    const nodes = await call('/rosapi/nodes', 'rosapi_msgs/srv/Nodes', {});
    simulated = !!(nodes && nodes.nodes && nodes.nodes.includes('/fake_lidar'));
  }
  function badge(s) {
    if (!isLidar(s)) return ['wait', '<i class="fa-solid fa-hourglass-half"></i> waiting for the Pico'];
    if (loaded.lidar_device) return ['ok', `<i class="fa-solid fa-plug-circle-check"></i> plugged in${hz()}`];
    if (simulated) return ['sim', `<i class="fa-solid fa-flask"></i> simulated${hz()}`];
    return ['bad', '<i class="fa-solid fa-plug-circle-xmark"></i> offline'];
  }

  const hz = () => (scan && scanHz ? ` · /scan ${Math.round(scanHz)} Hz` : '');

  // The lidar's points, at most twice a second, in base_link from where the lidar is now
  subscribe('/scan', 'sensor_msgs/msg/LaserScan', (m) => {
    const s = sensors.find(isLidar);
    if (!s || !visible) return;
    const pts = [];
    const c = Math.cos(s.yaw_deg * Math.PI / 180), n = Math.sin(s.yaw_deg * Math.PI / 180);
    for (let i = 0; i < m.ranges.length; i += 2) {
      const r = m.ranges[i];
      if (r == null || !Number.isFinite(r) || r < m.range_min || r > m.range_max) continue;
      const a = m.angle_min + i * m.angle_increment;
      const lx = r * Math.cos(a), ly = r * Math.sin(a);
      pts.push([s.x + lx * c - ly * n, s.y + lx * n + ly * c]);
    }
    const first = !scan;
    scan = pts;
    scanHz = m.scan_time > 0 ? 1 / m.scan_time : 0;   // the lidar's own rate (we only get 2 a second)
    scanAt = Date.now();
    if (first) renderList();
    redraw();
  }, 500);
  setInterval(() => { if (scan && Date.now() - scanAt > 3000) { scan = null; renderList(); redraw(); } }, 1000);

  // ---------- state ----------
  const taken = (except) => new Set(sensors.filter((t) => t !== except).map((t) => t.name));
  function rename(s) {
    if (s.nameEdited) return;
    const old = s.name;
    s.name = defaultName(s, taken(s));
    if (selected === old) selected = s.name;
  }
  function touched() {
    changed = true;
    status('Changed: Save to keep it (the sensor poses follow at once).', 'warn');
    redraw();
  }

  let raf = 0;
  function redraw() {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      const hits = Object.fromEntries(sensors.map((s) => [s.name, s.found === false ? null
        : sees(s, object.x, object.y, object.size, object.heightTop)]));
      const cov = coverage(sensors);
      const state = { sensors, selected, object, hits, cov, showGaps: $('s-gaps').checked, fullRange: $('s-far').checked, scan };
      map.draw(state);
      if (!$('view3d').hidden && $('views').className !== 'views v-top') view3d.draw(state);
      stats(cov);
      readings(hits);
    });
  }

  function stats(cov) {
    $('s-near').textContent = sensors.length ? Math.round(cov.near * 100) + '%' : '0%';
    $('s-farv').textContent = sensors.length ? Math.round(cov.far * 100) + '%' : '0%';
    const found = sensors.filter((s) => badge(s)[0] === 'ok' || badge(s)[0] === 'sim').length;
    $('s-found').textContent = `${found} / ${sensors.length}`;
    const side = (a) => (a === 0 ? 'front' : Math.abs(a) === 180 ? 'back' : `${Math.abs(a)}° ${a > 0 ? 'right' : 'left'}`);
    $('s-blind').innerHTML = cov.blind.length
      ? 'Blind within 50 cm: ' + cov.blind.map(([a, b]) => `<b>${side(a)} to ${side(b)}</b>`).join(', ') + '.'
      : 'No blind spots within 50 cm.';
  }

  function readings(hits) {
    for (const el of document.querySelectorAll('#slist .sensor')) {
      const d = hits[el.dataset.name];
      el.classList.toggle('hit', d != null);
      el.querySelector('.reading').textContent = d != null ? `${d.toFixed(2)} m` : '—';
    }
  }

  // ---------- cards ----------
  function slider(s, key, label, min, max, step, fmt, scale = 1) {
    return `<div class="row"><label>${label}</label><div class="slider"><input type="range" data-k="${key}" data-scale="${scale}" ` +
           `min="${min}" max="${max}" step="${step}" value="${s[key] / scale}"><b>${fmt(s[key])}</b></div></div>`;
  }
  const FMT = {
    yaw_deg: (v) => sideText(v),
    pitch_deg: (v) => (v ? `${Math.round(v)}° down` : 'level'),
    fov_deg: (v) => `${Math.round(v)}°`,
    range_max: (v) => `${v.toFixed(2)} m`,
    z: (v) => `${Math.round(v * 1000)} mm`,
    stop_distance: (v) => (v ? `${Math.round(v * 100)} cm` : 'never'),
  };
  function pinSelect(s, pin, used) {
    const opts = Array.from({ length: 29 }, (_, g) => `<option value="${g}"${s.pico[pin] === g ? ' selected' : ''}>GP${g}</option>`).join('');
    const clash = used.get(s.pico[pin]) > 1 ? ' clash' : '';
    return `<label class="pin${clash}">${pin} <select data-pin="${pin}">${opts}</select></label>`;
  }

  const posText = (s) => `${Math.round(Math.abs(s.x) * 1000)} mm ${s.x >= 0 ? 'ahead' : 'behind'}, ` +
    `${Math.round(Math.abs(s.y) * 1000)} mm ${s.y >= 0 ? 'left' : 'right'} — drag it on the map`;

  function renderList() {
    const box = $('slist');
    box.textContent = '';
    const used = new Map();
    for (const s of sensors) for (const p of Object.values(s.pico || {})) used.set(p, (used.get(p) || 0) + 1);
    for (const s of sensors) {
      const T = TYPES[s.type];
      const [cls, text] = badge(s);
      const el = document.createElement('div');
      el.className = 'sensor' + (s.name === selected ? ' sel' : '');
      el.dataset.name = s.name;
      el.style.setProperty('--c', T.colour);
      el.innerHTML = `
        <div class="top"><span class="title">${T.label}</span><span class="sub"></span><span class="reading">—</span>
          <span class="badge ${cls}">${text}</span></div>
        <div class="edit">
          <div class="row"><label><i class="fa-solid fa-tag"></i>name</label><input class="name" spellcheck="false"></div>
          ${slider(s, 'yaw_deg', '<i class="fa-solid fa-compass"></i>points to', -180, 180, 1, FMT.yaw_deg)}
          ${isLidar(s) ? '' : slider(s, 'pitch_deg', '<i class="fa-solid fa-arrow-down"></i>tilt down', -10, 80, 1, FMT.pitch_deg)}
          ${slider(s, 'fov_deg', `<i class="fa-solid fa-eye"></i>${isLidar(s) ? 'not hidden by R2' : 'field of view'}`, T.fov[0], T.fov[1], 1, FMT.fov_deg)}
          ${slider(s, 'range_max', '<i class="fa-solid fa-ruler"></i>range', T.range[0], T.range[1], 0.05, FMT.range_max)}
          ${slider(s, 'z', '<i class="fa-solid fa-arrows-up-down"></i>height', 0.03, 1.0, 0.005, FMT.z)}
          ${isLidar(s) ? '' : slider(s, 'stop_distance', '<i class="fa-solid fa-hand"></i>stop when closer', 0, Math.min(0.8, s.range_max - 0.01), 0.01, FMT.stop_distance)}
          ${isLidar(s) ? `<div class="row"><label><i class="fa-brands fa-usb"></i>port</label><span class="sub port"></span></div>`
            : `<div class="row"><label><i class="fa-solid fa-microchip"></i>on the Pico</label><div class="pins">${PINS[s.type].map((p) => pinSelect(s, p, used)).join('')}</div></div>`}
          <div class="row"><label><i class="fa-solid fa-location-dot"></i>position</label>
            <span class="sub pos">${posText(s)}</span></div>
          <div class="row"><span></span><button class="remove"><i class="fa-solid fa-trash"></i>Remove</button></div>
        </div>`;
      el.querySelector('.sub').textContent = s.name;
      if (el.querySelector('.port')) el.querySelector('.port').textContent = s.port;
      const name = el.querySelector('.name');
      name.value = s.name;
      name.addEventListener('change', () => {
        const n = uniqueName(name.value, taken(s));
        if (!n) {
          name.value = s.name;
          return status('That name is empty, already used, or not lower case letters, digits and _.', 'bad');
        }
        if (selected === s.name) selected = n;
        s.name = n;
        s.nameEdited = n !== defaultName(s, taken(s));
        renderList();
        touched();
      });
      el.addEventListener('click', (e) => {
        if (e.target.closest('input, select, button') || s.name === selected) return;
        selected = s.name; renderList(); redraw();
      });
      el.querySelectorAll('input[type=range]').forEach((inp) => inp.addEventListener('input', () => {
        const k = inp.dataset.k;
        s[k] = r3(Number(inp.value) * Number(inp.dataset.scale));
        inp.nextElementSibling.textContent = FMT[k](s[k]);
        if (k === 'yaw_deg' || k === 'pitch_deg') {
          const old = s.name;
          rename(s);
          if (s.name !== old) { el.dataset.name = s.name; el.querySelector('.sub').textContent = s.name; name.value = s.name; }
        }
        if (k === 'range_max') s.stop_distance = Math.min(s.stop_distance, r3(s.range_max - 0.01));
        touched();
      }));
      el.querySelectorAll('select[data-pin]').forEach((sel) => sel.addEventListener('change', () => {
        s.pico[sel.dataset.pin] = Number(sel.value);
        renderList();
        touched();
      }));
      el.querySelector('.remove').addEventListener('click', () => {
        sensors = sensors.filter((t) => t !== s);
        if (selected === s.name) selected = sensors[0] ? sensors[0].name : null;
        renderList();
        touched();
      });
      if (locked) el.querySelectorAll('input, select, button').forEach((c) => { c.disabled = true; });
      box.append(el);
    }
    $('s-addtype').querySelector('[value=rplidar_c1]').disabled = sensors.some(isLidar);
  }

  function freePins(n) {
    const used = new Set(sensors.flatMap((s) => Object.values(s.pico || {})));
    const out = [];
    for (let g = 0; g <= 28 && out.length < n; g++) if (!used.has(g)) out.push(g);
    return out;
  }
  $('s-add').addEventListener('click', () => {
    const type = $('s-addtype').value, T = TYPES[type];
    const s = { type, x: 0, y: R2.bodyR + 0.01, z: 0.3, yaw_deg: 90, pitch_deg: 0, fov_deg: T.fovDeg, range_max: T.rangeMax,
                range_min: type === 'hcsr04' ? 0.02 : type === 'vl53l0x' ? 0.03 : 0.05, stop_distance: 0, found: null, nameEdited: false };
    if (type === 'rplidar_c1') Object.assign(s, { port: '/dev/r2-lidar', x: 0.17, y: 0, z: 0.11, yaw_deg: 0 });
    else {
      const pins = freePins(PINS[type].length);
      if (pins.length < PINS[type].length) return status('No free Pico pins left.', 'bad');
      s.pico = Object.fromEntries(PINS[type].map((p, i) => [p, pins[i]]));
    }
    s.name = defaultName(s, taken(null));
    sensors.push(s);
    selected = s.name;
    renderList();
    touched();
  });

  // ---------- file ----------
  function toYaml() {
    let out = '# R2 sensors, saved from the web console (Setup -> Sensors). Hand edits are fine too.\n' +
              '# Metres and degrees. x forward, y left, z up from the floor under the body centre\n' +
              '# (base_link, REP 103). yaw_deg + = left, pitch_deg + = down.\n';
    for (const s of sensors) {
      out += `${s.name}:\n`;
      const keys = [...FIELDS, ...Object.keys(s).filter((k) => !FIELDS.includes(k) && !['name', 'nameEdited', 'found'].includes(k))];
      for (const k of keys) {
        if (s[k] === undefined) continue;
        if (isLidar(s) && ['pitch_deg', 'stop_distance', 'pico'].includes(k)) continue;
        if (k === 'pico') out += `  pico: {${Object.entries(s.pico).map(([p, g]) => `${p}: ${g}`).join(', ')}}\n`;
        else out += `  ${k}: ${typeof s[k] === 'number' ? r3(s[k]) : s[k]}\n`;
      }
    }
    return out;
  }

  async function save(text) {
    if (text == null && locked) { status('sensors.yaml is broken: fix it in the File tab first.', 'bad'); return false; }
    const body = JSON.stringify({ yaml: text ?? toYaml() });
    let res;
    try { res = await (await fetch('api/sensors', { method: 'POST', body })).json(); } catch { status('Not saved: the Pi does not answer.', 'bad'); return false; }
    if (res.error) { status(res.error, 'bad'); return false; }
    changed = false;
    loaded = { ...loaded, file: res.file, saved: true, yaml: text ?? toYaml() };
    status(`Saved in ${res.file}. The sensor poses follow at once.`, 'ok');
    return true;
  }

  // ---------- page wiring ----------
  $('s-zin').addEventListener('click', () => map.zoom(1 / 1.4));
  $('s-zout').addEventListener('click', () => map.zoom(1.4));
  $('s-reset').addEventListener('click', () => { map.reset(); object = { ...object, ...OBJECT0 }; redraw(); });
  $('s-gaps').addEventListener('change', redraw);
  $('s-far').addEventListener('change', redraw);
  // Top / 3D / Both, maximize, and the model (the console's choice by default)
  const setView = (v) => {
    $('views').className = 'views v-' + v;
    document.querySelectorAll('#s-view button').forEach((b) => b.classList.toggle('on', b.dataset.v === v));
    try { localStorage.setItem('r2web.sensorView', v); } catch { /* private window */ }
    view3d.resize();
    redraw();
  };
  document.querySelectorAll('#s-view button').forEach((b) => b.addEventListener('click', () => setView(b.dataset.v)));
  const setMax = (on) => {
    $('viewer').classList.toggle('max', on);
    $('s-max').innerHTML = on ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-expand"></i>';
    $('s-max').title = on ? 'close (Esc)' : 'maximize';
    view3d.resize();
  };
  $('s-max').addEventListener('click', () => setMax(!$('viewer').classList.contains('max')));
  addEventListener('keydown', (e) => { if (e.key === 'Escape') setMax(false); });
  const modelSel = $('s-model');
  modelSel.innerHTML = Object.entries(MODELS).map(([k, m]) => `<option value="${k}">${m.label}</option>`).join('');
  let pref = { model: 'simple', view: 'both' };
  try { pref = { model: localStorage.getItem('r2web.model') || 'simple', view: localStorage.getItem('r2web.sensorView') || 'both' }; } catch { /* private window */ }
  modelSel.value = MODELS[pref.model] ? pref.model : 'simple';
  modelSel.addEventListener('change', () => view3d.setModel(modelSel.value).catch((e) => status(`Could not load the model: ${e}`, 'bad')));
  view3d.setModel(modelSel.value).catch(() => {});
  setView(['top', '3d', 'both'].includes(pref.view) ? pref.view : 'both');

  const objSel = $('s-object');
  objSel.innerHTML = Object.entries(OBJECTS).map(([k, o]) => `<option value="${k}">${o.label}</option>`).join('');
  objSel.addEventListener('change', () => { object = { ...object, ...OBJECTS[objSel.value] }; redraw(); });
  setInterval(async () => {
    if (!visible) return;
    try {
      const api = await (await fetch('api/sensors', { cache: 'no-store' })).json();
      const before = loaded.lidar_device;
      loaded.lidar_device = api.lidar_device;
      const sim = simulated;
      await checkLidar();
      if (before !== api.lidar_device || sim !== simulated) { renderList(); redraw(); }
    } catch { /* restarting */ }
  }, 5000);

  return {
    load,
    show() { visible = true; $('save').disabled = locked; view3d.resize(); redraw(); },
    hide() { visible = false; $('save').disabled = false; },
    toYaml,
    fileText: () => (changed && !locked ? toYaml() : loaded.yaml),
    fileName: () => loaded.file + (loaded.saved ? '' : ' (the package default: saving creates ~/.config/ros2d2/sensors.yaml)'),
    save,
    onError(cb) { errorCb = cb; },
  };
}
