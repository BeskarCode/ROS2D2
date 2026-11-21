// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Ctrl+S (Cmd+S on a Mac) saves what the page shows, from anywhere on it, and a message floating at
// the bottom of the window says whether it was saved. The browser's own "save page" never opens.
//   onSaveKey(async () => ({ ok: true, text: 'Saved in …' }))   the page's save; ok null = nothing to save
//   toast(text, cls)                                           cls: ok | warn | bad
let box = null, hideTimer = null;

function ensureBox() {
  if (box) return box;
  const style = document.createElement('style');
  style.textContent = `
    .r2toast { position: fixed; left: 50%; bottom: 24px; transform: translate(-50%, 12px); z-index: 10000;
      max-width: min(560px, calc(100vw - 32px)); padding: 10px 16px; border-radius: 10px; font: 14px system-ui, sans-serif;
      display: flex; gap: 10px; align-items: center; color: var(--text); background: #1f2630; border: 1px solid #3d4652;
      box-shadow: 0 8px 28px rgba(0,0,0,.45); opacity: 0; pointer-events: none; transition: opacity .18s, transform .18s; }
    .r2toast.show { opacity: 1; transform: translate(-50%, 0); }
    .r2toast.ok { border-color: var(--green); } .r2toast.ok i { color: var(--green); }
    .r2toast.warn { border-color: var(--amber); } .r2toast.warn i { color: var(--amber); }
    .r2toast.bad { border-color: var(--red); } .r2toast.bad i { color: var(--red); }
    @media (prefers-reduced-motion: reduce) { .r2toast { transition: none; } }`;
  document.head.append(style);
  box = document.createElement('div');
  box.className = 'r2toast';
  box.setAttribute('role', 'status');
  box.setAttribute('aria-live', 'polite');
  document.body.append(box);
  return box;
}

const ICONS = { ok: 'fa-circle-check', warn: 'fa-triangle-exclamation', bad: 'fa-circle-xmark', '': 'fa-spinner fa-spin' };

export function toast(text, cls = 'ok', ms = 3000) {
  const b = ensureBox();
  b.className = `r2toast ${cls} show`;
  b.replaceChildren();
  const i = document.createElement('i');
  i.className = `fa-solid ${ICONS[cls] || ICONS.ok}`;
  b.append(i, document.createTextNode(text));   // text from the Pi goes in as text, never HTML
  clearTimeout(hideTimer);
  if (ms) hideTimer = setTimeout(() => b.classList.remove('show'), ms);
}

export function onSaveKey(save) {
  let busy = false;
  window.addEventListener('keydown', async (e) => {
    if (!(e.ctrlKey || e.metaKey) || e.altKey || e.key.toLowerCase() !== 's') return;
    e.preventDefault();
    if (busy || e.repeat) return;
    busy = true;
    toast('Saving…', '', 0);
    let r;
    try { r = await save(); } catch (err) { r = { ok: false, text: `Not saved: ${err.message || err}` }; }
    busy = false;
    if (!r || r.ok === null) toast(r && r.text ? r.text : 'Nothing to save on this page', 'warn');
    else toast(r.text || (r.ok ? 'Saved' : 'Not saved'), r.ok ? 'ok' : 'bad', r.ok ? 2500 : 5000);
  });
}
