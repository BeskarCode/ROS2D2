// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// Navigation page: what Patrol and Free roam's head (the wander node, /wander/state) shows. Pure: node --test.

const HEAD = { walk: 'walking', look: 'looking around', greet: 'saying hello', turn_away: 'turning away' };

/** Patrol's circle round where it started, in pixels: {cx, cy, r}, or null (Free roam, no start yet).
 *  toPx(x, y) -> [px, py] and toLen(metres) -> px are the map's. */
export function radiusCircle(st, toPx, toLen) {
  if (!st || st.mode !== 'patrol' || !Array.isArray(st.start) || !st.radius) return null;
  const [cx, cy] = toPx(st.start[0], st.start[1]);
  return { cx, cy, r: toLen(st.radius) };
}

/** What the head is doing, in words ('' with no state). */
export function headLabel(st) {
  if (!st || !st.state) return '';
  return HEAD[st.state] || st.state;
}
