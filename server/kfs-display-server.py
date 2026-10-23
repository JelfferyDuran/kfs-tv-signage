#!/usr/bin/env python3
"""
kfs-display-server.py — control server for the KFS kitchen display TVs.

Serves:
  GET  /scene/<tv_id>          -> current scene JSON for that TV (polled by TVs)
  GET  /content/<file>         -> static content (images/videos)
  POST /set                    -> set a scene: {"tv":"all|menu1|...", "scene":{...}}
  GET  /                        -> tiny control page

Scene types: image, video, menu, url, blank
  image: {"type":"image","src":"file.jpg"}
  video: {"type":"video","src":"file.mp4","loop":true}
  menu:  {"type":"menu","title":"LUNCH","items":[{"name":"...","price":"$9.99"}],"footer":"..."}
  url:   {"type":"url","src":"http://..."}
  blank: {"type":"blank"}

Content files go in ./content/  (jpg, png, webp, mp4, webm)
"""
import json, mimetypes, os, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(ROOT, "content")
PORT = int(os.environ.get("KFS_PORT", "8080"))
TVS = ["menu1", "menu2", "menu3"]

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

# default scene per TV
scenes = {tv: {"type": "blank"} for tv in TVS}
lock = threading.Lock()

def set_scene(tv, scene):
    with lock:
        if tv == "all":
            for t in TVS: scenes[t] = scene
        elif tv in TVS:
            scenes[tv] = scene
        else:
            return False
    return True

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
            with lock:
                scene = scenes.get(tv)
            if scene is None:
                self._json(404, {"error": "unknown tv"})
            else:
                self._json(200, scene)
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
            self._json(200, {"tvs": TVS, "scenes": {t: scenes[t] for t in TVS},
                             "content": os.listdir(CONTENT_DIR) if os.path.isdir(CONTENT_DIR) else []})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/set":
            self._json(404, {"error": "not found"})
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
    srv.serve_forever()

if __name__ == "__main__":
    main()
