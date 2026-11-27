// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// When the ROS2D2 system stops answering, the page that is already loaded says so kindly instead of failing bit by
// bit: a cover with what is down (the Pi's web server, or ROS through rosbridge), for how long, and
// it goes away by itself when both are back. Moving to another section first checks that the Pi
// answers, so the browser's own "can't reach this page" never shows: it waits here and goes on.
//   import './offline.js'                 (each page; the header's section links are handled)
//   reportRos(true | false)               (whoever owns the rosbridge socket: on open / on close)
import { toast } from './savekey.js';

const PING_MS = 4000;          // how often the web server is asked while all is well
const RETRY_MS = 2000;         // and while it is down
const GRACE_MS = 6000;         // a cut shorter than this shows nothing (a reconnect, a restart blip)
const PING_TIMEOUT_MS = 2500;

let webOk = true, rosOk = true, rosDownAt = 0, webFails = 0;
let downSince = 0, shown = false, goTo = null, cover = null, timer = null;

function ensureCover() {
  if (cover) return cover;
  const style = document.createElement('style');
  style.textContent = `
    .r2off { position: fixed; inset: 0; z-index: 9000; display: grid; place-items: center; padding: 16px;
      background: rgba(1,4,9,.78); backdrop-filter: blur(2px); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
    .r2off[hidden] { display: none; }
    .r2off .card { max-width: 440px; width: 100%; background: var(--panel); color: var(--text); border: 1px solid var(--line2);
      border-radius: 12px; padding: 20px 22px; box-shadow: 0 16px 48px rgba(0,0,0,.6); text-align: center; }
    .r2off h3 { margin: 6px 0 8px; font-size: 17px; }
    .r2off .big { font-size: 30px; color: var(--amber); }
    .r2off p { margin: 6px 0; color: var(--muted); }
    .r2off .what { color: var(--text); }
    .r2off button { width: auto; margin: 12px auto 0; background: var(--line); color: var(--text); border: 1px solid var(--line2); border-radius: 6px;
      padding: 6px 14px; font: inherit; cursor: pointer; display: inline-flex; gap: 8px; align-items: center; }`;
  document.head.append(style);
  cover = document.createElement('div');
  cover.className = 'r2off';
  cover.hidden = true;
  cover.setAttribute('role', 'alertdialog');
  cover.setAttribute('aria-live', 'assertive');
  cover.innerHTML = `<div class="card"><div class="big"><i class="fa-solid fa-plug-circle-exclamation"></i></div>
    <h3>The ROS2D2 system is not answering</h3><p class="what"></p>
    <p><i class="fa-solid fa-spinner fa-spin"></i> Waiting for it to come back… <span class="secs"></span></p>
    <p class="go" hidden></p>
    <button type="button"><i class="fa-solid fa-rotate-right"></i>Reload now</button></div>`;
  cover.querySelector('button').addEventListener('click', () => location.reload());
  document.body.append(cover);
  return cover;
}

function render() {
  const down = !webOk || !rosOk;
  const now = Date.now();
  if (down && !downSince) downSince = now;
  if (!down) {
    const was = shown;
    downSince = 0;
    shown = false;
    if (cover) cover.hidden = true;
    if (goTo) { const u = goTo; goTo = null; location.href = u; return; }
    if (was) toast('ROS2D2 is back: connection recovered', 'ok');
    return;
  }
  // a short cut shows nothing; a page change waiting on it shows at once
  if (!shown && now - downSince < GRACE_MS && !goTo) return;
  shown = true;
  const c = ensureCover();
  c.querySelector('.what').textContent = !webOk
    ? "The Pi's web server does not answer: the Pi may be off, restarting, or out of WiFi range."
    : 'The Pi answers, but ROS does not (ROS2D2 is restarting, or its bridge to the browser is down).';
  c.querySelector('.secs').textContent = `(${Math.round((now - downSince) / 1000)} s)`;
  const go = c.querySelector('.go');
  go.hidden = !goTo;
  if (goTo) go.textContent = `It will open ${new URL(goTo).pathname.replace(/^\//, '') || 'the console'} as soon as it answers.`;
  c.hidden = false;
}

async function pingWeb() {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), PING_TIMEOUT_MS);
  try {
    const r = await fetch('api/ping', { cache: 'no-store', signal: ctl.signal });   // nothing to compute: just alive
    return r.ok;
  } catch { return false; } finally { clearTimeout(t); }
}

async function tick() {
  clearTimeout(timer);
  if (document.visibilityState === 'visible' || goTo) {
    const ok = await pingWeb();
    webFails = ok ? 0 : webFails + 1;
    webOk = webFails < 2;            // one lost answer is not a fall
    if (!rosOk && rosDownAt && Date.now() - rosDownAt < GRACE_MS) { /* give the socket its retry first */ }
    render();
  }
  timer = setTimeout(tick, webOk && rosOk ? PING_MS : RETRY_MS);
}

/** The rosbridge socket opened (true) or closed (false). */
export function reportRos(ok) {
  if (ok === rosOk) return;
  rosOk = ok;
  rosDownAt = ok ? 0 : Date.now();
  render();
  if (!ok) { clearTimeout(timer); timer = setTimeout(tick, RETRY_MS); }
}

// The header's section links: check the Pi answers before leaving this (loaded) page
document.addEventListener('click', async (e) => {
  const a = e.target.closest && e.target.closest('a[href]');
  if (!a || e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || a.target === '_blank') return;
  const url = new URL(a.href, location.href);
  if (url.origin !== location.origin || !/\.html$|\/$/.test(url.pathname)) return;
  e.preventDefault();
  if (await pingWeb()) { location.href = url.href; return; }
  webOk = false;
  webFails = 2;
  goTo = url.href;
  render();
  clearTimeout(timer);
  timer = setTimeout(tick, RETRY_MS);
});

document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') tick(); });
timer = setTimeout(tick, PING_MS);
