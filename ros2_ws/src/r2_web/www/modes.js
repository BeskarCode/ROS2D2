// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup -> Modes: which controller combination starts each mode, and the colour the follow mode
// follows, picked by clicking on the camera picture. Saves modes.yaml through /api/modes; the web
// server then publishes /r2/modes/reload and the Mega bridge sends the new combos to the Mega.
//
// While this tab is on screen the page publishes /marker/preview true (color_marker then sends
// /marker/mask/compressed: the picture with the matches painted magenta). A click publishes
// /marker/pick and the answer comes back on /marker/pick_result.
import { publish, subscribe } from './rosbridge.js';
import { showStream, stopStream } from './mjpeg.js';
import { COMBOS, MODES, MODE_LABELS, comboChoices, hsvToRgb, losesAction, pickToColor, toYaml } from './modesform.js';

const $ = (id) => document.getElementById(id);
const ICONS = { goto: 'fa-location-crosshairs', forward: 'fa-arrow-up', patrol: 'fa-route', follow: 'fa-shirt' };
const FOLLOW_SLIDERS = [
  // key, label, icon, min, max, step, how it reads
  ['hue_tol', 'hue margin', 'fa-palette', 2, 40, 1, (v) => `±${v}`],
  ['light_tol', 'light margin', 'fa-sun', 10, 120, 1, (v) => `±${v}`],
  ['distance', 'distance', 'fa-ruler-horizontal', 0.8, 4, 0.1, (v) => `${v.toFixed(1)} m`],
  ['max_speed', 'max speed', 'fa-gauge-high', 0.05, 0.4, 0.05, (v) => `${v.toFixed(2)} m/s`],
  ['search_s', 'search time', 'fa-magnifying-glass', 0, 20, 1, (v) => `${v} s`],
];
const MASK_STALE_MS = 2500;     // no painted picture for this long: show the plain camera instead

