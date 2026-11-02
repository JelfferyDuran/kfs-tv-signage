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
import json, mimetypes, os, re, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

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
    print(f"port {PORT} already in use (another server running?) - exiting", file=sys.stderr)
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
    # merge: persisted devices first, then any new ids added via KFS_TVS
    TVS = list(_state["tvs"]) + [t for t in TVS if t not in _state["tvs"]]
scenes = {tv: _state.get("scenes", {}).get(tv, {"type": "blank"}) for tv in TVS}
lock = threading.Lock()

def _save_state():
    # atomic write: a crash mid-write must not wipe every device's scene
    tmp = STATE_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"tvs": TVS, "scenes": scenes}, f, indent=1)
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        print(f"WARNING: could not save state: {e}", file=sys.stderr)

_ID_OK = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SCENE_TYPES = ("image", "video", "menu", "url", "blank", "playlist")

def validate_scene(scene, nested=False):
    """Return an error string, or None if the scene is valid."""
    if not isinstance(scene, dict) or scene.get("type") not in SCENE_TYPES:
        return f"scene.type must be one of {', '.join(SCENE_TYPES)}"
    t = scene["type"]
    if t in ("image", "video", "url") and not isinstance(scene.get("src"), str):
        return f"{t} scene needs a string src"
    if t == "menu" and not isinstance(scene.get("items", []), list):
        return "menu items must be a list"
    if t == "playlist":
        if nested:
            return "playlists cannot be nested"
        items = scene.get("items")
        if not isinstance(items, list) or not items:
            return "playlist needs a non-empty items list"
        try:
            if float(scene.get("interval", 15)) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return "playlist interval must be a positive number"
        for it in items:
            err = validate_scene(it, nested=True)
            if err:
                return "playlist item: " + err
    return None

def ensure_tv(tv):
    """Auto-register unknown TV ids so new devices join the ecosystem."""
    if tv in scenes:
        return True
    if _AUTOREG and _ID_OK.match(tv or ""):
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
    try:
        interval = max(float(scene.get("interval", 15)), 2)
    except (TypeError, ValueError):
        interval = 15
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

    def _send_file(self, fname):
        fpath = os.path.join(CONTENT_DIR, fname)
        if not fname or not os.path.isfile(fpath):
            self._json(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
        size = os.path.getsize(fpath)
        start, end = 0, size - 1
        m = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", ""))
        partial = bool(m and (m.group(1) or m.group(2)))
        if partial:
            if m.group(1):
                start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
            else:  # suffix range: last N bytes
                start = max(0, size - int(m.group(2)))
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        # stream in chunks instead of loading whole videos into memory
        try:
            with open(fpath, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # client (e.g. video element) aborted mid-transfer

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
            self._send_file(os.path.basename(unquote(p[len("/content/"):])))
        elif p == "/":
            names = {}
            if DEVICE_NAMES:
                for pair in DEVICE_NAMES.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        names[k.strip()] = v.strip()
            with lock:
                snap = {t: scenes[t] for t in TVS}
            self._json(200, {"tvs": list(snap), "device_names": names,
                             "scenes": snap,
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
        if not isinstance(body, dict):
            self._json(400, {"error": "bad json"})
            return
        tv = body.get("tv", "all")
        if not isinstance(tv, str):
            self._json(400, {"error": "tv must be a string"})
            return
        scene = body.get("scene")
        err = validate_scene(scene)
        if err:
            self._json(400, {"error": err})
            return
        if set_scene(tv, scene):
            self._json(200, {"ok": True, "tv": tv, "scene": scene})
        else:
            self._json(400, {"error": "unknown tv"})

class Server(ThreadingHTTPServer):
    # Must be a class attribute: it is read during __init__ (bind). Setting it
    # on the instance afterwards had no effect. On Windows SO_REUSEADDR would
    # let a 2nd instance hijack the port.
    allow_reuse_address = False
    daemon_threads = True

def main():
    os.makedirs(CONTENT_DIR, exist_ok=True)
    srv = Server(("0.0.0.0", PORT), Handler)
    print(f"KFS display server on :{PORT}  content={CONTENT_DIR}")
    print(f"TVs: {', '.join(TVS)}")
    if API_TOKEN:
        print("API auth: enabled")
    srv.serve_forever()

if __name__ == "__main__":
    main()