# Devices — every way to run a display

The signage system is device-agnostic. Any device that can poll an HTTP URL
and render HTML can be a display. Two client implementations exist:

1. **`player.html`** — universal web player (any browser, any OS)
2. **Tizen app** — native Samsung TV app (fullscreen, no browser chrome)

Both speak the same `/scene/<id>` protocol, so you can mix device types in
one deployment and control them all from the same server.

---

## 1. Universal web player (`player.html`) — recommended for most devices

Served by the display server at:

```
http://<server-ip>:8080/content/player.html?tv=<device-id>
```

- `tv` — device ID (defaults to `menu1`). Use any string: `bar-tv`,
  `drive-thru`, `lobby`, `tablet-1`…
- `server` — optional, overrides the server host (defaults to the page's host)

The player renders all scene types: image, video, menu, url, blank. It shows
a "NO SIGNAL" overlay when the server is unreachable and self-heals when the
server returns.

### Where to run it

| Device | How |
|---|---|
| **Laptop / desktop** | Open in Chrome/Edge/Firefox, F11 fullscreen |
| **Tablet (iPad/Android)** | Open in browser, enable Guided Access / kiosk mode |
| **Phone** | Same — useful for a test display or a portable menu |
| **Fire TV / Fire Stick** | Silk browser → open the URL, fullscreen |
| **Android TV / Google TV** | Any browser app (e.g. TV Bro) → open URL |
| **Raspberry Pi** | `chromium-browser --kiosk "http://<ip>:8080/content/player.html?tv=pi1"` |
| **Windows kiosk** | Edge `--kiosk` or a shell-replacement kiosk app |
| **Chromecast / Cast devices** | Cast the tab, or use a Cast web receiver pointing at the URL |

### Kiosk quick commands

Raspberry Pi (Raspberry Pi OS):
```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars \
  "http://10.1.10.238:8080/content/player.html?tv=pi1"
```

Windows (Edge):
```powershell
msedge --kiosk "http://10.1.10.238:8080/content/player.html?tv=win1" --edge-kiosk-type=fullscreen
```

---

## 2. Samsung Tizen TV — native app

Fullscreen native app, no browser chrome, survives TV reboots (relaunch on
boot if configured). This is the route used for the 3 supermarket TVs.

### One-time TV setup (per TV, ~5 min, at the TV)

1. **Smart Hub → Apps → App Settings** (gear icon, top right)
2. Enter code **`12345`** on the number pad
3. Toggle **Developer mode ON**, enter the server PC's IP, OK
4. **Reboot the TV** when prompted
5. After reboot, "Develop Mode" shows at the top of the Apps panel

### PC-side toolchain (one-time)

1. Install **Tizen Studio** (Web IDE + TV Extension, or CLI tools)
2. Create a certificate profile in **Tools → Certificate Manager**
   - For retail TVs: create a **Samsung → TV** profile (requires a Samsung
     Developer account) and add **each TV's DUID** (TV: Menu → Support →
     Contact Samsung → Unique Device ID)
   - The generic Tizen public signer is rejected by newer retail TVs
     (install error 118,-12)
3. Build + install:
   ```bash
   cd scripts
   ./build-install.sh            # builds wgt, installs on all TVs
   ./build-install.sh 10.1.10.46 # just one TV
   ```
   Set `PROFILE` in the script to your certificate profile name.

### Per-TV device ID

The app's `TV_ID` is set in `tizen-app/app.js` (`var TV_ID = "menu1"`).
Build a variant per TV if you want per-TV scenes; the server keys scenes by
device ID. The server auto-registers any ID it sees, so a new TV just works.

---

## 3. Auto-registration

The server adopts any device ID that polls it (unless `KFS_AUTOREGISTER=0`).
So you can:

- Add a new TV: just point it at the server with a new ID — it appears in
  `kfsctl.py status` and `GET /` automatically
- Rename a device: change the `tv` param in the player URL / app build
- Give devices friendly names: `KFS_DEVICE_NAMES="menu1=Kitchen 1,bar-tv=Bar"`

Registered devices and their scenes persist in `server/kfs-state.json`.

---

## 4. Device matrix

| Device | Client | Fullscreen | Autostart | Notes |
|---|---|---|---|---|
| Samsung Tizen TV | native app | ✅ | ✅ (on boot) | Best for permanent walls |
| Any browser | player.html | ✅ (F11/kiosk) | via OS | Fastest to deploy |
| Raspberry Pi | player.html + chromium | ✅ | ✅ (autostart) | Cheap dedicated displays |
| Fire TV | Silk browser | ✅ | partial | Good for secondary screens |
| Android TV | browser app | ✅ | partial | |
| Tablet / phone | player.html | ✅ (kiosk mode) | partial | Portable menus |
| Windows PC | player.html + Edge kiosk | ✅ | ✅ (Task Scheduler) | |

---

## 5. Content sizing guidance

- **Images**: WEBP/JPG, max 1280px long edge, ≤300KB (the repo's dish photos
  are already optimized: 1.7MB total for 20 dishes)
- **Video**: WEBM (VP9) or MP4 (H.264), 1280x720, ≤1.5MB, muted autoplay loop
- **Pages**: keep total page weight ≤15MB; TVs load over LAN every 3s
- TVs are 1080p; design for 1920x1080 with safe margins
