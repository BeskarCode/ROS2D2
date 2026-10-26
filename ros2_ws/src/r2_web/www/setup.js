// Camera setup: which cameras R2 uses, their number, size, direction and field of view.
// Saves cameras.yaml on the Pi through the web console's /api/cameras.
import { call, connect, setParam } from './rosbridge.js';
import { createSensorsTab } from './sensors.js';

const $ = (id) => document.getElementById(id);
const TRACKER = '/dome_tracker';

let rows = [];           // one per camera: { use, num, name, source, id, title, modes, mode, yaw, hfov, extra, running }
let running = [];        // camera names the tracker uses right now
let fileText = '';
let cameraFile = '';

// ---------- load ----------
// The camera list loads again on every rosbridge reconnect: it only speaks (status line,
// File text) while the cameras are the section on screen
const camStatus = (text, cls) => { if (section === 'cameras') status(text, cls); };
async function load() {
  if (section === 'cameras') $('status').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> loading…';
  const api = await (await fetch('api/cameras')).json();
  if (api.error) return camStatus(api.error, 'bad');
  plugged = api.detected.map((d) => d.path).join('|');
  fileText = api.yaml;
  if (section === 'cameras') $('yaml').value = fileText;
  cameraFile = api.file + (api.saved ? '' : ' (the package default: saving creates ~/.config/ros2d2/cameras.yaml)');
  if (section === 'cameras') $('filename').textContent = cameraFile;
  const t = await call(`${TRACKER}/get_parameters`, 'rcl_interfaces/srv/GetParameters', { names: ['cameras'] });
  running = t && t.values[0] ? t.values[0].string_array_value || [] : [];
  // Pixelate as chosen on the console (remembered in this browser), also after a restart
  let pix = null;
  try { pix = localStorage.getItem('r2web.pixelate'); } catch { /* private window */ }
  if (pix !== null) for (const n of running) setParam(`/cameras/${n}/face_detector`, 'pixelate', pix === 'true');

  const configured = Object.entries(api.cameras);       // [name, params] in file order
  const used = new Set();
  rows = [];
  // Cameras plugged in: matched to the configured ones by their path
  for (const d of api.detected) {
    const match = configured.find(([, p]) => [d.path, d.id, d.device].includes(String(p.source)));
    if (match) used.add(match[0]);
    rows.push(makeRow(match, configured.indexOf(match), { source: d.id || d.path, id: d.id, title: d.name, modes: d.modes }));
  }
  // Configured but not found (unplugged, or a network camera like an ESP32)
  for (const entry of configured) {
    if (used.has(entry[0])) continue;
    const src = String(entry[1].source ?? '');
    const net = src.includes('://');
    rows.push(makeRow(entry, configured.indexOf(entry), { source: src, title: net ? 'Network camera' : 'Unplugged camera', modes: [], missing: !net }));
  }
  // Numbers: configured ones keep their order, new ones go after
  rows.forEach((r, i) => { r.num = r.num ?? 100 + i; });
  renumber();
  render();
  camStatus(api.saved ? 'Loaded the saved setup.' : 'Using the package default (auto). Save to keep your own.', api.saved ? '' : 'warn');
}

function makeRow(entry, order, found) {
  const [name, p] = entry || [null, {}];
  const w = p.width ?? 640, h = p.height ?? 480, fps = p.fps ?? 30;
  const extra = { ...p };
  for (const k of ['source', 'yaw_deg', 'hfov_deg', 'width', 'height', 'fps']) delete extra[k];
  return {
    use: !!entry, name, num: entry ? order : null,
    source: entry ? String(p.source) : found.source, id: found.id,
    title: found.title, modes: found.modes, mode: `${w}x${h}@${fps}`,
    yaw: Number(p.yaw_deg ?? 0), hfov: Number(p.hfov_deg ?? 60), extra, running: running.includes(name),
    missing: !!found.missing,
  };
}

function renumber() {
  // Used cameras first (by their number), then the others; numbers 1..n
  rows.sort((a, b) => (b.use - a.use) || (a.num - b.num));
  rows.forEach((r, i) => { r.num = i + 1; });
}

