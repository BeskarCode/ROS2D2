// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// One virtual PS3 Nav of the Remote window, without the page: what is pressed and what goes to the
// Mega. Pure, tested with node --test (test/padlogic.test.mjs).
//
// With a mouse two buttons cannot be pressed at once, so: a click presses and releases; holding a
// button longMs leaves it HELD (the Mega sees it pressed all along); the next click sends the held
// ones plus that one together for comboMs and lets them all go. A click on a held button lets it go;
// Esc lets every hold go. A hold stays pressed while the stick moves and goes when it is let go.

// Bit order, as the Mega reads it (DroidButton / VirtualPad.h)
export const BUTTONS = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'CROSS', 'CIRCLE', 'L1', 'L2', 'L3', 'PS'];

export const maskOf = (names) => [...names].reduce((m, n) => m | (1 << BUTTONS.indexOf(n)), 0);

const CENTRE = 128;

export function createPad({ longMs = 600, comboMs = 300 } = {}) {
  const held = new Set();
  const downs = new Map();          // name -> when it went down (not promoted to a hold yet)
  const promoted = new Set();       // went to HOLD while still pressed: its release is no click
  const letGo = new Set();          // pressed while held: its release lets it go
  let pulse = null;                 // { mask, until }: a click or a combination being sent
  let x = CENTRE, y = CENTRE, stickOn = false;
  let forced = 0;                   // a shortcut's buttons (Remote -> Shortcuts)

  const promote = (name) => { downs.delete(name); promoted.add(name); held.add(name); };

  return {
    down(name, t) {
      if (held.has(name)) letGo.add(name);
      else downs.set(name, t);
      return { action: null };
    },

    // Buttons pressed long enough to become HOLD now (the window marks them)
    tick(t) {
      const now = [];
      for (const [name, at] of downs) if (t - at >= longMs) { promote(name); now.push(name); }
      return now;
    },

    up(name, t) {
      if (letGo.delete(name)) { held.delete(name); return { action: 'let-go' }; }
      if (promoted.delete(name)) return { action: 'hold' };
      if (!downs.has(name)) return { action: null };
      const at = downs.get(name);
      if (t - at >= longMs) { promote(name); promoted.delete(name); return { action: 'hold' }; }
      downs.delete(name);
      const combo = held.size > 0;
      pulse = { mask: maskOf([...held, name]), until: t + comboMs };
      held.clear();                 // their bits stay in the pulse: no gap for the Mega
      return { action: combo ? 'combo' : 'tap' };
    },

    stick(nx, ny) { x = nx; y = ny; stickOn = true; },

    stickUp() { x = CENTRE; y = CENTRE; stickOn = false; held.clear(); },

    esc() { held.clear(); letGo.clear(); promoted.clear(); },

    reset() {
      held.clear(); downs.clear(); promoted.clear(); letGo.clear();
      pulse = null; x = CENTRE; y = CENTRE; stickOn = false; forced = 0;
    },

    force(mask) { forced = mask; },

    held() { return new Set(held); },

    // a button is down and not yet decided (tap or HOLD): the window keeps ticking to mark the HOLD
    pressing() { return downs.size > 0; },

    state(t) {
      let buttons = maskOf(held);
      if (pulse && t < pulse.until) buttons |= pulse.mask;
      buttons |= forced;
      return { buttons, x, y };
    },

    active(t) {
      const s = this.state(t);
      return s.buttons !== 0 || stickOn || s.x !== CENTRE || s.y !== CENTRE;
    },
  };
}

// Who drives the virtual Navs (/mega/pads' owner), from this page's point of view
export function ownerState(pads, me) {
  const owner = pads && pads.owner;
  if (!owner) return 'free';
  return owner === me ? 'mine' : 'other';
}
