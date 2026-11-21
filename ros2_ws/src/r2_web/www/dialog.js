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
    dialog.r2dlg { max-width: min(480px, calc(100vw - 32px)); padding: 0; border-radius: 12px; border: 1px solid var(--line2);
      background: var(--panel); color: var(--text); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
      box-shadow: 0 16px 48px rgba(0,0,0,.6); }
    dialog.r2dlg::backdrop { background: rgba(1,4,9,.65); }
    .r2dlg h3 { margin: 0; padding: 14px 18px; font-size: 15px; display: flex; gap: 10px; align-items: center;
      border-bottom: 1px solid var(--line); }
    .r2dlg .body { padding: 14px 18px; }
    .r2dlg .body p { margin: 0 0 10px; }
    .r2dlg .warn { color: var(--amber); display: flex; gap: 8px; align-items: baseline; }
    .r2dlg .acts { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 18px; border-top: 1px solid var(--line); }
    .r2dlg button { background: var(--line); color: var(--text); border: 1px solid var(--line2); border-radius: 6px; padding: 6px 14px;
      font: inherit; cursor: pointer; display: inline-flex; gap: 8px; align-items: center; }
    .r2dlg button:hover { filter: brightness(1.15); }
    .r2dlg button.primary { background: var(--blue); border-color: var(--blue); }
    .r2dlg input { width: 100%; box-sizing: border-box; background: var(--bg); color: var(--text); border: 1px solid var(--line2);
      border-radius: 6px; padding: 8px 10px; font: inherit; }`;
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

// The same window with a text box: the text typed (trimmed), or null for Cancel / Esc / empty.
//   const name = await promptDialog({ title: 'Name this favourite', value: 'Vol +', max: 20 })
export function promptDialog({ title, lines = [], value = '', max = 40, ok = 'OK', cancel = 'Cancel', icon: ic = 'fa-pen' }) {
  addStyle();
  return new Promise((resolve) => {
    const d = el('dialog', 'r2dlg');
    const h = el('h3');
    h.append(icon(ic), document.createTextNode(title));
    const body = el('div', 'body');
    for (const l of lines) body.append(el('p', '', l));
    const input = el('input');
    input.type = 'text';
    input.maxLength = max;
    input.value = value;
    body.append(input);
    const acts = el('div', 'acts');
    const no = el('button', '', cancel);
    const yes = el('button', 'primary', ok);
    no.type = yes.type = 'button';
    acts.append(no, yes);
    d.append(h, body, acts);
    const done = (v) => { d.close(); d.remove(); resolve(v); };
    no.addEventListener('click', () => done(null));
    yes.addEventListener('click', () => done(input.value.trim() || null));
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); yes.click(); } });
    d.addEventListener('cancel', (e) => { e.preventDefault(); done(null); });
    document.body.append(d);
    d.showModal();
    input.focus();
    input.select();
  });
}