// ---------- render ----------
function render() {
  const box = $('cams');
  box.querySelectorAll('img').forEach((i) => { i.src = ''; });   // close the old MJPEG connections
  box.textContent = '';
  for (const r of rows) {
    const el = document.createElement('div');
    el.className = 'cam' + (r.use ? '' : ' off');
    r.el = el;
    const modes = [...new Set([r.mode, ...r.modes])];
    el.innerHTML = `
      <div class="pic"><img alt=""><div class="msg"></div><div class="num">${r.num}</div></div>
      <div class="body">
        <div class="row"><span><span class="title"></span><div class="path"></div></span>
          <label><input type="checkbox" class="use"> <i class="fa-solid fa-power-off"></i>use</label></div>
        <div class="row"><label><i class="fa-solid fa-hashtag"></i>number</label><div class="step"><button data-a="left"><i class="fa-solid fa-chevron-left"></i></button><b>${r.num}</b><button data-a="right"><i class="fa-solid fa-chevron-right"></i></button></div></div>
        <div class="row"><label><i class="fa-solid fa-expand"></i>size</label><select class="mode">${modes.map((m) => `<option>${m}</option>`).join('')}</select></div>
        <div class="row"><label><i class="fa-solid fa-compass"></i>points to</label><div class="slider"><input type="range" class="yawr" min="-180" max="180" step="1"><b class="yaw"></b></div></div>
        <div class="row"><label><i class="fa-solid fa-eye"></i>field of view</label><div class="slider"><input type="range" class="hfovr" min="20" max="170" step="1"><b class="hfov"></b></div></div>
      </div>`;
    el.querySelector('.title').textContent = r.title + (r.name ? ` (${r.name})` : '');
    const badge = document.createElement('span');
    badge.className = 'badge ' + (r.missing ? 'offline' : 'online');
    badge.innerHTML = r.missing ? '<i class="fa-solid fa-plug-circle-xmark"></i> offline' : '<i class="fa-solid fa-plug-circle-check"></i> plugged in';
    el.querySelector('.title').after(badge);
    el.querySelector('.path').textContent = r.source;
    el.querySelector('.use').checked = r.use;
    el.querySelector('.mode').value = r.mode;
    showGeometry(r);
    const msg = el.querySelector('.msg');
    if (r.missing) {
      msg.textContent = 'Not plugged in. Plug it back in, or untick "use" and Save to remove it.';
    } else if (r.running) {
      // The face detector's picture (pixelated when that is on), as MJPEG from web_video_server
      const img = el.querySelector('img');
      img.onload = () => { msg.textContent = ''; };
      img.src = `http://${location.hostname}:8081/stream?topic=/cameras/${r.name}/faces/image` +
                '&type=ros_compressed&qos_profile=sensor_data';
      msg.textContent = 'waiting for the picture…';
    } else {
      msg.textContent = r.use ? 'Not running yet: Save and restart to start it.' : 'Not used.';
    }
    el.querySelector('.use').addEventListener('change', (e) => { r.use = e.target.checked; renumber(); render(); dirty(true); });
    el.querySelector('.mode').addEventListener('change', (e) => {
      r.mode = e.target.value; dirty();
      if (r.running) {
        const [w, h, fps] = r.mode.split(/[x@]/).map(Number);
        const node = `/cameras/${r.name}/camera`;
        setParam(node, 'width', w).then(() => setParam(node, 'height', h)).then(() => setParam(node, 'fps', Math.round(fps)));
      }
    });
    el.querySelectorAll('button[data-a]').forEach((b) => b.addEventListener('click', () => act(r, b.dataset.a)));
    el.querySelector('.yawr').value = r.yaw;
    el.querySelector('.hfovr').value = r.hfov;
    el.querySelector('.yawr').addEventListener('input', (e) => slide(r, 'yaw', Number(e.target.value)));
    el.querySelector('.hfovr').addEventListener('input', (e) => slide(r, 'hfov', Number(e.target.value)));
    box.append(el);
  }
}

function showGeometry(r) {
  r.el.querySelector('.yaw').textContent = `${r.yaw > 0 ? '+' : ''}${r.yaw}°`;
  r.el.querySelector('.hfov').textContent = `${r.hfov}°`;
  drawMap();
}

// Slider moved: show it, and tell the tracker straight away (at most ~10 times a second)
const sendTimers = {};
function slide(r, what, value) {
  r[what] = value;
  showGeometry(r);
  dirty();
  if (!r.running) return;
  const key = r.name + what;
  clearTimeout(sendTimers[key]);
  sendTimers[key] = setTimeout(() => setParam(TRACKER, `${r.name}.${what === 'yaw' ? 'yaw_deg' : 'hfov_deg'}`, r[what] + 0.0), 100);
}

