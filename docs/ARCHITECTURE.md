# Architecture

## The core idea

A **poll-based scene protocol**. Display devices don't receive pushes — they
poll the server every 3 seconds for their current scene and render whatever
comes back. This makes the system:

- **Fire-and-forget**: no websockets, no persistent connections, no NAT
  traversal. A device just needs HTTP GET.
- **Self-healing**: if the server restarts, devices reconnect on the next
  poll. If a device reboots, it resumes on the next poll.
- **Trivially scalable**: the server is stateless-ish (state is a dict +
  JSON file). Thousands of devices = thousands of tiny GETs.

## Components

```
┌──────────────┐   GET /scene/<id> (every 3s)   ┌─────────────────────┐
│  Display     │ ─────────────────────────────► │  kfs-display-server │
│  (player.html│ ◄───────────────────────────── │  :8080             │
│   or Tizen)  │   scene JSON / content files   │  scenes dict        │
└──────────────┘                                │  kfs-state.json     │
                                                └──────────┬──────────┘
                                                           ▲
                                    POST /set (kfsctl.py, curl, apps)
```

### Server (`server/kfs-display-server.py`)

- Stdlib Python `ThreadingHTTPServer` — zero dependencies
- `scenes` dict: `{device_id: scene_json}`, guarded by a lock
- `ensure_tv()` auto-registers unknown device IDs (ecosystem feature)
- `_save_state()` persists scenes + device list to `kfs-state.json`
- Single-instance guard: exits quietly if the port is already bound
- CORS `*` on all responses (browser apps can call the API)

### Clients

| Client | Where | Behavior |
|---|---|---|
| `player.html` | any browser | Polls, renders image/video/menu/url/blank, NO SIGNAL overlay |
| Tizen app | Samsung TVs | Same protocol, native fullscreen, `window.location.replace` for url scenes |

### Control

- `kfsctl.py` — CLI wrapper over `POST /set` + content copy
- `tvctl.py` — Samsung remote-API control (keys, launch, power) — separate
  from the scene protocol, used for TV management

## Scene lifecycle

1. Operator runs `kfsctl.py menu menu.json` (or any app POSTs `/set`)
2. Server stores the scene under the target device ID(s), persists to disk
3. Device's next poll (≤3s) returns the new scene
4. Device renders it; if unchanged, it skips re-render (client-side diff)

## State & persistence

- `kfs-state.json` holds `{"tvs": [...], "scenes": {...}}`
- Written on every scene change and device registration
- Loaded at startup — scenes survive server restarts
- Delete the file to reset everything

## Security model (current)

- **LAN-first**: binds `0.0.0.0`, no auth. Fine inside a trusted network.
- **Roadmap**: shared-secret token for `/set`, HTTPS, remote management via
  Tailscale/WireGuard (see `docs/UPGRADE.md`).

## Design decisions

| Decision | Why |
|---|---|
| Polling over push | Simplicity, self-healing, no persistent connections |
| Stdlib only | Zero install friction — `python kfs-display-server.py` and it runs |
| JSON scenes | Language-agnostic; any app can produce/consume them |
| Auto-registration | New devices join without config — the ecosystem hook |
| CORS `*` | Browser-based control dashboards work out of the box |
| WEBP content | 95% smaller than the original PNGs; TVs load over LAN |
