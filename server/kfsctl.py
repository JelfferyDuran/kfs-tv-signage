#!/usr/bin/env python3
"""
kfsctl.py — control the KFS kitchen displays from the command line.

Usage:
  python kfsctl.py status                          # show all TV scenes
  python kfsctl.py menu <menu.json> [tv]           # push a menu scene (default: all)
  python kfsctl.py image <file> [tv]               # show an image (default: all)
  python kfsctl.py video <file> [tv]               # play a video (default: all)
  python kfsctl.py url <http://...> [tv]           # show a web page
  python kfsctl.py blank [tv]                      # blank screen
  python kfsctl.py copy <file>...                  # copy content files to server

tv: menu1 | menu2 | menu3 | all (default all)
"""
import json, os, shutil, sys, urllib.request

SERVER = os.environ.get("KFS_SERVER", "http://10.1.10.238:8080")
CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
TVS = ("menu1", "menu2", "menu3", "all")

def post(payload):
    req = urllib.request.Request(SERVER + "/set", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())

def get(path):
    with urllib.request.urlopen(SERVER + path, timeout=5) as r:
        return json.loads(r.read().decode())

def split_tv(rest):
    """Return (tv, remaining_args). A tv name may be first or last arg."""
    if rest and rest[0] in TVS:
        return rest[0], rest[1:]
    if rest and rest[-1] in TVS:
        return rest[-1], rest[:-1]
    return "all", rest

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    c = sys.argv[1]
    rest = sys.argv[2:]

    if c == "status":
        data = get("/")
        for t, s in data["scenes"].items():
            print(f"{t:6} {s.get('type','?'):6} {s.get('src') or s.get('title') or ''}")
        print("content:", ", ".join(data["content"]) or "(empty)")

    elif c == "menu":
        tv, rest = split_tv(rest)
        path = rest[0] if rest else None
        if not path:
            print("need a menu json file"); return
        with open(path) as f:
            scene = json.load(f)
        scene.setdefault("type", "menu")
        print(post({"tv": tv, "scene": scene}))

    elif c in ("image", "video", "url", "blank"):
        tv, rest = split_tv(rest)
        if c == "blank":
            print(post({"tv": tv, "scene": {"type": "blank"}})); return
        src = rest[0] if rest else None
        if not src:
            print(f"need a {'file' if c in ('image','video') else 'url'}"); return
        if c in ("image", "video"):
            fname = os.path.basename(src)
            dst = os.path.join(CONTENT_DIR, fname)
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copyfile(src, dst)
                print(f"copied {fname} to server content dir")
            scene = {"type": c, "src": fname}
        else:
            scene = {"type": "url", "src": src}
        print(post({"tv": tv, "scene": scene}))

    elif c == "copy":
        for f in rest:
            shutil.copyfile(f, os.path.join(CONTENT_DIR, os.path.basename(f)))
            print(f"copied {os.path.basename(f)}")
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
