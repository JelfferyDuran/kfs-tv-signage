# Media Update Workflow

How to update menu content on the 3 kitchen displays (menu1/menu2/menu3) —
for humans and AI agents (ChatGPT, etc.).

## TL;DR

1. Put the new image in `server/content/` (webp preferred, ~1920x1080)
2. Push it to the TVs:
   ```bash
   cd C:/Users/Jayto/tvctl/server
   KFS_API_TOKEN=$(cat .api_token) python kfsctl.py image <file> all
   ```
3. Or point the TVs at a full menu page:
   ```bash
   KFS_API_TOKEN=$(cat .api_token) python kfsctl.py url menu-premium-webp.html all
   ```

## The one-time cert rule

**Certificates are ONE-TIME per TV, never per media change.** The DUID-bound
Samsung certs exist only to INSTALL the app. After install, every
menu/image/video/playlist change is a server push — zero certs, zero TV
visits, zero reinstalls. 3 TVs = 3 certs total, then content is free.

## Commands (kfsctl.py)

| Command | What it does |
|---|---|
| `status` | Show all TV scenes |
| `menu <menu.json> [tv]` | Push a menu scene (default: all) |
| `image <file> [tv]` | Show an image (default: all) |
| `video <file> [tv]` | Play a video (default: all) |
| `url <http://...> [tv]` | Show a web page |
| `blank [tv]` | Blank screen |
| `playlist <interval> <file\|url>...` | Rotate scenes (default: all) |
| `copy <file>...` | Copy content files to server |

`tv` is `menu1 | menu2 | menu3 | all` (default `all`).

## Auth

The server requires a bearer token for `POST /set`:

```bash
KFS_API_TOKEN=$(cat .api_token) python kfsctl.py <command>
```

The token lives in `server/.api_token` (gitignored). The Startup launcher
`server/start-server.cmd` loads it on boot. If you get a 401, the token file
is missing or the server was started without it — restart via the launcher.

## Content files

- `server/content/` holds images (`.webp` preferred), videos, and HTML pages
- `menu-premium-webp.html` is the current full menu page
- The app polls `GET /scene/<tv>` every 3s; a `url` scene hands off to the
  page (the app stops polling — that's success, not failure)

## Server

- Runs as `kfs-display-server.py` on port 8080
- Auto-starts on boot via Startup shortcut → `start-server.cmd`
- State persists in `server/kfs-state.json` (delete to reset)
- TVs: menu1=10.1.10.46, menu2=10.1.10.91, menu3=10.1.10.185


## Premium page and Tizen-safe motion

The two premium HTML variants are self-contained and use local WEBP assets.
`menu-premium-webp.html` and `menu-premium.html` both use optimized WEBP so the
Tizen fallback page does not load the original multi-megabyte PNGs. The
Picadera strip now uses a meat platter with fried yuca and plantain sides.

Motion details and per-asset video specs are in
[`PREMIUM-MOTION-SPECS.md`](./PREMIUM-MOTION-SPECS.md). The page has no runtime
dependency on the supermarket site or internet; scene polling behavior is
unchanged.
