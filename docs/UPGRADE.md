# Upgrade Roadmap — from working signage to commercial product

Current state: a working, LAN-first signage system (server + Tizen app +
universal web player + optimized content). This doc is the path to a
commercial product with an ecosystem.

## Phase 0 — Ship what works (done)

- ✅ Server with scene protocol, auto-registration, state persistence
- ✅ Universal web player (`player.html`) — any device with a browser
- ✅ Native Tizen app for Samsung TVs
- ✅ Optimized media (WEBP, 95% smaller)
- ✅ Public repo: `JelfferyDuran/kfs-tv-signage`

## Phase 1 — Product hardening (next)

| Item | Why | Effort |
|---|---|---|
| **API auth tokens** | Anyone on the LAN can currently push scenes. Add a shared-secret token for `/set` (read stays open for devices). | ✅ Done — `KFS_API_TOKEN` |
| **Playlists / scheduling** | Server-side rotation: `{"playlist": [scene1, scene2], "interval": 15}`. The killer feature for signage. | ✅ Done — `playlist` scene type |
| **Webhooks** | Notify apps when a scene changes / device goes offline (heartbeat tracking). | Medium |
| **Device heartbeat** | Track last-poll time per device; expose in `GET /`; alert on stale devices. | Small |
| **Control dashboard** | A single HTML page (served by the server) to manage devices, push scenes, upload content. | Medium |
| **HTTPS** | Self-signed cert or reverse proxy for remote management. | Small |
| **Docker** | `Dockerfile` + `docker-compose` for one-command deploys. | Small |

## Phase 2 — Ecosystem (commercial)

| Item | Why | Effort |
|---|---|---|
| **Plugin scene types** | Custom renderers (ticker, clock, weather, QR, social feed) registered server-side. | Medium |
| **Content API** | Upload/delete content via API (not just `kfsctl.py copy`). | Small |
| **Multi-site management** | One dashboard over many site servers. | Medium |
| **Remote management** | Tailscale/WireGuard + HTTPS + auth = manage any client's TVs from anywhere. | Medium |
| **Billing / licensing** | Per-site license keys, or SaaS tier. | Medium |
| **Analytics** | Impressions, uptime, content performance. | Medium |

## Phase 3 — Premium content (design)

The repo ships a reference menu page (`menu-premium-webp.html`, dark green +
gold). For a commercial offering, generate a full premium design system:

- **Design**: display serif headers + clean sans items, emerald/gold palette,
  glassmorphism cards, refined price treatment
- **Motion**: staggered fade-up entrances, ambient gold particles (canvas,
  ≤20 elements), Ken Burns on photos, animated gold underlines — all
  GPU-friendly (transform/opacity only), with `prefers-reduced-motion`
- **Video**: 4–6s seamless-loop dish videos (WEBM/MP4, 1280x720, ≤1.5MB),
  hero background loop (≤3MB), logo shimmer
- **Constraints**: Tizen 5.5 webview — no backdrop-filter assumptions, no
  heavy JS libs, total page ≤15MB

Use the `menu-signage-design` skill (Hermes) to regenerate the full
ChatGPT prompt for any client's brand.

## Suggested first PRs (good for other LLM agents)

1. **Webhooks** — notify apps when a scene changes / device goes offline
2. **Heartbeat** — track `last_seen` per device, expose in `GET /`
3. **Dashboard** — single-file HTML control panel served at `/admin`
4. **Docker** — containerize the server

Each is self-contained, testable with `curl`, and doesn't break the scene
protocol. Playlists and API auth are already shipped.
