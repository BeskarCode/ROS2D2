// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The header's status pills, the same on every page: ROS, Mega, Pico, Lidar, Camera, Mode, each as
// "Name: state" (green ok, amber so-so, red gone, grey not known yet). Pure: tested with node --test.
const FRESH_MS = 3000;
const MODE_LABELS = { goto: 'Go to a point', forward: 'Go forward', patrol: 'Patrol', follow: 'Follow a colour' };

const pill = (key, icon, text, cls, title, href) => ({ key, icon, text, cls, title, href });

export function statusPills(s, now) {
  const fresh = (t) => t && now - t < FRESH_MS;
  const out = [];
  out.push(pill('ros', 'fa-plug', `ROS: ${s.ros == null ? '…' : s.ros ? 'connected' : 'not connected'}`,
    s.ros == null ? '' : s.ros ? 'ok' : 'bad', 'The page talking to ROS on the Pi (rosbridge)'));
  out.push(pill('mega', 'fa-microchip', `Mega: ${s.mega == null ? '…' : s.mega ? 'connected' : 'not connected'}`,
    s.mega == null ? '' : s.mega ? 'ok' : 'bad', 'The Mega (ShadowMD) on the Pi\'s USB'));
  const picoOn = fresh(s.picoAt) && s.pico && s.pico.connected;
  out.push(pill('pico', 'fa-microchip', `Pico: ${s.picoAt == null ? '…' : picoOn ? (s.pico.firmware || 'connected') : 'not connected'}`,
    s.picoAt == null ? '' : picoOn ? 'ok' : 'bad',
    picoOn && s.pico.commit ? `The Pico sensor board · firmware ${s.pico.firmware} · ${s.pico.commit}` : 'The Pico sensor board'));
  out.push(pill('lidar', 'fa-satellite-dish', `Lidar: ${s.scanAt == null ? '…' : fresh(s.scanAt) ? 'scanning' : 'no scans'}`,
    s.scanAt == null ? '' : fresh(s.scanAt) ? 'ok' : 'warn', 'The lidar\'s scans (/scan)'));
  const cams = Object.values(s.cams || {});
  const live = cams.filter(fresh).length;
  let camText = 'Camera: none', camCls = '';
  if (cams.length === 1) { camText = `Camera: ${live ? 'online' : 'offline'}`; camCls = live ? 'ok' : 'bad'; }
  else if (cams.length > 1) { camText = `Cameras: ${live} of ${cams.length} online`; camCls = live === cams.length ? 'ok' : live ? 'warn' : 'bad'; }
  out.push(pill('cam', 'fa-video', camText, camCls, 'The cameras in cameras.yaml'));
  let mode = 'off', modeCls = '';
  if (s.auto && s.mode) { mode = MODE_LABELS[s.mode] || s.mode; modeCls = 'ok'; }
  else if (s.track) { mode = 'face tracking'; modeCls = 'ok'; }
  out.push(pill('mode', 'fa-gamepad', `Mode: ${mode}`, modeCls, 'The automatic mode on, or face tracking (Setup → Modes)', 'setup.html#modes'));
  return out;
}
