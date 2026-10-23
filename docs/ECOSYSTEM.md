# Ecosystem — building apps on the signage platform

The display server is a plain, CORS-enabled HTTP API. Any application can
push scenes to any device. This is the integration surface for the
commercial product: POS systems, order screens, video walls, schedulers,
and your other LLM agents.

## The contract

- **Devices poll** `GET /scene/<device-id>` every 3s and render the JSON.
- **Apps push** `POST /set` with `{"tv": "<id>|all", "scene": {...}}`.
- **Content** is served from `GET /content/<file>` (upload via `kfsctl.py copy`).
- **Discovery** is `GET /` (list of devices, scenes, content).

That's the whole platform. No SDK required — any HTTP client works.

## Integration patterns

### 1. POS / order system → menu updates

When a price or item changes, push the new menu:

```bash
curl -X POST http://<server>:8080/set \
  -H "Content-Type: application/json" \
  -d '{"tv":"all","scene":{"type":"menu","title":"LUNCH","items":[{"name":"Mangu","price":"$9.99"}]}}'
```

### 2. Promo / event scheduler

A cron job or scheduler pushes time-based scenes:

```bash
# 11:00 — lunch menu
curl -X POST http://<server>:8080/set -H "Content-Type: application/json" \
  -d '{"tv":"all","scene":{"type":"url","src":"menu-lunch.html"}}'
# 17:00 — dinner + video promo
curl -X POST http://<server>:8080/set -H "Content-Type: application/json" \
  -d '{"tv":"all","scene":{"type":"video","src":"dinner-promo.mp4","loop":true}}'
```

### 3. Other LLM agents

Your agents can drive the displays the same way they'd call any API:

```python
import urllib.request, json
req = urllib.request.Request(
    "http://10.1.10.238:8080/set",
    data=json.dumps({"tv": "menu1", "scene": {"type": "image", "src": "specials.webp"}}).encode(),
    headers={"Content-Type": "application/json"})
urllib.request.urlopen(req)
```

### 4. Web apps (browser-based control)

CORS is enabled (`Access-Control-Allow-Origin: *`), so a control dashboard
can run entirely in the browser:

```js
await fetch("http://<server>:8080/set", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({tv: "all", scene: {type: "blank"}})
});
```

### 5. Multi-site / multi-server

Each site runs its own server. A central dashboard can fan out to all of
them (each server is stateless-ish and exposes the same API).

## Content pipeline

1. Drop files into `server/content/` (or `python kfsctl.py copy file...`)
2. Reference them by filename in scenes
3. The server serves them at `/content/<file>` with correct MIME types

Optimization rules (from `docs/DEVICES.md`): WEBP ≤300KB, video ≤1.5MB,
total page ≤15MB. The repo ships a `menu-premium-webp.html` page and 20
optimized dish photos as a reference implementation.

## Roadmap hooks (see docs/UPGRADE.md)

Planned ecosystem features: API auth tokens, webhooks (scene-changed events),
playlists/scheduling server-side, a control dashboard, and a plugin system
for custom scene types. Contributions welcome — open an issue or PR.