// Top-down map: the dome, its front, and one fan per camera in use
const COLOURS = ['#3b82f6', '#f0b429', '#3fb950', '#f85149', '#a371f7', '#39c5cf'];
function drawMap() {
  const svg = $('map');
  if (!svg) return;
  const used = rows.filter((r) => r.use);
  const R = 95;
  // degrees from the front (+ = right) -> point on the map (front = up)
  const at = (deg, rad) => [Math.sin(deg * Math.PI / 180) * rad, -Math.cos(deg * Math.PI / 180) * rad];
  let out = `<circle r="${R}" fill="none" stroke="#2a313c" stroke-dasharray="3 4"/>`;
  used.forEach((r, i) => {
    const c = COLOURS[i % COLOURS.length];
    const h = Math.min(r.hfov, 359.9);
    const [x1, y1] = at(r.yaw - h / 2, R), [x2, y2] = at(r.yaw + h / 2, R), [tx, ty] = at(r.yaw, R * 0.62);
    out += `<path d="M0 0 L${x1} ${y1} A${R} ${R} 0 ${h > 180 ? 1 : 0} 1 ${x2} ${y2} Z" fill="${c}" fill-opacity=".22" stroke="${c}" stroke-width="1.5"/>`;
    out += `<circle cx="${tx}" cy="${ty}" r="11" fill="#0d1117" stroke="${c}" stroke-width="2"/>` +
           `<text x="${tx}" y="${ty + 4.5}" text-anchor="middle" font-size="13" font-weight="700" fill="${c}">${i + 1}</text>`;
  });
  out += `<circle r="26" fill="#161b22" stroke="#8b949e" stroke-width="2"/>` +
         `<path d="M0 -40 L-7 -27 L7 -27 Z" fill="#e6edf3"/>` +
         `<text y="5" text-anchor="middle" font-size="10" fill="#8b949e">dome</text>`;
  svg.innerHTML = out;
  // Total view without counting overlaps twice (1 degree steps)
  let seen = 0;
  for (let d = -180; d < 180; d++) if (used.some((r) => Math.abs(((d - r.yaw + 540) % 360) - 180) <= r.hfov / 2)) seen++;
  $('cover').textContent = used.length ? `Together they see ${seen}° of 360°.` : 'No camera in use.';
}

function act(r, a) {
  if (a === 'left' || a === 'right') {
    const i = rows.indexOf(r), j = a === 'left' ? i - 1 : i + 1;
    if (j < 0 || j >= rows.length || !rows[j].use || !r.use) return;
    [rows[i].num, rows[j].num] = [rows[j].num, rows[i].num];
    renumber(); render(); dirty(true);
    return;
  }
  if (a === 'yaw-') r.yaw -= 5; if (a === 'yaw+') r.yaw += 5;
  if (a === 'hfov-') r.hfov = Math.max(10, r.hfov - 1); if (a === 'hfov+') r.hfov = Math.min(170, r.hfov + 1);
  showGeometry(r);
  dirty();
  // Live: the tracker uses the new direction straight away
  if (r.running) {
    if (a.startsWith('yaw')) setParam(TRACKER, `${r.name}.yaw_deg`, r.yaw + 0.0);
    else setParam(TRACKER, `${r.name}.hfov_deg`, r.hfov + 0.0);
  }
}

$('identify').addEventListener('click', () => {
  rows.forEach((r) => r.el.classList.add('identify'));
  setTimeout(() => rows.forEach((r) => r.el.classList.remove('identify')), 3000);
});

// ---------- save ----------
let needsRestart = false;
function dirty(restart = false) {
  needsRestart = needsRestart || restart;
  status(needsRestart ? 'Changed: Save and restart to apply.' : 'Changed (already applied live): Save to keep it.', 'warn');
}

