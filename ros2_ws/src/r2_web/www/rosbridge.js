// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// rosbridge for the setup page: one websocket, service calls, parameters and throttled
// subscriptions (sent again after a reconnect).
import { reportRos } from './offline.js';

const WS_URL = `ws://${location.hostname || 'localhost'}:9090`;

let ws = null;
let callId = 0;
const pending = {};
const handlers = {};       // topic -> [callbacks] (two tabs may follow the same topic)
const subs = {};           // topic -> subscribe message, to send again on reconnect

const onOpens = [];
/** One socket per page, shared by everyone who calls this (the page, the status pills, the Remote
 *  window); onOpen runs on every (re)connection. */
export function connect(onOpen) {
  if (onOpen) onOpens.push(onOpen);
  if (ws && ws.readyState <= WebSocket.OPEN) {      // already connecting or open: just join it
    if (ws.readyState === WebSocket.OPEN && onOpen) onOpen();
    return;
  }
  ws = new WebSocket(WS_URL);
  ws.onopen = () => { reportRos(true); advertised.clear(); Object.values(subs).forEach(send); onOpens.forEach((f) => f()); };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.op === 'publish' && handlers[m.topic]) handlers[m.topic].forEach((cb) => cb(m.msg));
    if (m.op === 'service_response' && pending[m.id]) { pending[m.id](m.result ? m.values : null); delete pending[m.id]; }
  };
  ws.onclose = () => { reportRos(false); setTimeout(() => connect(), 2000); };
}

/** Send if the socket is open; true if it went. */
function send(o) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return false;
  ws.send(JSON.stringify(o));
  return true;
}

export function call(service, type, args) {
  return new Promise((resolve) => {
    const id = 'c' + (++callId);
    pending[id] = resolve;
    send({ op: 'call_service', id, service, type, args });
    setTimeout(() => { if (pending[id]) { delete pending[id]; resolve(null); } }, 3000);
  });
}

export function setParam(node, name, value) {
  const v = typeof value === 'boolean' ? { type: 1, bool_value: value }
    : typeof value === 'string' ? { type: 4, string_value: value }
    : Number.isInteger(value) ? { type: 2, integer_value: value } : { type: 3, double_value: value };
  return call(`${node}/set_parameters`, 'rcl_interfaces/srv/SetParameters', { parameters: [{ name, value: v }] });
}

export function subscribe(topic, type, cb, throttleMs = 0) {
  (handlers[topic] = handlers[topic] || []).push(cb);
  if (subs[topic]) return;             // already subscribed: the new callback shares it
  subs[topic] = { op: 'subscribe', topic, type, throttle_rate: throttleMs, queue_length: 1 };
  send(subs[topic]);
}

/** Stop one callback; the last one gone, stop the topic (a tab that is not on screen reads nothing). */
export function unsubscribe(topic, cb) {
  handlers[topic] = (handlers[topic] || []).filter((f) => f !== cb);
  if (handlers[topic].length || !subs[topic]) return;
  delete subs[topic];
  send({ op: 'unsubscribe', topic });
}

const advertised = new Set();
/** Advertise a topic ahead of its first message: ROS needs a moment to match publisher and
 *  subscriber, and a message published along with the advertise can be lost. */
export function advertise(topic, type) {
  if (!advertised.has(topic) && send({ op: 'advertise', topic, type })) advertised.add(topic);
}
/** Open the socket if this page has not (the console page talks to rosbridge on its own). */
export function ensureConnected() {
  if (!ws) connect(() => {});
}

export function publish(topic, type, msg) {
  advertise(topic, type);
  send({ op: 'publish', topic, msg });
}
