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
  python kfsctl.py playlist <interval> <file|url>... [--tv <tv>]  # rotate scenes
  python kfsctl.py copy <file>...                  # copy content files to server

tv: menu1 | menu2 | menu3 | all | any registered device id (default all)
    For playlist, a non-menuN device id must be given with --tv <id>.
Note: image/video/copy write into the local server/content dir, so run them
on the machine that hosts the server.
"""
import json, os, shutil, sys, urllib.error, urllib.request

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
    try:
        with urllib.request.urlopen(SERVER + path, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        sys.exit(f"cannot reach server {SERVER}: {e}  (set KFS_SERVER?)")

def split_tv(rest, nargs=None):
    """Return (tv, remaining_args).

    --tv <id> always wins. Otherwise a known name may be first or last arg.
    If the command takes a fixed number of args (nargs), one extra trailing
    arg is the tv id, so custom device ids work too. Previously an unknown id
    was silently ignored and the scene went to ALL screens.
    """
    rest = list(rest)
    if "--tv" in rest:
        i = rest.index("--tv")
        if i + 1 >= len(rest):
            sys.exit("--tv needs a device id")
        tv = rest[i + 1]
        return tv, rest[:i] + rest[i + 2:]
    if rest and rest[0] in TVS:
        return rest[0], rest[1:]
    if rest and rest[-1] in TVS:
        return rest[-1], rest[:-1]
    if nargs is not None and len(rest) == nargs + 1:
        return rest[-1], rest[:-1]
    if nargs is not None and len(rest) > nargs + 1:
        sys.exit(f"too many arguments: {' '.join(rest)}")
    return "all", rest

def stage_file(src):
    """Make sure src is in the content dir; return its basename or None."""
    fname = os.path.basename(src)
    dst = os.path.join(CONTENT_DIR, fname)
    if os.path.abspath(src) == os.path.abspath(dst):
        return fname if os.path.isfile(dst) else None
    if os.path.isfile(src):
        shutil.copyfile(src, dst)
        print(f"copied {fname} to server content dir")
        return fname
    if os.path.isfile(dst):
        print(f"{fname} already in server content dir")
        return fname
    print(f"ERROR: {src} not found (cwd or content dir)")
    return None

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    c = sys.argv[1]
    rest = sys.argv[2:]

    if c == "status":
        data = get("/")
        for t, s in data["scenes"].items():
            if s.get("type") == "playlist":
                desc = f"{len(s.get('items', []))} items / {s.get('interval', 15)}s: " + \
                       ", ".join(i.get("src") or i.get("type", "?") for i in s.get("items", []))
            else:
                desc = s.get("src") or s.get("title") or ""
            print(f"{t:6} {s.get('type','?'):8} {desc}")
        print("content:", ", ".join(data["content"]) or "(empty)")

    elif c == "menu":
        tv, rest = split_tv(rest, nargs=1)
        path = rest[0] if rest else None
        if not path:
            print("need a menu json file"); return
        with open(path, encoding="utf-8-sig") as f:
            scene = json.load(f)
        scene.setdefault("type", "menu")
        print(post({"tv": tv, "scene": scene}))

    elif c in ("image", "video", "url", "blank"):
        tv, rest = split_tv(rest, nargs=0 if c == "blank" else 1)
        if c == "blank":
            print(post({"tv": tv, "scene": {"type": "blank"}})); return
        src = rest[0] if rest else None
        if not src:
            print(f"need a {'file' if c in ('image','video') else 'url'}"); return
        if c in ("image", "video"):
            fname = stage_file(src)
            if not fname:
                sys.exit(1)
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
        try:
            interval = float(rest[0])
            if interval <= 0:
                raise ValueError
        except ValueError:
            sys.exit(f"interval must be a positive number of seconds, got {rest[0]!r}")
        items = []
        for it in rest[1:]:
            if it.startswith("http://") or it.startswith("https://"):
                items.append({"type": "url", "src": it})
            else:
                fname = stage_file(it)
                if not fname:
                    continue
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                kind = ("video" if ext in ("mp4", "webm", "mov", "mkv")
                        else "url" if ext in ("html", "htm") else "image")
                items.append({"type": kind, "src": fname})
        if not items:
            sys.exit("no playable items - nothing sent")
        scene = {"type": "playlist", "items": items, "interval": interval}
        print(post({"tv": tv, "scene": scene}))

    elif c == "copy":
        for f in rest:
            shutil.copyfile(f, os.path.join(CONTENT_DIR, os.path.basename(f)))
            print(f"copied {os.path.basename(f)}")
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
