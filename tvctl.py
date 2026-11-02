#!/usr/bin/env python3
"""
tvctl.py — Samsung Tizen TV controller (Path A)
Controls the 3 menu TVs at the supermarket over the Tizen remote API.

Usage:
  python tvctl.py list                          # show TVs + power state
  python tvctl.py launch <tv> <appId>           # launch an app (e.g. YouTube)
  python tvctl.py key <tv> <KEY>                # send a remote key
  python tvctl.py power <tv> on|off             # power control
  python tvctl.py volume <tv> up|down|mute      # volume control
  python tvctl.py apps <tv>                     # list installed apps
  python tvctl.py youtube <tv> <videoId>        # open YouTube video
  python tvctl.py all <command>                 # run command on all TVs

TVs: menu1 (10.1.10.46), menu2 (10.1.10.91), menu3 (10.1.10.185)
First connection to each TV pops an "Allow" prompt on the TV — accept it once.
The pairing token is cached in .tv_tokens.json (gitignored).
Note: "power on" only works if the TV keeps its network up in standby
(Settings > General > Network > Expert Settings > Power On with Mobile).
Requires: pip install websocket-client
"""
import base64, json, os, ssl, sys, time, urllib.parse, urllib.request
import websocket

TVS = {
    "menu1": {"ip": "10.1.10.46", "name": "Menu TV 1"},
    "menu2": {"ip": "10.1.10.91", "name": "Menu TV 2"},
    "menu3": {"ip": "10.1.10.185", "name": "Menu TV 3"},
}
CLIENT_NAME = "HermesTV"
APP_IDS = {
    "youtube": "111299001912",
    "netflix": "11101200001",
    "prime": "3201512006785",
    "hulu": "11000000003",
    "settings": "org.tizen.setting",
}

TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tv_tokens.json")

def _load_tokens():
    try:
        with open(TOKEN_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_token(ip, token):
    tokens = _load_tokens()
    if token and tokens.get(ip) != token:
        tokens[ip] = token
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=1)

def _ws_url(ip):
    # Samsung expects the client name base64-encoded; the token returned on
    # first "Allow" is passed back so the TV doesn't prompt again.
    name = urllib.parse.quote(base64.b64encode(CLIENT_NAME.encode()).decode())
    url = f"wss://{ip}:8002/api/v2/channels/samsung.remote.control?name={name}"
    token = _load_tokens().get(ip)
    if token:
        url += f"&token={urllib.parse.quote(str(token))}"
    return url

def _connect(ip, timeout=30):
    ws = websocket.create_connection(
        _ws_url(ip), timeout=timeout, sslopt={"cert_reqs": ssl.CERT_NONE}
    )
    # The TV speaks first: ms.channel.connect (accepted, may carry a token)
    # or ms.channel.unauthorized (user denied / timed out on the TV prompt).
    # The old code sent a made-up "ctr" handshake and waited for a "welcome"
    # event the Samsung API never sends.
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = json.loads(ws.recv())
        ev = msg.get("event")
        if ev == "ms.channel.connect":
            _save_token(ip, (msg.get("data") or {}).get("token"))
            return ws
        if ev in ("ms.channel.unauthorized", "ms.channel.timeOut"):
            ws.close()
            raise RuntimeError(f"TV refused connection ({ev}) - accept the prompt on the TV")
    ws.close()
    raise RuntimeError("no ms.channel.connect from TV")

def _close(ws):
    time.sleep(0.3)  # give the TV a moment to act before the socket drops
    ws.close()

def _send_key(ws, key):
    ws.send(json.dumps({
        "method": "ms.remote.control",
        "params": {
            "Cmd": "Click", "DataOfCmd": key,
            "Option": "false", "TypeOfRemote": "SendRemoteKey",
        },
    }))

