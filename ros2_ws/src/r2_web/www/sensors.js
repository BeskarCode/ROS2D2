// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> Sensors: place the lidar and the distance sensors on the droid, see what they
// cover and what they miss, and save sensors.yaml (the TF follows at once on the Pi).
// Sensors are kept as in sensors.yaml (metres, degrees, ROS axes: + yaw = left).
import { MODELS } from './models.js';
import { call, publish, subscribe } from './rosbridge.js';
import { createSensorMap } from './sensormap.js';
import { createSensorView3d } from './sensorview3d.js';
import { OFF_COLOUR, isConnected, picoPill, sensorBadge } from './picostate.js';
import { LIDAR_MOTOR, lastFrontInUse, lidarInfoText, lidarModes, lidarYamlValue, PALETTE, sensorColour } from './sensormath.js';
import { CONNECTORS, PICO_GPIO, R2, TYPES, beamDefaults, connectorOf, connectorPins, coverage, freeConnector, defaultName, isLidar, nearestPoint, sees, sideText, uniqueName } from './sensormath.js';

const $ = (id) => document.getElementById(id);
const OBJECTS = {
  none: { label: 'none', none: true },
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
  let object = { ...OBJECT0, ...OBJECTS.none };
  let errorCb = () => {};
  let visible = false;
  // beams hidden on the map and in 3D (the sensor's dot and the lidar's points stay), per browser
  let hidden = new Set();
  try { hidden = new Set(JSON.parse(localStorage.getItem('r2web.hiddenBeams') || '[]')); } catch { /* private window */ }
  const moveHidden = (from, to) => {
    let moved = false;
    for (const k of ['', '#points']) if (hidden.delete(from + k)) { hidden.add(to + k); moved = true; }
    if (moved) saveHidden();
  };
  // "Connected only": hide the cards and beams of the sensors that are not measuring, per browser
  let onlyConnected = false;
  try { onlyConnected = localStorage.getItem('r2web.onlyConnected') === '1'; } catch { /* private window */ }
  const saveHidden = () => { try { localStorage.setItem('r2web.hiddenBeams', JSON.stringify([...hidden])); } catch { /* private window */ } };
  let scan = null;          // live lidar points in base_link: [[x, y]]
  let scanHz = 0;
  let scanTurns = null;      // turns per second, unrounded, and points per turn (the lidar's info line)
  let scanPoints = null;
  let lidarInfo = null;      // /lidar/info: what the lidar says about itself (model, firmware, modes...)
  let scanAt = 0;
  let pico = null;          // /pico/state from r2_pico_bridge, and when it came
  let picoAt = 0;
  let simWorld = false;     // the navigation simulator publishes the /range topics instead
  const ranges = {};        // name -> { range (m, Infinity = nothing in range), at }
  const rangeSubs = new Set();

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
    onHover: (name, cx, cy) => hover(name, cx, cy),
  });
  const view3d = createSensorView3d($('view3d'), { onHover: (name, cx, cy) => hover(name, cx, cy) });

  // The sensor under the mouse (on the map, in 3D or its card): highlighted everywhere, and a
  // tooltip that says which one it is, when the mouse is over a viewer
  let hovered = null;
  const tip = document.createElement('div');
  tip.className = 'stip';
  tip.hidden = true;
  document.body.append(tip);
  function hover(name, cx, cy) {
    const s = name && sensors.find((t) => t.name === name);
    if (s && cx != null) {
      const [, text] = badge(s);
      tip.innerHTML = `<b>${TYPES[s.type].label}</b> <span class="sub"></span><br>${text}`;
      tip.querySelector('.sub').textContent = s.name;
      tip.style.left = `${cx + 14}px`;
      tip.style.top = `${cy + 14}px`;
      tip.hidden = false;
    } else tip.hidden = true;
    const n = s ? s.name : null;
    if (n === hovered) return;
    hovered = n;
    for (const el of document.querySelectorAll('#slist .sensor')) el.classList.toggle('hover', el.dataset.name === hovered);
    redraw();
  }

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
    subscribeRanges();
    await checkLidar();       // through rosbridge: may take a moment, or not answer
    renderList();
    redraw();
  }

  // The lidar: plugged in (its device exists), simulated (fake_lidar running) or offline.
  // The Pico's sensors: from /pico/state and /range/<name> (see picostate.js).
  async function checkLidar() {
    const nodes = await call('/rosapi/nodes', 'rosapi_msgs/srv/Nodes', {});
    simulated = !!(nodes && nodes.nodes && nodes.nodes.includes('/fake_lidar'));
    simWorld = !!(nodes && nodes.nodes && nodes.nodes.includes('/sim_world'));
  }
  const ICONS = { ok: 'fa-ruler-horizontal', sim: 'fa-flask', bad: 'fa-plug-circle-xmark', off: 'fa-circle-minus', wait: 'fa-hourglass-half' };
  function reading(name, now) {
    const r = ranges[name];
    return r ? { range: r.range, ageMs: now - r.at } : null;
  }
  function badge(s) {
    if (!isLidar(s)) {
      const now = Date.now();
      const b = sensorBadge(s.name, pico, reading(s.name, now), now - picoAt, simWorld);
      return [b.cls, `<i class="fa-solid ${ICONS[b.cls]}"></i> ${b.text}`];
    }
    if (loaded.lidar_device) return ['ok', `<i class="fa-solid fa-plug-circle-check"></i> plugged in${hz()}`];
    if (simulated) return ['sim', `<i class="fa-solid fa-flask"></i> simulated${hz()}`];
    return ['bad', '<i class="fa-solid fa-plug-circle-xmark"></i> offline'];
  }

  const lidarPointsShown = () => { const l = sensors.find(isLidar); return !l || !hidden.has(l.name + '#points'); };
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
    // the lidar's own rate (we only get 2 a second); it runs at about 10.5 Hz, so only move the
    // shown number when it is 1 Hz off, or the badge flickers between 10 and 11
    const hzNow = m.scan_time > 0 ? 1 / m.scan_time : 0;
    if (!scanHz || Math.abs(hzNow - scanHz) >= 1) scanHz = Math.round(hzNow);
    scanTurns = hzNow ? (scanTurns ? scanTurns * 0.8 + hzNow * 0.2 : hzNow) : scanTurns;
    scanPoints = m.ranges.length;
    const info = document.querySelector('.sensor .lidarinfo');
    if (info) info.textContent = lidarInfoText(lidarInfo, scanTurns, scanPoints);
    scanAt = Date.now();
    if (first) renderList();
    redraw();
  }, 500);
  setInterval(() => { if (scan && Date.now() - scanAt > 3000) { scan = null; scanTurns = null; renderList(); redraw(); } }, 1000);
  // what the lidar says about itself (the driver publishes it once, latched); fills the scan modes
  subscribe('/lidar/info', 'std_msgs/msg/String', (m) => {
    try { lidarInfo = JSON.parse(m.data); } catch { return; }
    renderList();
  });

  // ---------- state ----------
  const taken = (except) => new Set(sensors.filter((t) => t !== except).map((t) => t.name));
  function rename(s) {
    if (s.nameEdited) return;
    const old = s.name;
    s.name = defaultName(s, taken(s));
    if (selected === old) selected = s.name;
    if (s.name !== old) moveHidden(old, s.name);
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
      const hits = Object.fromEntries(sensors.map((s) => [s.name, s.found === false || object.none ? null
        : sees(s, object.x, object.y, object.size, object.heightTop)]));
      const cov = coverage(sensors);
      const now = Date.now();
      const live = Object.fromEntries(sensors.map((s) => {
        const b = isLidar(s) ? null : badge(s)[0], r = reading(s.name, now);
        return [s.name, (b === 'ok' || b === 'sim') && r ? r.range : null];
      }));
      const shown = onlyConnected ? sensors.filter((s) => isConnected(badge(s)[0])) : sensors;
      const colours = Object.fromEntries(sensors.map((s) => [s.name, colourOf(s)]));
      const state = { sensors: shown, colours, selected, object: object.none ? null : object, hits, cov, showGaps: $('s-gaps').checked, fullRange: $('s-far').checked, scan: lidarPointsShown() ? scan : null, near: nearestPoint(scan), readings: live, hidden, hovered };
      map.draw(state);
      if (!$('view3d').hidden && $('views').className !== 'views v-top') view3d.draw(state);
      stats(cov);
      readings(hits);
      badges();
    });
  }

  // its own colour (or its type's), or its grey when a Pico sensor is not measuring
  const IGNORED_COLOUR = '#6e7681';
  const colourOf = (s) => (s.enabled === false ? IGNORED_COLOUR
    : OFF_COLOUR[s.type] && !isConnected(badge(s)[0]) ? OFF_COLOUR[s.type] : sensorColour(s));

  // Refresh only the badges (the cards hold inputs: rebuilding them would lose the focus)
  // and, with "Connected only", hide the cards of the sensors that are not measuring
  function badges() {
    let off = 0;
    for (const s of sensors) {
      const card = document.querySelector(`#slist .sensor[data-name="${s.name}"]`);
      const el = card && card.querySelector('.badge');
      if (!el) continue;
      const [cls, text] = badge(s);
      // while the mouse is in the list (or dragging a slider out of it) the cards stay where they are
      const hide = holdList ? card.hidden : onlyConnected && !isConnected(cls);
      const c = colourOf(s);
      if (card.style.getPropertyValue('--c') !== c) card.style.setProperty('--c', c);
      if (card.hidden !== hide) card.hidden = hide;
      off += hide;
      if (el.className !== `badge ${cls}`) el.className = `badge ${cls}`;
      if (el.innerHTML !== text) el.innerHTML = text;
    }
    // the connected ones first (only on screen: the file keeps its order)
    const box = $('slist');
    const want = [...sensors].sort((a, b) => isConnected(badge(b)[0]) - isConnected(badge(a)[0]))
      .map((s) => box.querySelector(`.sensor[data-name="${s.name}"]`)).filter(Boolean);
    if (!holdList && want.some((el, i) => box.children[i] !== el)) box.append(...want);
    const n = $('s-hiddenn');
    const msg = off ? `${off} not connected, hidden` : '';
    if (n.textContent !== msg) n.textContent = msg;
  }
  // Hold the list still while the mouse is in it or a button is held (a slider being dragged);
  // it catches up when the mouse leaves
  let mouseInList = false, pressing = false, holdList = false;
  const updateHold = () => {
    const hold = mouseInList || pressing;
    if (hold === holdList) return;
    holdList = hold;
    if (!hold) redraw();
  };
  $('slist').addEventListener('pointerenter', () => { mouseInList = true; updateHold(); });
  $('slist').addEventListener('pointerleave', () => { mouseInList = false; updateHold(); });
  $('slist').addEventListener('pointerdown', () => { pressing = true; updateHold(); });
  addEventListener('pointerup', () => { pressing = false; updateHold(); });
  addEventListener('pointercancel', () => { pressing = false; updateHold(); });
  const showOnlyConnected = (on) => {
    onlyConnected = on;
    $('s-connected').classList.toggle('on', on);
    try { localStorage.setItem('r2web.onlyConnected', on ? '1' : '0'); } catch { /* private window */ }
    redraw();
  };
  $('s-connected').addEventListener('click', () => showOnlyConnected(!onlyConnected));
  showOnlyConnected(onlyConnected);

  // Live: the Pico's state and each Pico sensor's /range, drawn at most 4 times a second
  let liveTimer = null;
  function live() {
    if (!visible || liveTimer) return;
    liveTimer = setTimeout(() => { liveTimer = null; redraw(); }, 250);
  }
  subscribe('/pico/state', 'std_msgs/msg/String', (m) => {
    try { pico = JSON.parse(m.data); picoAt = Date.now(); } catch { return; }
    live();
  });
  // The header's Pico pill (whatever tab is open)
  function showPico() {
    const el = $('picopill');
    if (!el) return;
    const p = picoPill(pico, Date.now() - picoAt);
    el.hidden = simWorld;
    el.className = 'pill ' + p.cls;
    el.innerHTML = '<i class="fa-solid fa-microchip"></i>';
    el.append(p.text);
  }
  // so a Pico or a reading that went quiet shows it
  setInterval(() => { showPico(); live(); }, 1000);
  function subscribeRanges() {
    for (const s of sensors) {
      if (isLidar(s) || rangeSubs.has(s.name)) continue;
      const name = s.name;
      rangeSubs.add(name);
      // rosbridge sends inf (nothing in range) as null
      subscribe(`/range/${name}`, 'sensor_msgs/msg/Range', (m) => {
        ranges[name] = { range: m.range == null ? Infinity : m.range, at: Date.now() };
        live();
      }, 100);
    }
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
  // the angles also get a box to type the degrees in
  const TYPED = ['yaw_deg', 'pitch_deg', 'fov_deg'];
  function slider(s, key, label, min, max, step, fmt, scale = 1) {
    const box = TYPED.includes(key) ? `<input type="number" class="num" data-for="${key}" min="${min}" max="${max}" step="${step}" value="${s[key] / scale}">°` : '';
    return `<div class="row"><label>${label}</label><div class="slider"><input type="range" data-k="${key}" data-scale="${scale}" ` +
           `min="${min}" max="${max}" step="${step}" value="${s[key] / scale}">${box}<b>${fmt(s[key])}</b></div></div>`;
  }
  // quick buttons under "points to" (+ = left, as in ROS)
  const SNAPS = [[90, '90° left'], [0, 'ahead'], [-90, '90° right'], [180, 'back']];
  const FMT = {
    yaw_deg: (v) => sideText(v),
    pitch_deg: (v) => (v ? `${Math.round(v)}° down` : 'level'),
    fov_deg: (v) => `${Math.round(v)}°`,
    range_max: (v) => `${v.toFixed(2)} m`,
    z: (v) => `${Math.round(v * 1000)} mm`,
    stop_distance: (v) => (v ? `${Math.round(v * 100)} cm` : 'never'),
  };
  function pinSelect(s, pin, used) {
    const opts = PICO_GPIO.map((g) => `<option value="${g}"${s.pico[pin] === g ? ' selected' : ''}>GP${g}</option>`).join('');
    const clash = used.get(s.pico[pin]) > 1 ? ' clash' : '';
    return `<label class="pin${clash}">${pin} <select data-pin="${pin}">${opts}</select></label>`;
  }
  // The board connector it is plugged into; "other pins (no board)" shows the GPIO pickers
  function connectorRow(s, used) {
    const conn = s.noBoard ? null : connectorOf(s);
    const clash = Object.values(s.pico).some((g) => used.get(g) > 1) ? ' clash' : '';
    const opts = CONNECTORS[s.type].map(([n, pins]) =>
      `<option value="${n}"${n === conn ? ' selected' : ''}>${n} · GP${Object.values(pins).join('/')}</option>`).join('') +
      `<option value=""${conn ? '' : ' selected'}>other pins (no board)</option>`;
    const row = `<div class="row"><label><i class="fa-solid fa-plug"></i>connector</label><div class="pins">` +
      `<label class="pin${clash}"><select class="conn">${opts}</select></label></div></div>`;
    return conn ? row : row + `<div class="row"><label><i class="fa-solid fa-microchip"></i>on the Pico</label>` +
      `<div class="pins">${PINS[s.type].map((p) => pinSelect(s, p, used)).join('')}</div></div>`;
  }

  const posText = (s) => `${Math.round(Math.abs(s.x) * 1000)} mm ${s.x >= 0 ? 'ahead' : 'behind'}, ` +
    `${Math.round(Math.abs(s.y) * 1000)} mm ${s.y >= 0 ? 'left' : 'right'} — drag it on the map`;

  function renderList() {
    const box = $('slist');
    // rebuilt in the order (and with the cards hidden) shown now: badges() moves them later
    const was = [...box.children].map((c) => c.dataset.name);
    const wasHidden = new Set([...box.children].filter((c) => c.hidden).map((c) => c.dataset.name));
    const at = (s) => { const i = was.indexOf(s.name); return i < 0 ? was.length : i; };
    box.textContent = '';
    const used = new Map();
    for (const s of sensors) for (const p of Object.values(s.pico || {})) used.set(p, (used.get(p) || 0) + 1);
    for (const s of [...sensors].sort((a, b) => at(a) - at(b))) {
      const T = TYPES[s.type];
      const [cls, text] = badge(s);
      const el = document.createElement('div');
      el.className = 'sensor' + (s.name === selected ? ' sel' : '') + (s.name === hovered ? ' hover' : '');
      el.addEventListener('mouseenter', () => hover(s.name));
      el.addEventListener('mouseleave', () => hover(null));
      el.dataset.name = s.name;
      el.style.setProperty('--c', colourOf(s));
      el.innerHTML = `
        <div class="top"><span class="title">${T.label}</span><span class="sub"></span><span class="reading">—</span>
          <span class="badge ${cls}">${text}</span>${s.enabled === false ? '<span class="badge off">ignored</span>' : ''}
          <button class="eye use${s.enabled === false ? ' off' : ''}" title="${s.enabled === false ? 'Ignored: navigation does not use it. Click to use it again' : 'In use. Click to ignore its readings (it keeps measuring)'}">
            <i class="fa-solid ${s.enabled === false ? 'fa-toggle-off' : 'fa-toggle-on'}"></i></button>
          <button class="eye${hidden.has(s.name) ? ' off' : ''}" title="${hidden.has(s.name) ? 'Show' : 'Hide'} its beam on the map">
            <i class="fa-solid ${hidden.has(s.name) ? 'fa-eye-slash' : 'fa-eye'}"></i></button>
          ${!isLidar(s) && connectorOf(s) ? `<button class="eye idb" title="Identify: ${connectorOf(s)}'s LED on the board blinks for 5 s">
            <i class="fa-solid fa-lightbulb"></i></button>` : ''}
          ${isLidar(s) ? `<button class="eye pts${hidden.has(s.name + '#points') ? ' off' : ''}" title="${hidden.has(s.name + '#points') ? 'Show' : 'Hide'} what it measures (its points) on the map">
            <i class="fa-solid ${hidden.has(s.name + '#points') ? 'fa-circle' : 'fa-braille'}"></i></button>` : ''}</div>
        <div class="edit">
          <div class="row"><label><i class="fa-solid fa-tag"></i>name</label><input class="name" spellcheck="false"></div>
          <div class="row"><label><i class="fa-solid fa-palette"></i>colour</label><span class="colour">
            <button class="typecol"${s.colour ? '' : ' hidden'} title="Back to the ${T.label}'s colour"><i class="fa-solid fa-rotate-left"></i>${T.label}'s</button>
            ${PALETTE.map((c) => { const by = sensors.find((o) => o !== s && o.colour === c);
              return `<button class="sw${s.colour === c ? ' on' : ''}${by ? ' taken' : ''}" data-c="${c}" style="--sw:${c}" title="${by ? `${c}, used by ${by.name}` : c}"></button>`; }).join('')}</span></div>
          ${slider(s, 'yaw_deg', '<i class="fa-solid fa-compass"></i>points to', -180, 180, 1, FMT.yaw_deg)}
          <div class="row"><span></span><div class="snaps">${SNAPS.map(([v, t]) =>
            `<button data-yaw="${v}" title="Point it ${t}"${s.yaw_deg === v || (v === 180 && s.yaw_deg === -180) ? ' class="on"' : ''}>${t}</button>`).join('')}</div></div>
          ${isLidar(s) ? '' : slider(s, 'pitch_deg', '<i class="fa-solid fa-arrow-down"></i>tilt down', -10, 80, 1, FMT.pitch_deg)}
          ${slider(s, 'fov_deg', `<i class="fa-solid fa-eye"></i>${isLidar(s) ? 'not hidden by R2' : 'field of view'}`, T.fov[0], T.fov[1], 1, FMT.fov_deg)}
          ${slider(s, 'range_max', '<i class="fa-solid fa-ruler"></i>range', T.range[0], T.range[1], 0.05, FMT.range_max)}
          ${slider(s, 'z', '<i class="fa-solid fa-arrows-up-down"></i>height', 0.03, 1.0, 0.005, FMT.z)}
          ${isLidar(s) ? '' : slider(s, 'stop_distance', '<i class="fa-solid fa-hand"></i>stop when closer', 0, Math.min(0.8, s.range_max - 0.01), 0.01, FMT.stop_distance)}
          ${isLidar(s) ? `<div class="row"><label><i class="fa-brands fa-usb"></i>port</label><span class="sub port"></span></div>
            ${lidarRows(s)}`
            : connectorRow(s, used)}
          <div class="row"><label><i class="fa-solid fa-location-dot"></i>position</label>
            <span class="sub pos">${posText(s)}</span></div>
          <div class="row"><span></span><span><button class="defaults" title="field of view and range back to the ${T.label}'s own (${T.fovDeg}°, ${T.rangeMax} m)"><i class="fa-solid fa-rotate-left"></i>Defaults</button>
            <button class="remove" title="Take this sensor out of sensors.yaml (Save to keep it)"><i class="fa-solid fa-trash"></i>Remove</button></span></div>
        </div>`;
      el.querySelector('.sub').textContent = s.name;
      if (el.querySelector('.port')) el.querySelector('.port').textContent = s.port;
      const toggle = (key) => { if (hidden.has(key)) hidden.delete(key); else hidden.add(key); saveHidden(); renderList(); redraw(); };
      el.querySelector('.eye:not(.use):not(.idb):not(.pts)').addEventListener('click', () => toggle(s.name));
      el.querySelector('.eye.pts')?.addEventListener('click', () => toggle(s.name + '#points'));
      el.querySelector('.eye.idb')?.addEventListener('click', () =>
        publish('/pico/command', 'std_msgs/msg/String', { data: `ID ${connectorOf(s)}` }));
      el.querySelectorAll('.sw').forEach((b) => b.addEventListener('click', () => {
        s.colour = b.dataset.c;
        renderList();
        touched();
      }));
      el.querySelector('.typecol').addEventListener('click', () => {
        delete s.colour;
        renderList();
        touched();
      });
      const name = el.querySelector('.name');
      name.value = s.name;
      name.addEventListener('change', () => {
        const n = uniqueName(name.value, taken(s));
        if (!n) {
          name.value = s.name;
          return status('That name is empty, already used, or not lower case letters, digits and _.', 'bad');
        }
        if (selected === s.name) selected = n;
        moveHidden(s.name, n);
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
        inp.parentElement.querySelector('b').textContent = FMT[k](s[k]);
        const num = inp.parentElement.querySelector('input.num');
        if (num && document.activeElement !== num) num.value = inp.value;
        if (k === 'yaw_deg' || k === 'pitch_deg') {
          const old = s.name;
          rename(s);
          if (s.name !== old) { el.dataset.name = s.name; el.querySelector('.sub').textContent = s.name; name.value = s.name; }
        }
        if (k === 'yaw_deg') el.querySelectorAll('.snaps button').forEach((o) =>
          o.classList.toggle('on', Number(o.dataset.yaw) === (s.yaw_deg === -180 ? 180 : s.yaw_deg)));
        if (k === 'range_max') s.stop_distance = Math.min(s.stop_distance, r3(s.range_max - 0.01));
        touched();
      }));
      // typed degrees: kept within the slider's range, then applied as if the slider moved
      el.querySelectorAll('input.num').forEach((num) => num.addEventListener('change', () => {
        const range = el.querySelector(`input[data-k=${num.dataset.for}]`);
        const v = Number(num.value);
        if (num.value === '' || !Number.isFinite(v)) { num.value = range.value; return; }
        num.value = Math.max(Number(range.min), Math.min(Number(range.max), Math.round(v)));
        range.value = num.value;
        range.dispatchEvent(new Event('input'));
      }));
      el.querySelectorAll('.snaps button').forEach((b) => b.addEventListener('click', () => {
        const yaw = el.querySelector('input[data-k=yaw_deg]');
        yaw.value = b.dataset.yaw;
        yaw.dispatchEvent(new Event('input'));
      }));
      el.querySelector('.eye.use').addEventListener('click', () => setInUse(s, s.enabled === false));
      if (isLidar(s)) wireLidar(el, s);
      el.querySelector('select.conn')?.addEventListener('change', (e) => {
        const n = e.target.value;
        s.noBoard = !n;                 // on screen only (never written to sensors.yaml)
        if (n) s.pico = connectorPins(s.type, n);
        renderList();
        if (n) touched();
      });
      el.querySelectorAll('select[data-pin]').forEach((sel) => sel.addEventListener('change', () => {
        s.pico[sel.dataset.pin] = Number(sel.value);
        renderList();
        touched();
      }));
      el.querySelector('.defaults').addEventListener('click', () => {
        Object.assign(s, beamDefaults(s.type));
        s.stop_distance = Math.min(s.stop_distance, r3(s.range_max - 0.01));
        renderList();
        touched();
        status(`${s.name}: field of view and range back to the ${T.label}'s own. Save to keep it.`, 'warn');
      });
      el.querySelector('.remove').addEventListener('click', () => {
        sensors = sensors.filter((t) => t !== s);
        if (selected === s.name) selected = sensors[0] ? sensors[0].name : null;
        renderList();
        touched();
      });
      if (locked) el.querySelectorAll('input, select, button').forEach((c) => { c.disabled = true; });
      el.hidden = wasHidden.has(s.name);
      box.append(el);
    }
    $('s-addtype').querySelector('[value=rplidar_c1]').disabled = sensors.some(isLidar);
  }

  function freePins(n) {
    const used = new Set(sensors.flatMap((s) => Object.values(s.pico || {})));
    const out = [];
    for (const g of PICO_GPIO) if (out.length < n && !used.has(g)) out.push(g);
    return out;
  }
  $('s-add').addEventListener('click', () => {
    const type = $('s-addtype').value;
    const s = { type, x: 0, y: R2.bodyR + 0.01, z: 0.3, yaw_deg: 90, pitch_deg: 0, ...beamDefaults(type),
                stop_distance: 0, found: null, nameEdited: false };
    if (type === 'rplidar_c1') Object.assign(s, { port: '/dev/r2-lidar', x: 0.17, y: 0, z: 0.11, yaw_deg: 0 });
    else {
      const conn = freeConnector(type, sensors);
      if (conn) s.pico = connectorPins(type, conn);
      else {
        // every connector of that type is taken: free pins, wired straight to the Pico
        const pins = freePins(PINS[type].length);
        if (pins.length < PINS[type].length) return status('No free Pico pins left.', 'bad');
        s.pico = Object.fromEntries(PINS[type].map((p, i) => [p, pins[i]]));
        s.noBoard = true;
      }
    }
    s.name = defaultName(s, taken(null));
    sensors.push(s);
    selected = s.name;
    renderList();
    touched();
    if (s.noBoard) status(`All the board's ${type === 'vl53l0x' ? 'VL' : 'US'} connectors are taken: ${s.name} goes on free Pico pins (no board). Save to keep it.`, 'warn');
  });

  // ---------- in use / ignored: saved at once, only that line (never the card's unsaved changes) ----------
  async function setInUse(s, use) {
    const warn = !use && lastFrontInUse(sensors, s.name);
    let res;
    try {
      res = await (await fetch('api/sensors/enabled', { method: 'POST', body: JSON.stringify({ name: s.name, enabled: use }) })).json();
    } catch { status('Not changed: the Pi does not answer.', 'bad'); return; }
    if (res.error) { status(res.error, 'bad'); return; }
    s.enabled = use;
    // the File tab shows (and would save) the file as it is now, with this line changed
    loaded = { ...loaded, file: res.file, saved: true, yaml: res.yaml ?? loaded.yaml };
    renderList(); redraw();
    status(use ? `${s.name} is in use again.`
      : warn ? `${s.name} ignored. Nothing in use looks ahead now: navigation will not move (no data).`
        : `${s.name} ignored: navigation does not use its readings (it keeps measuring).`, warn ? 'warn' : 'ok');
  }

  // ---------- the lidar's own settings ----------
  // motor, scan mode, upside down, blind sectors (degrees of the lidar's own view) and its info line
  function lidarRows(s) {
    const modes = lidarModes(lidarInfo);
    if (s.scan_mode && !modes.includes(s.scan_mode)) modes.push(s.scan_mode);
    const opt = (v, t, cur) => `<option value="${v}"${v === cur ? ' selected' : ''}>${t}</option>`;
    const sectors = (s.blind_sectors || []).map(([a, b], i) => `<span class="sector" data-i="${i}">
        <input type="number" class="num sa" min="-180" max="180" step="1" value="${a}">° to
        <input type="number" class="num sb" min="-180" max="180" step="1" value="${b}">°
        <button class="eye srm" title="Remove this blind sector"><i class="fa-solid fa-xmark"></i></button></span>`).join('');
    return `
      <div class="row"><label><i class="fa-solid fa-fan"></i>motor</label><select class="lmotor" title="Only with an automatic mode: R2 standing still is quiet; a mode waits up to 5 s for the lidar to spin up">
        ${LIDAR_MOTOR.map(([v, t]) => opt(v, t, s.motor || 'always')).join('')}</select></div>
      <div class="row"><label><i class="fa-solid fa-wave-square"></i>scan mode</label><select class="lmode" title="The modes the lidar says it has. Changing it restarts the lidar's driver">
        ${modes.map((m) => opt(m, m, s.scan_mode || 'Standard')).join('')}</select></div>
      <div class="row"><label><i class="fa-solid fa-arrows-rotate"></i>upside down</label><label class="chk"><input type="checkbox" class="linv"${s.inverted ? ' checked' : ''}> mounted upside down</label></div>
      <div class="row"><label title="Angles of the lidar's own view to ignore (R2's leg): from, counter-clockwise, to"><i class="fa-solid fa-ban"></i>blind sectors</label>
        <span>${sectors}<button class="addsec" title="Add a blind sector"><i class="fa-solid fa-plus"></i>Add</button></span></div>
      <div class="row"><label><i class="fa-solid fa-circle-info"></i>lidar</label><span class="sub lidarinfo">${lidarInfoText(lidarInfo, scanTurns, scanPoints)}</span></div>`;
  }
  function wireLidar(el, s) {
    el.querySelector('.lmotor').addEventListener('change', (e) => { s.motor = e.target.value; touched(); });
    el.querySelector('.lmode').addEventListener('change', (e) => { s.scan_mode = e.target.value; touched(); });
    el.querySelector('.linv').addEventListener('change', (e) => { s.inverted = e.target.checked; touched(); });
    el.querySelector('.addsec').addEventListener('click', () => {
      s.blind_sectors = [...(s.blind_sectors || []), [170, -170]];
      renderList(); touched();
    });
    el.querySelectorAll('.sector').forEach((row) => {
      const i = Number(row.dataset.i);
      const set = () => {
        const a = Math.round(Number(row.querySelector('.sa').value));
        const b = Math.round(Number(row.querySelector('.sb').value));
        if (!Number.isFinite(a) || !Number.isFinite(b)) return;
        s.blind_sectors[i] = [Math.max(-180, Math.min(180, a)), Math.max(-180, Math.min(180, b))];
        touched();
      };
      row.querySelector('.sa').addEventListener('change', set);
      row.querySelector('.sb').addEventListener('change', set);
      row.querySelector('.srm').addEventListener('click', () => {
        s.blind_sectors.splice(i, 1);
        renderList(); touched();
      });
    });
  }

  // ---------- file ----------
  function toYaml() {
    let out = '# R2 sensors, saved from the web console (Setup -> Sensors). Hand edits are fine too.\n' +
              '# Metres and degrees. x forward, y left, z up from the floor under the body centre\n' +
              '# (base_link, REP 103). yaw_deg + = left, pitch_deg + = down.\n';
    for (const s of sensors) {
      out += `${s.name}:\n`;
      const keys = [...FIELDS, ...Object.keys(s).filter((k) => !FIELDS.includes(k) && !['name', 'nameEdited', 'found', 'noBoard'].includes(k))];
      for (const k of keys) {
        if (s[k] === undefined) continue;
        if (isLidar(s) && ['pitch_deg', 'stop_distance', 'pico'].includes(k)) continue;
        if (k === 'enabled' && s[k] !== false) continue;      // written only when ignored
        if (k === 'pico') out += `  pico: {${Object.entries(s.pico).map(([p, g]) => `${p}: ${g}`).join(', ')}}\n`;
        else if (k === 'colour') out += `  colour: "${s[k]}"\n`;      // quoted: # starts a YAML comment
        else out += `  ${k}: ${typeof s[k] === 'number' ? r3(s[k]) : lidarYamlValue(s[k])}\n`;
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
    status(`Saved in ${res.file}. The sensor poses follow at once.${res.lidar_restarted ? ' The lidar restarts with its new settings (a few seconds without /scan).' : ''}`, 'ok');
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
  objSel.addEventListener('change', () => { object = { ...object, none: false, ...OBJECTS[objSel.value] }; redraw(); });
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
