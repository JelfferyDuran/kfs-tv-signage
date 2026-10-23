#!/usr/bin/env python3
"""
kfs-display-server.py — control server for the KFS kitchen display TVs.

Serves:
  GET  /scene/<tv_id>          -> current scene JSON for that TV (polled by TVs)
  GET  /content/<file>         -> static content (images/videos)
  POST /set                    -> set a scene: {"tv":"all|menu1|...", "scene":{...}}
  GET  /                        -> status / discovery

Scene types: image, video, menu, url, blank, playlist
  image:    {"type":"image","src":"file.jpg"}
  video:    {"type":"video","src":"file.mp4","loop":true}
  menu:     {"type":"menu","title":"LUNCH","items":[{"name":"...","price":"$9.99"}],"footer":"..."}
  url:      {"type":"url","src":"http://..."}
  blank:    {"type":"blank"}
  playlist: {"type":"playlist","items":[<scene>,...],"interval":15}
            Server-side rotation: polls return the active item, so clients
            need no playlist support.

Content files go in ./content/  (jpg, png, webp, mp4, webm)

Environment:
  KFS_PORT          port (default 8080)
  KFS_TVS           comma-separated known TV ids (default menu1,menu2,menu3)
  KFS_DEVICE_NAMES  friendly names: "menu1=Kitchen 1,menu2=Kitchen 2"
  KFS_AUTOREGISTER  "0" disables auto-registration of unknown device ids
  KFS_API_TOKEN     if set, POST /set requires Authorization: Bearer <token>
"""
import json, mimetypes, os, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(ROOT, "content")
PORT = int(os.environ.get("KFS_PORT", "8080"))
# Comma-separated known TV IDs. Devices that poll with an unknown ID are
# auto-registered (see ensure_tv), so any device can join the ecosystem.
TVS = [t.strip() for t in os.environ.get("KFS_TVS", "menu1,menu2,menu3").split(",") if t.strip()]
DEVICE_NAMES = os.environ.get("KFS_DEVICE_NAMES", "")  # optional: "menu1=Kitchen 1,menu2=Kitchen 2"
_AUTOREG = os.environ.get("KFS_AUTOREGISTER", "1") != "0"
API_TOKEN = os.environ.get("KFS_API_TOKEN", "")  # if set, POST /set needs Bearer

# single-instance guard: bind the same address the server will use; if taken, exit quietly
probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    probe.bind(("0.0.0.0", PORT))
except OSError:
    sys.exit(0)
finally:
    probe.close()

# startup log line
with open(os.path.join(ROOT, "kfs-display-server.log"), "a", encoding="utf-8") as f:
    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  start (pid={os.getpid()})\n")

# state persistence: scenes + registered devices survive restarts
STATE_FILE = os.path.join(ROOT, "kfs-state.json")

def _load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_state = _load_state()
if _state.get("tvs"):
    TVS = _state["tvs"]
scenes = {tv: _state.get("scenes", {}).get(tv, {"type": "blank"}) for tv in TVS}
lock = threading.Lock()

def _save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"tvs": TVS, "scenes": scenes}, f, indent=1)
    except Exception:
        pass

def ensure_tv(tv):
    """Auto-register unknown TV ids so new devices join the ecosystem."""
    if tv in scenes:
        return True
    if _AUTOREG:
        with lock:
            if tv not in scenes:
                TVS.append(tv)
                scenes[tv] = {"type": "blank"}
                _save_state()
                return True
    return False

def set_scene(tv, scene):
    # stamp playlist start time so rotation is deterministic across devices
    if scene.get("type") == "playlist" and "started_at" not in scene:
        scene = dict(scene)
        scene["started_at"] = time.time()
    if tv == "all" or tv == "*":
        with lock:
            for t in list(scenes):
                scenes[t] = scene
            _save_state()
        return True
    if not ensure_tv(tv):
        return False
    with lock:
        scenes[tv] = scene
        _save_state()
    return True

def resolve_playlist(scene):
    """If scene is a playlist, return the active item for the current time."""
    if not scene or scene.get("type") != "playlist":
        return scene
    items = scene.get("items") or []
    if not items:
        return {"type": "blank"}
    interval = max(int(scene.get("interval", 15)), 2)
    started = float(scene.get("started_at", time.time()))
    elapsed = max(0, time.time() - started)
    idx = int(elapsed // interval) % len(items)
    return items[idx]

def _authorized(self):
    if not API_TOKEN:
        return True
    auth = self.headers.get("Authorization", "")
    return auth == f"Bearer {API_TOKEN}"

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        if p.startswith("/scene/"):
            tv = p.split("/")[2]
            ensure_tv(tv)
            with lock:
                scene = scenes.get(tv)
            if scene is None:
                self._json(404, {"error": "unknown tv"})
            else:
                self._json(200, resolve_playlist(scene))
        elif p.startswith("/content/"):
            fname = os.path.basename(p[len("/content/"):])
            fpath = os.path.join(CONTENT_DIR, fname)
            if not os.path.isfile(fpath):
                self._json(404, {"error": "not found"})
                return
            ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
            with open(fpath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        elif p == "/":
            names = {}
            if DEVICE_NAMES:
                for pair in DEVICE_NAMES.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        names[k.strip()] = v.strip()
            self._json(200, {"tvs": TVS, "device_names": names,
                             "scenes": {t: scenes[t] for t in TVS},
                             "content": os.listdir(CONTENT_DIR) if os.path.isdir(CONTENT_DIR) else []})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/set":
            self._json(404, {"error": "not found"})
            return
        if not _authorized(self):
            self._json(401, {"error": "unauthorized — set KFS_API_TOKEN and send Authorization: Bearer <token>"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode() or "{}")
        except Exception:
            self._json(400, {"error": "bad json"})
            return
        tv = body.get("tv", "all")
        scene = body.get("scene")
        if not scene or not isinstance(scene, dict) or "type" not in scene:
            self._json(400, {"error": "scene needs a type"})
            return
        if set_scene(tv, scene):
            self._json(200, {"ok": True, "tv": tv, "scene": scene})
        else:
            self._json(400, {"error": "unknown tv"})

def main():
    os.makedirs(CONTENT_DIR, exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.allow_reuse_address = False  # Windows: SO_REUSEADDR would let a 2nd instance hijack the port
    print(f"KFS display server on :{PORT}  content={CONTENT_DIR}")
    print(f"TVs: {', '.join(TVS)}")
    if API_TOKEN:
        print("API auth: enabled")
    srv.serve_forever()

if __name__ == "__main__":
    main()