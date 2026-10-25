// Camera setup: which cameras R2 uses, their number, size, direction and field of view.
// Saves cameras.yaml on the Pi through the web console's /api/cameras.
const $ = (id) => document.getElementById(id);
const WS_URL = `ws://${location.hostname || 'localhost'}:9090`;
const TRACKER = '/dome_tracker';

let rows = [];           // one per camera: { use, num, name, source, id, title, modes, mode, yaw, hfov, extra, running }
let running = [];        // camera names the tracker uses right now
let fileText = '';

// ---------- rosbridge (live preview and live changes) ----------
let ws = null;
let callId = 0;
const pending = {};
const handlers = {};
function connect() {
  ws = new WebSocket(WS_URL);
  ws.onopen = () => load();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.op === 'publish' && handlers[m.topic]) handlers[m.topic](m.msg);
    if (m.op === 'service_response' && pending[m.id]) { pending[m.id](m.result ? m.values : null); delete pending[m.id]; }
  };
  ws.onclose = () => setTimeout(connect, 2000);
}
const send = (o) => ws && ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify(o));
function call(service, type, args) {
  return new Promise((resolve) => {
    const id = 'c' + (++callId);
    pending[id] = resolve;
    send({ op: 'call_service', id, service, type, args });
    setTimeout(() => { if (pending[id]) { delete pending[id]; resolve(null); } }, 3000);
  });
}
function setParam(node, name, value) {
  const v = typeof value === 'boolean' ? { type: 1, bool_value: value }
    : Number.isInteger(value) ? { type: 2, integer_value: value } : { type: 3, double_value: value };
  return call(`${node}/set_parameters`, 'rcl_interfaces/srv/SetParameters', { parameters: [{ name, value: v }] });
}

// ---------- load ----------
async function load() {
  status('loading…');
  const api = await (await fetch('api/cameras')).json();
  if (api.error) return status(api.error, 'bad');
  plugged = api.detected.map((d) => d.path).join('|');
  fileText = api.yaml;
  $('yaml').value = fileText;
  $('filename').textContent = api.file + (api.saved ? '' : ' (the package default: saving creates ~/.config/ros2d2/cameras.yaml)');
  const t = await call(`${TRACKER}/get_parameters`, 'rcl_interfaces/srv/GetParameters', { names: ['cameras'] });
  running = t && t.values[0] ? t.values[0].string_array_value || [] : [];

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
  status(api.saved ? 'Loaded the saved setup.' : 'Using the package default (auto). Save to keep your own.', api.saved ? '' : 'warn');
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
          <label><input type="checkbox" class="use"> use</label></div>
        <div class="row"><label>number</label><div class="step"><button data-a="left">◀</button><b>${r.num}</b><button data-a="right">▶</button></div></div>
        <div class="row"><label>size</label><select class="mode">${modes.map((m) => `<option>${m}</option>`).join('')}</select></div>
        <div class="row"><label>points to (− left, + right)</label><div class="step"><button data-a="yaw-">−</button><b class="yaw"></b><button data-a="yaw+">+</button></div></div>
        <div class="row"><label>field of view</label><div class="step"><button data-a="hfov-">−</button><b class="hfov"></b><button data-a="hfov+">+</button></div></div>
      </div>`;
    el.querySelector('.title').textContent = r.title + (r.name ? ` (${r.name})` : '');
    const badge = document.createElement('span');
    badge.className = 'badge ' + (r.missing ? 'offline' : 'online');
    badge.textContent = r.missing ? 'offline' : 'plugged in';
    el.querySelector('.title').after(badge);
    el.querySelector('.path').textContent = r.source;
    el.querySelector('.use').checked = r.use;
    el.querySelector('.mode').value = r.mode;
    showGeometry(r);
    const msg = el.querySelector('.msg');
    if (r.missing) {
      msg.textContent = 'Not plugged in. Plug it back in, or untick "use" and Save to remove it.';
    } else if (r.running) {
      handlers[`/cameras/${r.name}/image_raw/compressed`] = (m) => {
        el.querySelector('img').src = `data:image/jpeg;base64,${m.data}`; msg.textContent = '';
      };
      send({ op: 'subscribe', topic: `/cameras/${r.name}/image_raw/compressed`, type: 'sensor_msgs/msg/CompressedImage', throttle_rate: 200, queue_length: 1 });
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
    box.append(el);
  }
}

function showGeometry(r) {
  r.el.querySelector('.yaw').textContent = `${r.yaw > 0 ? '+' : ''}${r.yaw}°`;
  r.el.querySelector('.hfov').textContent = `${r.hfov}°`;
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

async function save(restart) {
  const fromFile = !$('file').hidden;
  const text = fromFile ? $('yaml').value : toYaml();
  const res = await (await fetch('api/cameras', { method: 'POST', body: JSON.stringify({ yaml: text }) })).json();
  if (res.error) return status(res.error, 'bad');
  needsRestart = false;
  $('yaml').value = text;
  if (!restart) return status(`Saved in ${res.file}.`, 'ok');
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

$('save').addEventListener('click', () => save(false));
$('restart').addEventListener('click', () => save(true));
$('tab-form').addEventListener('click', () => { $('form').hidden = false; $('file').hidden = true; $('tab-form').classList.add('on'); $('tab-file').classList.remove('on'); });
$('tab-file').addEventListener('click', () => {
  if (needsRestart || $('status').classList.contains('warn')) $('yaml').value = toYaml();
  $('form').hidden = true; $('file').hidden = false; $('tab-file').classList.add('on'); $('tab-form').classList.remove('on');
});
$('yaml').addEventListener('input', () => dirty(true));

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

connect();
