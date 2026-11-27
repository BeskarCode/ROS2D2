// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// node --test ros2_ws/src/r2_web/test/*.mjs
// REV-T1 (WEB-1): rosbridge.js against a pretend WebSocket: what reaches rosbridge when two parts of
// a page want the same topic at different rates, the order unsubscribe -> subscribe, and the
// subscriptions sent again after a reconnect.
import test from 'node:test';
import assert from 'node:assert/strict';

// ---- the browser bits rosbridge.js and offline.js touch when they load
const realSetTimeout = globalThis.setTimeout;
globalThis.setTimeout = (fn, ms, ...a) => { const t = realSetTimeout(fn, ms, ...a); t.unref?.(); return t; };
globalThis.location = { hostname: 'r2pi', href: 'http://r2pi:8080/' };
globalThis.document = { addEventListener() {}, visibilityState: 'hidden', createElement: () => ({}), head: { append() {} }, body: { append() {} } };
globalThis.fetch = async () => ({ ok: true, json: async () => ({}) });

const sockets = [];
class FakeWS {
  static CONNECTING = 0; static OPEN = 1; static CLOSING = 2; static CLOSED = 3;
  constructor(url) { this.url = url; this.readyState = FakeWS.CONNECTING; this.sent = []; sockets.push(this); }
  send(s) { this.sent.push(JSON.parse(s)); }
  open() { this.readyState = FakeWS.OPEN; this.onopen?.(); }
  drop() { this.readyState = FakeWS.CLOSED; this.onclose?.(); }
  publish(topic, msg) { this.onmessage?.({ data: JSON.stringify({ op: 'publish', topic, msg }) }); }
}
globalThis.WebSocket = FakeWS;

const rb = await import('../www/rosbridge.js');
const subOps = (ws, topic) => ws.sent.filter((m) => m.topic === topic && (m.op === 'subscribe' || m.op === 'unsubscribe'));

rb.connect();
const ws = sockets[0];
ws.open();

test('a slow subscriber first, a fast one after: rosbridge is asked again at the fast rate', () => {
  const slow = [], fast = [];
  const fSlow = (m) => slow.push(m), fFast = (m) => fast.push(m);
  rb.subscribe('/scan', 'sensor_msgs/msg/LaserScan', fSlow, 2000);       // the status bar
  rb.subscribe('/scan', 'sensor_msgs/msg/LaserScan', fFast, 200);        // Navigation
  const ops = subOps(ws, '/scan');
  assert.deepEqual(ops.map((m) => [m.op, m.throttle_rate]), [['subscribe', 2000], ['unsubscribe', undefined], ['subscribe', 200]]);
  ws.publish('/scan', 1);
  assert.deepEqual([slow.length, fast.length], [1, 1]);
  ws.publish("/scan", 2);                       // straight after: each callback waits for its own rate
  assert.deepEqual([slow.length, fast.length], [1, 1]);
  rb.unsubscribe('/scan', fFast);               // the fast one leaves: back to 2 s
  rb.unsubscribe('/scan', fSlow);               // the last one leaves: unsubscribed
  const after = subOps(ws, '/scan').slice(3).map((m) => [m.op, m.throttle_rate]);
  assert.deepEqual(after, [['unsubscribe', undefined], ['subscribe', 2000], ['unsubscribe', undefined]]);
});

test('a slower subscriber after a faster one sends nothing', () => {
  const before = ws.sent.length;
  const a = () => {}, b = () => {};
  rb.subscribe('/pico/state', 'std_msgs/msg/String', a, 0);
  rb.subscribe('/pico/state', 'std_msgs/msg/String', b, 1000);
  assert.deepEqual(ws.sent.slice(before).map((m) => [m.op, m.throttle_rate]), [['subscribe', 0]]);
  rb.unsubscribe('/pico/state', a);
  rb.unsubscribe('/pico/state', b);
});

test('after a reconnect the subscriptions are sent again, at the rate in force', () => {
  const f = () => {};
  rb.subscribe('/range/tof_front', 'sensor_msgs/msg/Range', f, 100);
  ws.drop();
  rb.connect();                                 // the page reconnects (its 2 s retry, done by hand here)
  const ws2 = sockets.at(-1);
  assert.notEqual(ws2, ws);
  ws2.open();
  assert.deepEqual(subOps(ws2, '/range/tof_front').map((m) => [m.op, m.throttle_rate]), [['subscribe', 100]]);
  rb.unsubscribe('/range/tof_front', f);
});
