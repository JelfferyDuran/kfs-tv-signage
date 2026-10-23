# API Reference

Base URL: `http://<server-ip>:8080` (configurable via `KFS_PORT`).

All responses are JSON. CORS is enabled (`Access-Control-Allow-Origin: *`).

## GET /

Discovery + status. Lists registered devices, their current scenes, and
content files.

```json
{
  "tvs": ["menu1", "menu2", "menu3"],
  "device_names": {"menu1": "Kitchen 1"},
  "scenes": {"menu1": {"type": "url", "src": "menu-premium-webp.html"}},
  "content": ["mangu.webp", "player.html", "..."]
}
```

## GET /scene/<device-id>

The scene for one device. This is what display clients poll every 3s.

```json
{"type": "url", "src": "menu-premium-webp.html"}
```

- Unknown device IDs are **auto-registered** (unless `KFS_AUTOREGISTER=0`)
- Returns `404 {"error": "unknown tv"}` only when auto-registration is off

## POST /set

Set a scene on one device or all devices.

Request body:
```json
{
  "tv": "all",            // "all" | "*" | "menu1" | any device id
  "scene": {"type": "image", "src": "mangu.webp"}
}
```

Response:
```json
{"ok": true, "tv": "all", "scene": {"type": "image", "src": "mangu.webp"}}
```

Errors: `400 {"error": "bad json"}` · `400 {"error": "scene needs a type"}` ·
`400 {"error": "unknown tv"}` (auto-registration off).

## GET /content/<file>

Static content (images, videos, HTML pages). Served with the correct MIME
type. `404 {"error": "not found"}` if missing.

## Scene types

| Type | Fields | Renders |
|---|---|---|
| `image` | `src` (file in content/) | Fullscreen image |
| `video` | `src`, `loop` (bool, default true) | Muted autoplay looping video |
| `menu` | `title`, `items[]` (`name`, `price`), `footer` | Styled menu card |
| `url` | `src` (http(s) URL or content/ file) | Full web page |
| `blank` | — | Blank screen |

### Menu example

```json
{
  "type": "menu",
  "title": "LUNCH",
  "items": [
    {"name": "Mangu con Los Tres Golpes", "price": "$12.99"},
    {"name": "Yaroa", "price": "$11.99"}
  ],
  "footer": "Catering available — call (201) 555-0199"
}
```

## CLI (kfsctl.py)

| Command | Effect |
|---|---|
| `python kfsctl.py status` | Show all device scenes + content |
| `python kfsctl.py menu <file.json> [tv]` | Push a menu scene |
| `python kfsctl.py image <file> [tv]` | Copy + show an image |
| `python kfsctl.py video <file> [tv]` | Copy + play a video |
| `python kfsctl.py url <url-or-page> [tv]` | Show a web page |
| `python kfsctl.py blank [tv]` | Blank a device |
| `python kfsctl.py copy <file>...` | Upload content files |

`tv` defaults to `all`. Override the server with `KFS_SERVER` env var.

## State persistence

Scenes and registered devices persist to `server/kfs-state.json` and are
reloaded on restart. Delete the file to reset.

## Environment variables

| Var | Default | Meaning |
|---|---|---|
| `KFS_PORT` | `8080` | Listen port |
| `KFS_TVS` | `menu1,menu2,menu3` | Initial device IDs |
| `KFS_DEVICE_NAMES` | *(empty)* | `menu1=Kitchen 1,menu2=Kitchen 2` |
| `KFS_AUTOREGISTER` | `1` | `0` disables auto-registration |
