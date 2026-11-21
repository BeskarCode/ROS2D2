// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Remote -> Shortcuts, without the page (tested with node --test, test/shortcuts.test.mjs): every
// combination that does something, what it does, and which buttons the two virtual Navs press for it.
//
// How the sketch reads a combination (ShadowMDLite.ino, checkFoot*/checkDome*): it fires on the FIRST
// loop the arrow is down, and only if no arrow was down in the second before. So the modifier buttons
// go down first, the arrow after them, and two shortcuts need more than a second between them.
// With a dome Nav connected (the Remote window keeps the virtual one on), Cross, Circle, PS and L3 for
// a foot arrow come from the DOME Nav, and for a dome arrow from the FOOT Nav; L1 and L2 stay on the
// arrow's own Nav.
import { COMBOS, FACE_TRACKING, MODES, MODE_LABELS, comboLabel } from './modesform.js';

export const PRE_MS = 150;     // modifiers alone, before the arrow
export const HOLD_MS = 350;    // then everything together
export const GAP_MS = 1200;    // before the next shortcut (the sketch waits for 1 s without arrows)

const ARROWS = ['UP', 'DOWN', 'LEFT', 'RIGHT'];
const OTHER_NAV = ['CROSS', 'CIRCLE', 'PS', 'L3'];

// ShadowMD Lite's default MarcDuino map (CheatSheet.md); the free ones (0) are left out
export const MD_ACTIONS = {
  FOOT_UP: 'Scream, all panels open', FOOT_DOWN: 'Lights reset', FOOT_LEFT: 'Mid awake', FOOT_RIGHT: 'Full awake',
  DOME_UP: 'Open body doors, arms and tools', DOME_DOWN: 'Data panel door (open / close)',
  DOME_LEFT: 'Use the interface tool', DOME_RIGHT: 'Use the gripper',
  FOOT_UP_CROSS: 'Volume up', FOOT_DOWN_CROSS: 'Volume down',
  FOOT_LEFT_CROSS: 'Front holo lights (on / off)', FOOT_RIGHT_CROSS: 'Rear holo lights (on / off)',
  DOME_UP_CROSS: 'Utility arms (open / close)', DOME_DOWN_CROSS: 'Close the body panels',
  DOME_LEFT_CROSS: 'Open all dome panels', DOME_RIGHT_CROSS: 'Close all panels',
  FOOT_UP_CIRCLE: 'Wave, one panel at a time (no sound)', FOOT_LEFT_CIRCLE: 'Fast smirk wave (no sound)',
  FOOT_RIGHT_CIRCLE: 'Marching ants (no sound)', FOOT_DOWN_CIRCLE: 'Cantina dance (no sound)',
  DOME_UP_CIRCLE: 'Cantina dance', DOME_LEFT_CIRCLE: 'Disco',
  DOME_RIGHT_CIRCLE: 'Star Wars disco dance', DOME_DOWN_CIRCLE: 'Star Trek disco dance',
  FOOT_UP_L1: 'Leia message', FOOT_LEFT_L1: 'Wave, dome and body',
  FOOT_RIGHT_L1: 'Wave 2: open all, close one by one',
  DOME_UP_L1: 'Fast smirk wave', DOME_LEFT_L1: 'Use the gripper', DOME_RIGHT_L1: 'Use the interface tool',
  DOME_DOWN_L1: 'Wave 2 (no sound)',
  FOOT_UP_PS: 'Open all dome panels', FOOT_DOWN_PS: 'Close all panels',
  FOOT_LEFT_PS: 'Previous song', FOOT_RIGHT_PS: 'Next song',
  DOME_UP_PS: 'Utility arms open, then close', DOME_LEFT_PS: 'Top utility arm (open / close)',
  DOME_RIGHT_PS: 'Bottom utility arm (open / close)', DOME_DOWN_PS: 'Ping-pong body doors',
};

// 'FOOT_UP_CROSS' -> { first: { F: [], D: ['CROSS'] }, then: { F: ['UP'], D: ['CROSS'] } }
export function stepsFor(combo) {
  const [nav, ...parts] = combo.split('_');
  const own = nav === 'FOOT' ? 'F' : 'D', other = own === 'F' ? 'D' : 'F';
  const first = { F: [], D: [] };
  const arrow = parts.find((p) => ARROWS.includes(p));
  if (!arrow) {                                  // PS + L2: PS first, then L2
    first[own].push(parts[0]);
    return { first, then: { ...{ F: [], D: [] }, [own]: [...parts], [other]: [] } };
  }
  for (const m of parts.filter((p) => p !== arrow)) first[OTHER_NAV.includes(m) ? other : own].push(m);
  const then = { F: [...first.F], D: [...first.D] };
  then[own].push(arrow);
  return { first, then };
}

// What each combination does now: a mode (from modes.yaml) wins over its MarcDuino action.
// Modes first, then face tracking, then the MarcDuino actions in the firmware's order.
export function shortcutList(modes = {}) {
  const modeOf = {};
  for (const m of MODES) if (modes[m] && modes[m].combo) modeOf[modes[m].combo] = m;
  const out = [];
  for (const combo of COMBOS) {
    const label = comboLabel(combo);
    if (modeOf[combo]) out.push({ combo, label, kind: 'mode', what: `${MODE_LABELS[modeOf[combo]]} (on / off)` });
    else if (MD_ACTIONS[combo]) out.push({ combo, label, kind: 'marcduino', what: MD_ACTIONS[combo] });
  }
  out.push({ combo: FACE_TRACKING, label: comboLabel(FACE_TRACKING), kind: 'tracking', what: 'Face tracking (on / off)' });
  const rank = { mode: 0, tracking: 1, marcduino: 2 };
  return out.sort((a, b) => rank[a.kind] - rank[b.kind]);   // stable: keeps the firmware's order inside
}