export function createModesTab({ status }) {
  let loaded = { file: '', saved: false, yaml: '', modes: {}, error: null, combos: COMBOS };
  let cfg = null;
  let changed = false;
  let locked = false;           // modes.yaml is broken: fix it in the File tab first
  let visible = false;
  let cameras = [];             // camera names in cameras.yaml
  let active = '';              // /r2/mode
  let lastPick = null;          // {x, y} of the last click, to pick again when a margin moves
  let pickTimer = null;
  let maskAt = 0;
  let ticker = null;
  let errorCb = () => {};
  let subscribed = false;

  // ---------- load ----------
  async function load() {
    let api;
    try { api = await (await fetch('api/modes', { cache: 'no-store' })).json(); } catch { return; }
    loaded = api;
    locked = !!api.error;
    cfg = locked ? null : api.modes;
    changed = false;
    lastPick = null;
    try { cameras = Object.keys((await (await fetch('api/cameras', { cache: 'no-store' })).json()).cameras || {}); } catch { cameras = []; }
    $('m-locked').hidden = !locked;
    if (visible) $('save').disabled = locked;
    render();
    if (locked) errorCb();
    else if (visible) status(api.saved ? 'Loaded the saved modes.' : 'Using the package default. Save to keep your own.', api.saved ? '' : 'warn');
  }

  // ---------- render ----------
  function render() {
    renderList();
    renderFollow();
  }

  function renderList() {
    const box = $('mlist');
    box.textContent = '';
    for (const m of MODES) {
      const row = document.createElement('div');
      row.className = 'mrow' + (active === m ? ' active' : '');
      row.innerHTML = `<div class="mname"><i class="fa-solid ${ICONS[m]}"></i><b></b><code></code>
          <span class="badge ok mon" ${active === m ? '' : 'hidden'}><i class="fa-solid fa-circle-play"></i>on now</span></div>
        <select aria-label="controller combination"></select>
        <div class="mwarn" hidden><i class="fa-solid fa-triangle-exclamation"></i>This combo will no longer play its MarcDuino action</div>`;
      row.querySelector('b').textContent = MODE_LABELS[m];
      row.querySelector('code').textContent = m;
      const sel = row.querySelector('select');
      const combo = cfg ? cfg[m].combo : null;
      sel.add(new Option('— no combo —', ''));
      for (const c of comboChoices(cfg || {}, m, loaded.combos || COMBOS)) {
        const o = new Option(c.taken_by ? `${c.label}  (${MODE_LABELS[c.taken_by]})` : c.label, c.name);
        o.disabled = !!c.taken_by;
        o.dataset.takenBy = c.taken_by || '';
        sel.add(o);
      }
      sel.value = combo || '';
      sel.disabled = locked;
      row.querySelector('.mwarn').hidden = !losesAction(combo);
      sel.addEventListener('change', () => {
        cfg[m].combo = sel.value || null;
        touched();
        renderList();
      });
      box.append(row);
    }
  }

  function renderFollow() {
    const f = cfg ? cfg.follow : null;
    const camSel = $('m-camera');
    camSel.textContent = '';
    const names = [...new Set([...(f ? [f.camera] : []), ...cameras])];
    for (const n of names) camSel.add(new Option(n, n));
    if (f) camSel.value = f.camera;
    camSel.disabled = locked;
    $('m-camname').textContent = f ? f.camera : '';
    const box = $('m-sliders');
    box.textContent = '';
    for (const [key, label, icon, min, max, step, fmt] of FOLLOW_SLIDERS) {
      if (key === 'distance') {
        const h = document.createElement('h4');
        h.innerHTML = '<i class="fa-solid fa-person-walking"></i>Following';
        box.append(h);
      }
      const row = document.createElement('div');
      row.className = 'row';
      row.innerHTML = `<label><i class="fa-solid ${icon}"></i>${label}</label>
        <div class="slider"><input type="range" min="${min}" max="${max}" step="${step}" data-k="${key}"><b></b></div>`;
      const input = row.querySelector('input');
      const out = row.querySelector('b');
      const v = f ? f[key] : min;
      input.value = v;
      input.disabled = locked;
      out.textContent = fmt(Number(v));
      input.addEventListener('input', () => {
        const n = Number(input.value);
        cfg.follow[key] = n;
        out.textContent = fmt(n);
        touched();
        if (key === 'hue_tol' || key === 'light_tol') pickAgain();
      });
      box.append(row);
    }
    showColor(null);
  }

  // The colour panel: from a fresh pick (result) or the saved colour
  function showColor(result) {
    const f = cfg ? cfg.follow : null;
    const sw = $('m-swatch');
    const match = $('m-match');
    const warn = $('m-warning');
    if (result) {
      const [r, g, b] = result.rgb;
      sw.style.background = `rgb(${r}, ${g}, ${b})`;
      sw.classList.remove('empty');
      $('m-rgb').textContent = `RGB ${r}, ${g}, ${b} · HSV ${result.h}, ${result.s}, ${result.v}`;
      const pct = Math.round(result.match * 100);
      match.hidden = false;
      match.className = 'mmatch ' + (result.match > 0 ? 'ok' : 'bad');
      match.innerHTML = result.match > 0
        ? `<i class="fa-solid fa-eye"></i>I can see it: ${pct} % of the picture`
        : '<i class="fa-solid fa-eye-slash"></i>I cannot see it in the picture';
      warn.hidden = !result.warning;
      warn.innerHTML = result.warning ? '<i class="fa-solid fa-triangle-exclamation"></i>' : '';
      warn.append(result.warning || '');
      return;
    }
    match.hidden = true;
    warn.hidden = true;
    if (f && f.color) {
      const [r, g, b] = hsvToRgb(f.color);
      sw.style.background = `rgb(${r}, ${g}, ${b})`;
      sw.classList.remove('empty');
      $('m-rgb').textContent = `Saved colour · HSV ${f.color.h}, ${f.color.s}, ${f.color.v}`;
    } else {
      sw.style.background = '';
      sw.classList.add('empty');
      $('m-rgb').textContent = 'No colour yet: click on it in the picture.';
    }
  }

  // ---------- the camera picture and the pick ----------
  function onMask(msg) {
    if (!visible) return;
    const img = $('m-pic');
    if (img.dataset.stream) stopStream(img);
    maskAt = Date.now();
    img.src = `data:image/jpeg;base64,${msg.data}`;
    $('m-picmsg').textContent = '';
    $('m-picnote').textContent = 'What the follow mode sees: the matches of the saved colour are painted magenta.';
  }

  // No painted picture (no colour saved yet, or the colour finder is not running): the plain camera
  function tick() {
    if (!visible) return;
    publish('/marker/preview', 'std_msgs/msg/Bool', { data: true });   // again, in case a node restarted
    const img = $('m-pic');
    const cam = cfg ? cfg.follow.camera : null;
    if (!cam || Date.now() - maskAt < MASK_STALE_MS || img.dataset.stream) return;
    showStream(img, `http://${location.hostname}:8081/stream?topic=/cameras/${cam}/image_raw&qos_profile=sensor_data`);
    if (!img.naturalWidth) $('m-picmsg').textContent = 'waiting for the picture…';
    $('m-picnote').textContent = cfg.follow.color
      ? 'The plain camera picture (the colour finder is not answering).'
      : 'The plain camera picture: once a colour is saved, its matches are painted magenta here.';
  }

  function onClick(e) {
    if (locked || !cfg) return;
    const r = e.currentTarget.getBoundingClientRect();
    lastPick = { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height };
    const cross = $('m-cross');
    cross.hidden = false;
    cross.style.left = `${lastPick.x * 100}%`;
    cross.style.top = `${lastPick.y * 100}%`;
    sendPick();
  }

  function sendPick() {
    if (!lastPick) return;
    publish('/marker/pick', 'std_msgs/msg/String', { data: JSON.stringify({
      x: lastPick.x, y: lastPick.y, hue_tol: cfg.follow.hue_tol, light_tol: cfg.follow.light_tol }) });
  }

  // A margin moved: pick the same spot again (at most ~4 times a second)
  function pickAgain() {
    clearTimeout(pickTimer);
    pickTimer = setTimeout(sendPick, 250);
  }

  function onPickResult(msg) {
    if (!visible || !cfg || locked) return;
    let r;
    try { r = JSON.parse(msg.data); } catch { return; }
    cfg = pickToColor(r, cfg);
    showColor(r);
    touched();
  }

  function onMode(msg) {
    active = msg.data || '';
    document.querySelectorAll('#mlist .mrow').forEach((row, i) => {
      row.classList.toggle('active', MODES[i] === active);
      row.querySelector('.mon').hidden = MODES[i] !== active;
    });
  }

  function touched() {
    changed = true;
    status('Changed: Save to keep it (the Mega gets the new combos at once).', 'warn');
  }

  // ---------- save ----------
  async function save(text) {
    const body = text ?? (cfg ? toYaml(cfg) : null);
    if (body === null) { status('modes.yaml has a mistake: fix it in the File tab.', 'bad'); return false; }
    let res;
    try {
      res = await (await fetch('api/modes', { method: 'POST', body: JSON.stringify({ yaml: body }) })).json();
    } catch (e) { status(`not saved: ${e}`, 'bad'); return false; }
    if (res.error) { status(res.error, 'bad'); return false; }
    loaded = { ...loaded, yaml: body, file: res.file, saved: true, error: null };
    changed = false;
    maskAt = 0;          // the colour finder re-reads the file: its painted picture follows
    status(`Saved in ${res.file}. The Mega has the new combos.`, 'ok');
    return true;
  }

  function show() {
    visible = true;
    $('save').disabled = locked;
    if (!subscribed) {
      subscribed = true;
      subscribe('/marker/mask/compressed', 'sensor_msgs/msg/CompressedImage', onMask, 200);
      subscribe('/marker/pick_result', 'std_msgs/msg/String', onPickResult);
      subscribe('/r2/mode', 'std_msgs/msg/String', onMode);
    }
    clearInterval(ticker);
    ticker = setInterval(tick, 1000);
    tick();
  }

  function hide() {
    if (!visible) return;
    visible = false;
    $('save').disabled = false;
    clearInterval(ticker);
    publish('/marker/preview', 'std_msgs/msg/Bool', { data: false });
    stopStream($('m-pic'));
    $('m-pic').removeAttribute('src');
    maskAt = 0;
  }

  $('m-pic').addEventListener('click', onClick);
  $('m-pic').addEventListener('load', () => { $('m-picmsg').textContent = ''; });
  $('m-camera').addEventListener('change', (e) => {
    cfg.follow.camera = e.target.value;
    $('m-camname').textContent = e.target.value;
    lastPick = null;
    $('m-cross').hidden = true;
    stopStream($('m-pic'));
    touched();
    status('Changed the camera: Save first, then click on the colour in its picture.', 'warn');
  });
  // Leaving the page with the tab open: the camera need not keep sending for the preview
  window.addEventListener('pagehide', () => { if (visible) publish('/marker/preview', 'std_msgs/msg/Bool', { data: false }); });

  return {
    load,
    save,
    show,
    hide,
    fileText: () => (changed && cfg ? toYaml(cfg) : loaded.yaml),
    fileName: () => loaded.file + (loaded.saved ? '' : ' (the package default: saving creates ~/.config/ros2d2/modes.yaml)'),
    onError(cb) { errorCb = cb; },
  };
}
