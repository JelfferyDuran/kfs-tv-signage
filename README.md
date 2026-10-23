# KFS Signage — Restaurant Menu Display System

Turn any TV, tablet, or browser into a managed menu display. A tiny Python
server holds a "scene" per device; each device polls every 3s and renders
whatever you push — image, video, menu, or full web page.

Built for **Anthony's Supermarket, Kearny NJ** (Dominican/Latin menu) and
designed to be a reusable commercial product: multi-device, LAN-first,
zero-dependency server, ecosystem-ready.

```
┌────────────────────┐   poll /scene/<device>    ┌──────────────────────┐
│ Display device     │ ◄─────────────────────── │ kfs-display-server   │
│ (Tizen app OR      │   /content/<file>         │ :8080 (any machine)  │
│  player.html)      │                           └──────────────────────┘
└────────────────────┘                                    ▲
                                                   kfsctl.py / curl / API
                                                   (you, from anywhere)
```

## Quick start (5 minutes)

### 1. Clone

```bash
git clone https://github.com/JelfferyDuran/kfs-tv-signage.git
cd kfs-tv-signage
```

### 2. Run the server

Requires Python 3.8+ (stdlib only — no pip install needed).

```bash
cd server
python kfs-display-server.py
# → KFS display server on :8080
```

### 3. Point a device at it

**Any browser** (laptop, tablet, phone, Fire TV, Android TV, Raspberry Pi):

```
http://<server-ip>:8080/content/player.html?tv=menu1
```

**Samsung Tizen TV** (native app, fullscreen, no browser chrome):
see [docs/DEVICES.md](docs/DEVICES.md) for the install path.

### 4. Push content

```bash
cd server
python kfsctl.py status                          # what each device shows
python kfsctl.py menu menu.json                  # menu to all devices
python kfsctl.py image promo.jpg menu2           # image to one device
python kfsctl.py video promo.mp4                 # video to all
python kfsctl.py url menu-premium-webp.html      # full web page
python kfsctl.py blank menu3                     # blank one device
```

That's it. The device picks up the change within 3 seconds.

## What's in the repo

| Path | What it is |
|---|---|
| `server/kfs-display-server.py` | The control server (stdlib Python, ~170 lines) |
| `server/kfsctl.py` | CLI to push scenes / copy content |
| `server/content/` | Menu pages + optimized WEBP dish photos (1.7MB total) |
| `server/content/player.html` | **Universal web player** — any device with a browser |
| `tizen-app/` | Native Samsung Tizen app (config.xml + app.js) |
| `tvctl.py` | Samsung remote-API control (keys, launch, power) |
| `scripts/build-install.sh` | Build + install the Tizen app on TVs |
| `docs/` | Architecture, API, devices, ecosystem, upgrade roadmap |

## Scene protocol (the whole idea)

Every device polls `GET /scene/<device-id>` every 3s. The server answers with
one JSON scene. Scene types:

```json
{"type": "image", "src": "mangu.webp"}
{"type": "video", "src": "promo.mp4", "loop": true}
{"type": "menu",  "title": "LUNCH", "items": [{"name": "Mangu", "price": "$9.99"}], "footer": "Catering available"}
{"type": "url",   "src": "menu-premium-webp.html"}
{"type": "blank"}
```

Set a scene: `POST /set` with `{"tv": "all|menu1|...", "scene": {...}}`.
Full API: [docs/API.md](docs/API.md).

## Devices

- **Samsung Tizen TVs** — native app (fullscreen, autostart-friendly)
- **Any browser** — `player.html` (Fire TV Silk, Android TV, tablets, phones, PCs)
- **Raspberry Pi / kiosk** — chromium in kiosk mode pointing at `player.html`
- **New devices auto-register** — poll with any ID and the server adopts it

Setup per device: [docs/DEVICES.md](docs/DEVICES.md).

## Ecosystem

The server is a plain HTTP API with CORS enabled — any app can push scenes:
POS systems, order screens, video walls, digital signage schedulers, your
other LLM agents. See [docs/ECOSYSTEM.md](docs/ECOSYSTEM.md) for patterns
and [docs/UPGRADE.md](docs/UPGRADE.md) for the product roadmap.

## Configuration (env vars)

| Var | Default | Meaning |
|---|---|---|
| `KFS_PORT` | `8080` | Server port |
| `KFS_TVS` | `menu1,menu2,menu3` | Known device IDs |
| `KFS_DEVICE_NAMES` | *(empty)* | Friendly names: `menu1=Kitchen 1,menu2=Kitchen 2` |
| `KFS_AUTOREGISTER` | `1` | `0` disables auto-registration of new device IDs |

State (scenes + registered devices) persists to `server/kfs-state.json`
across restarts.

## TV map (Anthony's Supermarket)

| Alias | IP | Model |
|---|---|---|
| menu1 | 10.1.10.46 | UN43TU7000FXZA |
| menu2 | 10.1.10.91 | UN43TU7000FXZA |
| menu3 | 10.1.10.185 | UN43TU7000FXZA |

## License

Proprietary — all rights reserved. Contact the owner for commercial use.
