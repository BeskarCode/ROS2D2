"""Serve a PC webcam as an MJPEG stream, the same format an ESP32-CAM gives.

Lets the ROS2D2 container (or the Pi) use a webcam plugged into Windows:

    python webcam_mjpeg.py [camera index] [port]
    camera node source:  http://host.docker.internal:8081/stream

http://localhost:8081/ is a test page: the picture plus what the bench is doing
(phase, countdown, face seen, dome speed), with Start and Stop buttons.
The bench and the buttons share the small JSON state at /state.
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

INDEX = int(sys.argv[1]) if len(sys.argv) > 1 else 0
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8081

latest = None
cond = threading.Condition()
state = {"phase": "idle"}
state_lock = threading.Lock()

PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>ROS2D2 banco de pruebas</title>
<style>
 body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif;text-align:center}
 #phase{font-size:2.4em;font-weight:700;padding:.4em;margin:0}
 #hint{font-size:1.2em;min-height:1.4em;margin:0 0 .4em}
 #count{font-size:4em;font-weight:800;min-height:1.1em}
 img{max-width:95vw;max-height:55vh;border:4px solid #444;border-radius:6px}
 .row{display:flex;justify-content:center;gap:2em;font-size:1.4em;margin:.5em}
 #bar{position:relative;width:min(600px,90vw);height:28px;margin:.4em auto;background:#333;border-radius:4px}
 #fill{position:absolute;top:0;bottom:0;background:#4c9}
 #mid{position:absolute;left:50%;top:-4px;bottom:-4px;width:2px;background:#eee}
 .idle{background:#333}.build{background:#555}.starting{background:#b80}
 .ready{background:#26a}.move{background:#2a6}.done{background:#246}
 button{font-size:1.4em;padding:.4em 1.4em;margin:.3em;border:0;border-radius:6px;cursor:pointer}
 button:disabled{opacity:.3;cursor:default}
 #go{background:#2a6;color:#fff}#stop{background:#c33;color:#fff}
</style></head><body>
<p id="phase" class="idle">Esperando</p>
<p id="hint"></p>
<div id="count"></div>
<div><button id="go" disabled>Empezar</button><button id="stop" disabled>Parar</button></div>
<img src="/stream" alt="webcam">
<div class="row"><span id="face">Cara: -</span><span id="speed">Velocidad dome: -</span></div>
<div id="bar"><div id="fill"></div><div id="mid"></div></div>
<p id="summary"></p>
<script>
const T = {
 idle: ["Esperando", "Aun no ha arrancado la prueba"],
 build: ["Preparando", "Compilando. Quedate quieto, todavia no"],
 starting: ["Preparate", "Arrancando los nodos..."],
 ready: ["Listo", "Colocate y pulsa Empezar"],
 move: ["MUEVETE", "Despacio, de un lado a otro"],
 done: ["Terminado", "Ya puedes parar"]};
const send = d => fetch("/state", {method: "POST", body: JSON.stringify(d)});
document.getElementById("go").onclick = () => send({start: true});
document.getElementById("stop").onclick = () => send({stop: true});
async function tick() {
  try {
    const s = await (await fetch("/state")).json();
    const t = T[s.phase] || [s.phase, ""];
    const ph = document.getElementById("phase");
    ph.textContent = t[0]; ph.className = s.phase;
    document.getElementById("hint").textContent = t[1];
    document.getElementById("count").textContent =
      s.remaining != null && s.phase != "done" ? Math.ceil(s.remaining) + " s" : "";
    document.getElementById("face").textContent =
      "Cara: " + (s.face == null ? "-" : s.face ? "SI" : "no");
    const v = s.speed;
    document.getElementById("speed").textContent = "Velocidad dome: " + (v == null ? "-" : v);
    const f = document.getElementById("fill"), w = Math.min(Math.abs(v || 0), 127) / 127 * 50;
    f.style.width = w + "%"; f.style.left = (v < 0 ? 50 - w : 50) + "%";
    document.getElementById("summary").textContent = s.summary || "";
    document.getElementById("go").disabled = !(s.phase == "ready" && !s.start);
    document.getElementById("stop").disabled = s.phase != "move";
  } catch (e) {}
  setTimeout(tick, 200);
}
tick();
</script></body></html>
"""


def capture():
    global latest
    cap = cv2.VideoCapture(INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        sys.exit(f"cannot open camera {INDEX}")
    print(f"camera {INDEX} open, test page http://localhost:{PORT}/", flush=True)
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with cond:
            latest = jpg.tobytes()
            cond.notify_all()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
        elif self.path == "/state":
            with state_lock:
                body = json.dumps(state).encode()
            self._send(200, "application/json", body)
        elif self.path == "/stream":
            self._stream()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/state":
            self.send_error(404)
            return
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        with state_lock:
            if data.get("reset"):
                state.clear()
            state.update({k: v for k, v in data.items() if k != "reset"})
            state["updated"] = time.time()
        self._send(204, "text/plain", b"")

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while True:
                with cond:
                    cond.wait()
                    jpg = latest
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                 b"Content-Length: %d\r\n\r\n" % len(jpg) + jpg + b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *args):
        pass


threading.Thread(target=capture, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
