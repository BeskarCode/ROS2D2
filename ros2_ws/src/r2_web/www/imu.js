// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Setup → IMU: the BNO085 node's status (/imu/status, always while the tab is open), what it measures
// (/imu/data, only with Telemetry on: the same switch as System), its settings (parameters of /imu,
// checked and saved by the node) and its three buttons (std_srvs/Trigger services).
import { call, setParam, subscribe, unsubscribe } from './rosbridge.js';
import { confirmDialog } from './dialog.js';
import { toast } from './savekey.js';
import { createImuSphere } from './imusphere.js';
import { BUMP_ALARM, bar, boxMismatch, createChecks, euler, linearAccel, statusPills, tiltClass, tiltOf } from './imulogic.js';

const $ = (id) => document.getElementById(id);
const DEG = 180 / Math.PI;
const RATE_S = 10;          // the turn-rate graph's last seconds
const RATE_FULL = 90;       // °/s at the top and bottom of the graph
const signed = (v, d = 1) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(d)}`;

export function createImuTab() {
  let visible = false, telemetry = false;
  let st = null, stAt = 0, dataAt = 0, sphere = null, timer = null;
  const checks = createChecks();
  const rates = [];          // [t s, °/s]

  // ---- status: the pills, the settings as the node has them, what can be pressed ----
  const noNode = () => !st || Date.now() - stAt > 3000;
  function showStatus() {
    const box = $('imu-pills');
    box.replaceChildren(...statusPills(st, Date.now() - stAt).map(({ text, cls }) => {
      const s = document.createElement('span');
      s.className = `pill ${cls}`;
      s.textContent = text;
      return s;
    }));
    const gone = noNode(), off = gone || !st.connected;
    for (const id of ['imu-inuse', 'imu-port', 'imu-front', 'imu-leftup']) $(id).disabled = gone;
    document.querySelectorAll('input[name="imu-box"]').forEach((r) => { r.disabled = gone; });
    $('imu-level').disabled = $('imu-heading').disabled = off;
    $('imu-forget').disabled = gone || !st.levelled;
    const mis = gone ? '' : boxMismatch(st);
    $('imu-mismatch').hidden = !mis;
    $('imu-mismatch').textContent = mis;
    $('imu-live').classList.toggle('stale', !telemetry || Date.now() - dataAt > 1000);
    if (gone) return;
    const bump = $('imu-bumprow');
    $('imu-bump').textContent = st.bump.toFixed(1);
    bump.classList.toggle('alarm', st.bump > BUMP_ALARM);
    // the controls follow the node, but not while one is being changed
    const keep = document.activeElement;
    if (keep !== $('imu-inuse')) $('imu-inuse').checked = st.in_use;
    if (keep !== $('imu-port')) $('imu-port').value = st.port === 'simulated' ? $('imu-port').value : st.port;
    if (keep !== $('imu-front')) $('imu-front').value = st.front;
    if (keep !== $('imu-leftup')) $('imu-leftup').checked = !st.invert_yaw;
    document.querySelectorAll('input[name="imu-box"]').forEach((r) => { if (keep !== r) r.checked = r.value === st.box; });
  }
  const onStatus = (m) => {
    try { st = JSON.parse(m.data); stAt = Date.now(); } catch { return; }
    showStatus();
  };

  // ---- live: sphere, dials, tilt, acceleration, turn rate, check steps ----
  function showChecks() {
    for (const { n, state } of checks.steps()) {
      const li = document.querySelector(`#imu-checks li[data-n="${n}"]`);
      li.className = state;
      li.firstElementChild.className = state === 'done' ? 'fa-solid fa-circle-check'
        : state === 'inverted' ? 'fa-solid fa-triangle-exclamation' : 'fa-regular fa-circle';
    }
    $('imu-invert').hidden = checks.steps()[2].state !== 'inverted';
  }
  const onData = (m) => {
    if (!visible || !telemetry) return;
    dataAt = Date.now();
    const { roll, pitch, yaw } = euler(m.orientation);
    const a = m.linear_acceleration;
    const lin = linearAccel(roll, pitch, [a.x, a.y, a.z]);
    const rate = m.angular_velocity.z * DEG;
    if (sphere) sphere.set(roll, pitch, yaw, lin);
    $('imu-sp').setAttribute('transform', `translate(0,20) rotate(${pitch.toFixed(1)})`);
    $('imu-sr').setAttribute('transform', `translate(0,20) rotate(${roll.toFixed(1)})`);
    $('imu-sy').setAttribute('transform', `rotate(${(-yaw).toFixed(1)})`);      // left turn = anticlockwise from above
    $('imu-pitch').textContent = `${signed(pitch)}°`;
    $('imu-roll').textContent = `${signed(roll)}°`;
    $('imu-yaw').textContent = `${yaw.toFixed(0)}°`;
    $('imu-turn').textContent = `turning ${signed(rate, 0)} °/s`;
    const tilt = tiltOf(roll, pitch);
    $('imu-tilt').textContent = `${tilt.toFixed(1)}°`;
    $('imu-tilt').className = tiltClass(tilt);
    ['ax', 'ay', 'az'].forEach((id, i) => {
      const b = bar(lin[i]);
      $(`imu-${id}`).style.left = `${b.left}%`;
      $(`imu-${id}`).style.width = `${b.width}%`;
      $(`imu-${id}v`).textContent = signed(lin[i], 2);
    });
    const t = dataAt / 1000;
    rates.push([t, rate]);
    while (rates.length && rates[0][0] < t - RATE_S) rates.shift();
    $('imu-rateline').setAttribute('points', rates.map(([s, r]) =>
      `${(((s - (t - RATE_S)) / RATE_S) * 300).toFixed(1)},${(25 - Math.max(-1, Math.min(1, r / RATE_FULL)) * 24).toFixed(1)}`).join(' '));
    checks.feed({ t, fps: st ? st.fps : 0, pitch, yaw });
    showChecks();
    $('imu-live').classList.remove('stale');
  };

  // ---- reading only while needed ----
  function listen() {
    unsubscribe('/imu/data', onData);
    if (visible && telemetry) subscribe('/imu/data', 'sensor_msgs/msg/Imu', onData, 50);
    showStatus();
  }
  function setTelemetry(on) {
    telemetry = on;
    $('imu-telemetry').checked = on;
    try { localStorage.setItem('r2web.telemetry', on ? '1' : '0'); } catch { /* private window */ }
    listen();
  }
  $('imu-telemetry').addEventListener('change', (e) => setTelemetry(e.target.checked));

  // ---- settings: the node checks and saves them; what it says goes in the toast ----
  async function setp(name, value) {
    const r = await setParam('/imu', name, value);
    const res = r && r.results && r.results[0];
    if (res && res.successful) toast('Saved');
    else toast(res ? (res.reason || 'Not accepted') : 'No answer from the IMU node', 'bad');
    showStatus();        // put the control back as the node has it
  }
  $('imu-inuse').addEventListener('change', (e) => setp('in_use', e.target.checked));
  $('imu-port').addEventListener('change', (e) => setp('port', e.target.value.trim()));
  $('imu-port').addEventListener('keydown', (e) => { if (e.key === 'Enter') e.target.blur(); });
  document.querySelectorAll('input[name="imu-box"]').forEach((r) => r.addEventListener('change', () => setp('box', r.value)));
  $('imu-front').addEventListener('change', (e) => setp('front', e.target.value));
  $('imu-leftup').addEventListener('change', (e) => setp('invert_yaw', !e.target.checked));
  $('imu-invert').addEventListener('click', async () => {
    await setp('invert_yaw', !(st && st.invert_yaw));
    checks.reset(); showChecks();
  });

  async function trigger(service) {
    const r = await call(service, 'std_srvs/srv/Trigger', {});
    if (r) toast(r.message, r.success ? 'ok' : 'bad', 5000);
    else toast('No answer from the IMU node', 'bad');
  }
  $('imu-level').addEventListener('click', () => trigger('/imu/level_here'));
  $('imu-heading').addEventListener('click', () => trigger('/imu/heading_zero'));
  $('imu-forget').addEventListener('click', async () => {
    const yes = await confirmDialog({ title: 'Forget the calibration?', icon: 'fa-rotate-left', ok: 'Forget',
      lines: ['The levelling is dropped and saved: the tilt the box sits at shows again until you press Level here.'] });
    if (yes) trigger('/imu/forget_calibration');
  });
  $('imu-done4').addEventListener('click', () => { checks.mark(4); showChecks(); });
  $('imu-checks-again').addEventListener('click', () => { checks.reset(); showChecks(); });

  const onResize = () => { if (visible && sphere) sphere.resize(); };
  window.addEventListener('resize', onResize);
  showChecks();

  return {
    show() {
      visible = true;
      try { telemetry = localStorage.getItem('r2web.telemetry') === '1'; } catch { telemetry = false; }
      $('imu-telemetry').checked = telemetry;
      if (!sphere) {
        try { sphere = createImuSphere($('imu-sphere')); } catch { /* no WebGL: the dials still work */ }
      } else sphere.resize();
      subscribe('/imu/status', 'std_msgs/msg/String', onStatus, 500);
      listen();
      clearInterval(timer);
      timer = setInterval(showStatus, 1000);      // a node that stops talking turns the pills red
    },
    hide() {
      visible = false;
      unsubscribe('/imu/status', onStatus);
      unsubscribe('/imu/data', onData);
      clearInterval(timer);
      timer = null;
    },
  };
}