function toYaml() {
  const used = rows.filter((r) => r.use);
  let out = '# R2 cameras, saved from the web console camera setup. Hand edits are fine too:\n' +
            '# the setup page reads this same file. Numbers go left to right.\n';
  used.forEach((r, i) => {
    const [w, h, fps] = r.mode.split(/[x@]/).map(Number);
    out += `cam${i + 1}:\n  source: ${r.source}\n  yaw_deg: ${r.yaw}\n  hfov_deg: ${r.hfov}\n` +
           `  width: ${w}\n  height: ${h}\n  fps: ${Math.round(fps)}\n`;
    for (const [k, v] of Object.entries(r.extra || {})) out += `  ${k}: ${v}\n`;
    if (!('fourcc' in (r.extra || {})) && !r.source.includes('://')) out += '  fourcc: MJPG\n';
  });
  if (!used.length) out += 'auto:\n';
  return out;
}

// Which settings the File tab and the Save buttons work on
let section = 'cameras';
const sensorsTab = createSensorsTab({ status });

async function save(restart) {
  const fromFile = !$('file').hidden;
  if (section === 'sensors') {
    const text = fromFile ? $('yaml').value : null;
    if (!(await sensorsTab.save(text))) return;
    if (fromFile) sensorsTab.load();
  } else {
    const text = fromFile ? $('yaml').value : toYaml();
    const res = await (await fetch('api/cameras', { method: 'POST', body: JSON.stringify({ yaml: text }) })).json();
    if (res.error) return status(res.error, 'bad');
    needsRestart = false;
    $('yaml').value = text;
    if (!restart) return status(`Saved in ${res.file}.`, 'ok');
  }
  if (!restart) return;
  busy(true);
  status('Saved. Restarting ROS2D2… the page reloads when it is back.', 'warn');
  await fetch('api/restart', { method: 'POST' });
  waitForRestart();
}

function waitForRestart() {
  let gone = false;
  const t = setInterval(async () => {
    try {
      const r = await fetch('api/cameras', { cache: 'no-store' });
      if (r.ok && gone) { clearInterval(t); setTimeout(() => location.reload(), 4000); }
    } catch { gone = true; }
  }, 1000);
}

// Tabs: Cameras, Sensors, and File (the text of whichever of the two was open last)
function showTab(name) {
  if (name !== 'file') section = name;
  $('form').hidden = name !== 'cameras';
  $('sensors').hidden = name !== 'sensors';
  $('file').hidden = name !== 'file';
  $('tab-form').classList.toggle('on', name === 'cameras');
  $('tab-sensors').classList.toggle('on', name === 'sensors');
  $('tab-file').classList.toggle('on', name === 'file');
  $('identify').hidden = name !== 'cameras';
  if (name === 'sensors') sensorsTab.show(); else sensorsTab.hide();
  if (name !== 'file') return;
  if (section === 'sensors') {
    $('yaml').value = sensorsTab.fileText();
    $('filename').textContent = sensorsTab.fileName();
  } else {
    $('yaml').value = needsRestart || $('status').classList.contains('warn') ? toYaml() : fileText;
    $('filename').textContent = cameraFile;
  }
}

$('save').addEventListener('click', () => save(false));
$('restart').addEventListener('click', () => save(true));
$('tab-form').addEventListener('click', () => showTab('cameras'));
$('tab-sensors').addEventListener('click', () => showTab('sensors'));
$('tab-file').addEventListener('click', () => showTab('file'));
$('yaml').addEventListener('input', () => dirty(section === 'cameras'));
sensorsTab.onError(() => { section = 'sensors'; showTab('file'); });

// While ROS2D2 restarts: spinning icon on the button, nothing else to press
function busy(on) {
  $('restart').disabled = on;
  $('save').disabled = on;
  $('restart').innerHTML = on ? '<i class="fa-solid fa-spinner fa-spin"></i>Restarting…'
                              : '<i class="fa-solid fa-power-off"></i>Save and restart';
}

function status(text, cls = '') { $('status').textContent = text; $('status').className = 'status ' + cls; }

// Cameras plugged in or out while the page is open: reload the list (unless there are
// unsaved changes, which a reload would throw away)
let plugged = '';
setInterval(async () => {
  try {
    const api = await (await fetch('api/cameras', { cache: 'no-store' })).json();
    const now = api.detected.map((d) => d.path).join('|');
    if (now === plugged) return;
    if ($('status').classList.contains('warn') && $('status').textContent.startsWith('Changed')) {
      status('A camera was plugged in or out. Save (or reload the page) to see it.', 'warn');
      plugged = now;
      return;
    }
    load();
  } catch { /* restarting */ }
}, 3000);

connect(load);
sensorsTab.load();   // from the web server: works without rosbridge
