// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// rosbridge for the setup page: one websocket, service calls, parameters and throttled
// subscriptions (sent again after a reconnect).
const WS_URL = `ws://${location.hostname || 'localhost'}:9090`;

let ws = null;
let callId = 0;
const pending = {};
const handlers = {};       // topic -> callback
const subs = {};           // topic -> subscribe message, to send again on reconnect

export function connect(onOpen) {
  ws = new WebSocket(WS_URL);
  ws.onopen = () => { advertised.clear(); Object.values(subs).forEach(send); onOpen(); };
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.op === 'publish' && handlers[m.topic]) handlers[m.topic](m.msg);
    if (m.op === 'service_response' && pending[m.id]) { pending[m.id](m.result ? m.values : null); delete pending[m.id]; }
  };
  ws.onclose = () => setTimeout(() => connect(onOpen), 2000);
}

const send = (o) => ws && ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify(o));

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
    : Number.isInteger(value) ? { type: 2, integer_value: value } : { type: 3, double_value: value };
  return call(`${node}/set_parameters`, 'rcl_interfaces/srv/SetParameters', { parameters: [{ name, value: v }] });
}

export function subscribe(topic, type, cb, throttleMs = 0) {
  handlers[topic] = cb;
  subs[topic] = { op: 'subscribe', topic, type, throttle_rate: throttleMs, queue_length: 1 };
  send(subs[topic]);
}

const advertised = new Set();
export function publish(topic, type, msg) {
  if (!advertised.has(topic)) { send({ op: 'advertise', topic, type }); advertised.add(topic); }
  send({ op: 'publish', topic, msg });
}
