# KFS Kitchen Display System

Controls the 3 Samsung TU7000 menu TVs at the supermarket.

## Architecture

```
┌─────────────────┐   poll /scene/<tv>    ┌──────────────────┐
│ TV app (Tizen)  │ ◄──────────────────── │ kfs-display-server│
│ fullscreen      │   /content/<file>    │ :8080 (this PC)  │
│ renderer        │                      └──────────────────┘
└─────────────────┘                             ▲
                                          kfsctl.py / curl
                                          (you, from anywhere)
```

- **TV app** (`tizen-app/`): Tizen web app installed on each TV. Polls the server
  every 3s for its scene, renders image/video/menu/url fullscreen.
- **Server** (`server/kfs-display-server.py`): holds the current scene per TV,
  serves content files. Runs on this PC (10.1.10.238:8080).
- **Control** (`server/kfsctl.py`): push scenes from CLI.

## Path A — Remote control (works today)

1. On each TV accept the **"Allow"** popup (one-time grant).
2. `python tvctl.py list` → all 3 show power=on.
3. Control: `python tvctl.py launch menu1 youtube`, `key`, `power`, `volume`.

## Path B — Custom signage app (the real goal)

Install our own app on the TVs that can display anything we push.

### Tomorrow at work — TV side (5 min per TV)

1. On each TV: **Smart Hub → Apps → App Settings** (gear icon, top right).
2. Enter code **`12345`** on the number pad.
3. Toggle **Developer mode ON**, enter this PC's IP: **`10.1.10.238`**, OK.
4. **Reboot the TV** when prompted.
5. After reboot, "Develop Mode" shows at top of Apps panel. Repeat for all 3 TVs.

### PC side — one-time toolchain (already downloading)

1. Install `tizen-studio-setup.exe` (in `C:\Users\Jayto\tvctl\`).
   - During install, select **Web IDE** + **TV Extension** (or CLI tools only).
2. Create a certificate profile:
   - Tizen Studio → **Tools → Certificate Manager → New** → "Tizen" profile.
   - Name it `KFS`. (No Samsung account needed for the Tizen distributor cert.)
3. Build + install:
   ```
   cd C:\Users\Jayto\tvctl\scripts
   ./build-install.sh            # builds wgt, installs on all 3 TVs
   ```
   (Edit `PROFILE` in the script if your cert profile has a different name.)

### After install — control the displays

```
cd C:\Users\Jayto\tvctl\server
python kfs-display-server.py &          # start server (or autostart it)
python kfsctl.py status                 # what each TV shows
python kfsctl.py menu menu.json         # push menu to all TVs
python kfsctl.py image photo.jpg menu2   # image to one TV
python kfsctl.py video promo.mp4        # video to all
python kfsctl.py blank menu3            # blank one TV
```

Content files (jpg/png/webp/mp4/webm) go in `server/content/` — `kfsctl.py`
auto-copies them. Menu JSON: `{"type":"menu","title":"...","items":[{"name":"...","price":"$..."}]}`.

## TV map

| Alias | IP | Model |
|---|---|---|
| menu1 | 10.1.10.46 | UN43TU7000FXZA |
| menu2 | 10.1.10.91 | UN43TU7000FXZA |
| menu3 | 10.1.10.185 | UN43TU7000FXZA |

## Notes

- Path A (remote API) works on retail firmware with zero install. Path B needs
  Developer Mode + signed wgt — that's the OS-level route.
- The TV app's `TV_ID` (menu1/2/3) is set in `tizen-app/app.js` — build a variant
  per TV if you want per-TV scenes; the server keys scenes by TV id.
- Server binds 0.0.0.0:8080 — reachable from any device on the LAN.
