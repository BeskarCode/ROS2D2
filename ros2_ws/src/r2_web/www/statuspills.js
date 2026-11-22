// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The header's status pills, the same on every page: ROS, Mega, Navs, Pico, Lidar, Camera, Mode, each as
// "Name: state" (green ok, amber so-so, red gone, grey not known yet). Pure: tested with node --test.
const FRESH_MS = 3000;
const MODE_LABELS = { goto: 'Go to a point', forward: 'Go forward', patrol: 'Patrol', follow: 'Follow a colour' };

const pill = (key, icon, text, cls, title, href) => ({ key, icon, text, cls, title, href });

// The two PS3 Navs the Mega has (/mega/pads): real, the console's virtual one, or none
function navsPill(p) {
  const title = 'The controllers the Mega has: real PS3 Navs, or the virtual ones of the Remote window or the phone view';
  if (!p || !p.mega || p.supported === null || p.supported === undefined) return pill('navs', 'fa-gamepad', 'Navs: …', '', title);
  if (p.supported === false) return pill('navs', 'fa-gamepad', 'Navs: ?', '', `${title} (this Mega firmware does not report them)`);
  const n = ['F', 'D'].filter((k) => p[k] && p[k] !== 'none').length;
  const text = n ? `Navs: foot ${p.F} · dome ${p.D}` : 'Navs: none';
  return pill('navs', 'fa-gamepad', text, n === 2 ? 'ok' : n ? 'warn' : 'bad', title);
}

export function statusPills(s, now) {
  const fresh = (t) => t && now - t < FRESH_MS;
  const out = [];
  out.push(pill('ros', 'fa-plug', `ROS: ${s.ros == null ? '…' : s.ros ? 'connected' : 'not connected'}`,
    s.ros == null ? '' : s.ros ? 'ok' : 'bad', 'The page talking to ROS on the Pi (rosbridge)'));
  out.push(pill('mega', 'fa-microchip', `Mega: ${s.mega == null ? '…' : s.mega ? 'connected' : 'not connected'}`,
    s.mega == null ? '' : s.mega ? 'ok' : 'bad', 'The Mega (ShadowMD) on the Pi\'s USB'));
  out.push(navsPill(s.pads));
  const picoOn = fresh(s.picoAt) && s.pico && s.pico.connected;
  out.push(pill('pico', 'fa-microchip', `Pico: ${s.picoAt == null ? '…' : picoOn ? (s.pico.firmware || 'connected') : 'not connected'}`,
    s.picoAt == null ? '' : picoOn ? 'ok' : 'bad',
    picoOn && s.pico.commit ? `The Pico sensor board · firmware ${s.pico.firmware} · ${s.pico.commit}` : 'The Pico sensor board', 'setup.html#system'));
  out.push(pill('lidar', 'fa-satellite-dish', `Lidar: ${s.scanAt == null ? '…' : fresh(s.scanAt) ? 'scanning' : 'no scans'}`,
    s.scanAt == null ? '' : fresh(s.scanAt) ? 'ok' : 'warn', 'The lidar\'s scans (/scan)', 'setup.html#sensors'));
  const cams = Object.values(s.cams || {});
  const live = cams.filter(fresh).length;
  let camText = 'Camera: none', camCls = '';
  if (cams.length === 1) { camText = `Camera: ${live ? 'online' : 'offline'}`; camCls = live ? 'ok' : 'bad'; }
  else if (cams.length > 1) { camText = `Cameras: ${live} of ${cams.length} online`; camCls = live === cams.length ? 'ok' : live ? 'warn' : 'bad'; }
  out.push(pill('cam', 'fa-video', camText, camCls, 'The cameras in cameras.yaml', 'setup.html#cameras'));
  let mode = 'off', modeCls = '';
  if (s.auto && s.mode) { mode = MODE_LABELS[s.mode] || s.mode; modeCls = 'ok'; }
  else if (s.track) { mode = 'face tracking'; modeCls = 'ok'; }
  out.push(pill('mode', 'fa-gamepad', `Mode: ${mode}`, modeCls, 'The automatic mode on, or face tracking (Setup → Modes)', 'setup.html#modes'));
  return out;
}
