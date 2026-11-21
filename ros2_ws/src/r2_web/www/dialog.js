// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The console's own confirmation window, instead of the browser's confirm(): same colours and
// buttons as the rest of the console. Esc or Cancel = no; Enter or the main button = yes.
//   if (await confirmDialog({ title, lines: ['…', '…'], ok: 'Flash', icon: 'fa-microchip', warn: '…' })) …
let style = false;

function addStyle() {
  if (style) return;
  style = true;
  const s = document.createElement('style');
  s.textContent = `
    dialog.r2dlg { max-width: min(480px, calc(100vw - 32px)); padding: 0; border-radius: 12px; border: 1px solid #3a4250;
      background: #161b22; color: #e6edf3; font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
      box-shadow: 0 16px 48px rgba(0,0,0,.6); }
    dialog.r2dlg::backdrop { background: rgba(1,4,9,.65); }
    .r2dlg h3 { margin: 0; padding: 14px 18px; font-size: 15px; display: flex; gap: 10px; align-items: center;
      border-bottom: 1px solid #2a313c; }
    .r2dlg .body { padding: 14px 18px; }
    .r2dlg .body p { margin: 0 0 10px; }
    .r2dlg .warn { color: #e3b341; display: flex; gap: 8px; align-items: baseline; }
    .r2dlg .acts { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 18px; border-top: 1px solid #2a313c; }
    .r2dlg button { background: #2a313c; color: #e6edf3; border: 1px solid #3a4250; border-radius: 6px; padding: 6px 14px;
      font: inherit; cursor: pointer; display: inline-flex; gap: 8px; align-items: center; }
    .r2dlg button:hover { filter: brightness(1.15); }
    .r2dlg button.primary { background: #1f6feb; border-color: #388bfd; }`;
  document.head.append(s);
}

const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;     // text from the Pi goes in as text, never as HTML
  return e;
};
const icon = (name) => el('i', `fa-solid ${name}`);

export function confirmDialog({ title, lines = [], warn = '', ok = 'OK', cancel = 'Cancel', icon: ic = 'fa-circle-question' }) {
  addStyle();
  return new Promise((resolve) => {
    const d = el('dialog', 'r2dlg');
    const h = el('h3');
    h.append(icon(ic), document.createTextNode(title));
    const body = el('div', 'body');
    for (const l of lines) body.append(el('p', '', l));
    if (warn) {
      const w = el('p', 'warn');
      w.append(icon('fa-triangle-exclamation'), document.createTextNode(warn));
      body.append(w);
    }
    const acts = el('div', 'acts');
    const no = el('button', '', cancel);
    const yes = el('button', 'primary', ok);
    no.type = yes.type = 'button';
    acts.append(no, yes);
    d.append(h, body, acts);
    const done = (v) => { d.close(); d.remove(); resolve(v); };
    no.addEventListener('click', () => done(false));
    yes.addEventListener('click', () => done(true));
    d.addEventListener('cancel', (e) => { e.preventDefault(); done(false); });   // Esc
    document.body.append(d);
    d.showModal();
    yes.focus();
  });
}
