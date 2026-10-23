#!/usr/bin/env python3
"""
kfsctl.py — control the KFS kitchen displays from the command line.

Usage:
  python kfsctl.py status                          # show all TV scenes
  python kfsctl.py menu <menu.json> [tv]           # push a menu scene (default: all)
  python kfsctl.py image <file> [tv]               # show an image (default: all)
  python kfsctl.py video <file> [tv]               # play a video (default: all)
  python kfsctl.py url <http://...> [tv]           # show a web page
  python kfsctl.py blank [tv]                       # blank screen
   python kfsctl.py playlist <interval> <file|url>... # rotate scenes (default: all)
  python kfsctl.py copy <file>...                  # copy content files to server

tv: menu1 | menu2 | menu3 | all (default all)
"""
import json, os, shutil, sys, urllib.request

SERVER = os.environ.get("KFS_SERVER", "http://10.1.10.238:8080")
CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
TVS = ("menu1", "menu2", "menu3", "all")

def post(payload):
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("KFS_API_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(SERVER + "/set", data=json.dumps(payload).encode(),
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

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

    elif c == "playlist":
        tv, rest = split_tv(rest)
        # usage: playlist <interval> <file1> <file2> ...  OR  playlist <interval> url1 url2 ...
        if len(rest) < 2:
            print("need: interval + at least one item (image/video file or http url)")
            return
        interval = rest[0]
        items = []
        for it in rest[1:]:
            if it.startswith("http://") or it.startswith("https://"):
                items.append({"type": "url", "src": it})
            else:
                fname = os.path.basename(it)
                dst = os.path.join(CONTENT_DIR, fname)
                if os.path.abspath(it) == os.path.abspath(dst):
                    pass  # already in content dir
                elif os.path.isfile(it):
                    shutil.copyfile(it, dst)
                    print(f"copied {fname} to server content dir")
                elif os.path.isfile(dst):
                    print(f"{fname} already in server content dir")
                else:
                    print(f"WARNING: {it} not found (cwd or content dir)"); continue
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                items.append({"type": "video" if ext in ("mp4", "webm", "mov", "mkv") else "image", "src": fname})
        scene = {"type": "playlist", "items": items, "interval": int(interval)}
        print(post({"tv": tv, "scene": scene}))

    elif c == "copy":
        for f in rest:
            shutil.copyfile(f, os.path.join(CONTENT_DIR, os.path.basename(f)))
            print(f"copied {os.path.basename(f)}")
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