def _http(ip, path, timeout=5):
    req = urllib.request.Request(f"http://{ip}:8001{path}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def get_tv(key):
    if key not in TVS:
        sys.exit(f"Unknown TV '{key}'. Use: {', '.join(TVS)}")
    return TVS[key]

def cmd_list():
    for k, tv in TVS.items():
        try:
            d = _http(tv["ip"], "/api/v2/")["device"]
            state = d.get("PowerState", "?")
            print(f"{k:6} {tv['ip']:14} {tv['name']:12} power={state} model={d.get('modelName','?')}")
        except Exception as e:
            print(f"{k:6} {tv['ip']:14} {tv['name']:12} UNREACHABLE ({e})")

def cmd_launch(tv, appid):
    t = get_tv(tv)
    ws = _connect(t["ip"])
    ws.send(json.dumps({
        "method": "ms.channel.emit",
        "params": {"event": "ed.apps.launch", "to": "host",
                   "data": {"appId": appid, "action_type": "NATIVE_LAUNCH"}},
    }))
    _close(ws)
    print(f"launched {appid} on {t['name']}")

def cmd_key(tv, key):
    t = get_tv(tv)
    ws = _connect(t["ip"])
    _send_key(ws, key)
    _close(ws)
    print(f"sent {key} to {t['name']}")

def cmd_power(tv, state):
    t = get_tv(tv)
    ws = _connect(t["ip"])
    if state == "on":
        _send_key(ws, "KEY_POWERON")
    elif state == "off":
        _send_key(ws, "KEY_POWEROFF")
    else:
        _send_key(ws, "KEY_POWER")
    _close(ws)
    print(f"power {state} -> {t['name']}")

def cmd_volume(tv, action):
    t = get_tv(tv)
    ws = _connect(t["ip"])
    key = {"up": "KEY_VOLUP", "down": "KEY_VOLDOWN", "mute": "KEY_MUTE"}[action]
    _send_key(ws, key)
    _close(ws)
    print(f"volume {action} -> {t['name']}")

def cmd_apps(tv):
    t = get_tv(tv)
    try:
        data = _http(t["ip"], "/api/v2/applications")
        for app in data.get("data", []):
            print(f"{app.get('appId')}  {app.get('name','')}")
    except Exception as e:
        print(f"apps endpoint failed ({e}) — try 'launch' with a known appId")

def cmd_youtube(tv, video_id):
    t = get_tv(tv)
    ws = _connect(t["ip"])
    ws.send(json.dumps({
        "method": "ms.channel.emit",
        "params": {"event": "ed.apps.launch", "to": "host",
                   "data": {"appId": "111299001912", "action_type": "NATIVE_LAUNCH",
                            "isRemote": True, "data": f"v={video_id}"}},
    }))
    _close(ws)
    print(f"opened YouTube {video_id} on {t['name']}")

def cmd_all(args):
    # args = [command, *rest]; per-TV commands take the tv as 1st argument,
    # so build [command, tv, *rest]. (Old code built [tv, command, ...],
    # which matched no command and just printed help 3 times.)
    if args and args[0] == "list":
        cmd_list(); return
    for k in TVS:
        print(f"--- {k} ---")
        try:
            run([args[0], k] + args[1:])
        except SystemExit:
            pass
        except Exception as e:
            print(f"  FAILED: {e}")

def run(argv):
    if not argv:
        print(__doc__); return
    c = argv[0]
    if c == "list": cmd_list()
    elif c == "launch" and len(argv) >= 3:
        appid = APP_IDS.get(argv[2].lower(), argv[2])
        cmd_launch(argv[1], appid)
    elif c == "key" and len(argv) >= 3: cmd_key(argv[1], argv[2].upper())
    elif c == "power" and len(argv) >= 3: cmd_power(argv[1], argv[2].lower())
    elif c == "volume" and len(argv) >= 3 and argv[2].lower() in ("up", "down", "mute"):
        cmd_volume(argv[1], argv[2].lower())
    elif c == "apps" and len(argv) >= 2: cmd_apps(argv[1])
    elif c == "youtube" and len(argv) >= 3: cmd_youtube(argv[1], argv[2])
    elif c == "all" and len(argv) >= 2: cmd_all(argv[1:])
    else: print(__doc__)

if __name__ == "__main__":
    run(sys.argv[1:])
