# Premium menu motion and asset handoff

The optional premium page remains a single local HTML file served by the KFS
LAN server. It does not fetch fonts, libraries, menu data, or media from the
internet. Motion is implemented with CSS transforms and opacity; no canvas,
backdrop blur, or video is required for the page to render.

## Implemented in the premium pages

- Entrance: menu cards rise 16px and fade in over 800ms, staggered by 200ms.
- Header mark: gold sweep repeats every 5s; header divider sweep every 7s.
- Card glow: a static radial gradient fades gently over 8s. No animated blur.
- Heading underline: draws across over 650ms on page load.
- Prices: 600ms scale/opacity entrance with one brief gold highlight.
- Dish photos: a slow 12s alternating scale/pan cycle, clipped to the image strip.
- Catering badge: low contrast opacity pulse every 4.8s.
- Embers: 18 fixed-position 2–3px motes rise and fade over 8–16s loops.
- Reduced motion: `prefers-reduced-motion` disables animation and leaves all
  content fully visible.

The page deliberately avoids `backdrop-filter` and continuously animated
box-shadow/filter effects. Tizen 5.5 rendering quality varies by firmware, so
verify the installed page on the actual TU7000 TVs before enabling additional
motion.

## Video motion specs (not included)

The repository has no generated dish videos or hero background video yet. No
video files are referenced by the menu page, so playback support is not a
runtime dependency.

| Asset | Duration / format target | Camera / motion | Loop point |
|---|---|---|---|
| Mangu | 5s, 1280x720, H.264 MP4, ≤1.5MB | 3% slow push-in; subtle steam only | Match first/last frame framing and steam opacity; no new garnish |
| Yaroa | 5s, 1280x720, H.264 MP4, ≤1.5MB | 3% push-in toward cheese and meat | Return to original crop; no visible sauce reset |
| Mofongo | 5s, 1280x720, H.264 MP4, ≤1.5MB | 2% lateral slide across bowl | Ease to center and match first frame |
| Chimi | 5s, 1280x720, H.264 MP4, ≤1.5MB | 3% diagonal push toward sandwich cut | Match start/end crop; no bite or ingredient changes |
| Cheesesteak | 5s, 1280x720, H.264 MP4, ≤1.5MB | 3% push-in across steak and melted cheese | Match start/end crop and lighting |
| Pica pollo | 5s, 1280x720, H.264 MP4, ≤1.5MB | 2% slow pan across crispy chicken | Match start/end crop; no chicken movement |
| Batidas | 5s, 1280x720, H.264 MP4, ≤1.5MB | 2% lateral camera drift across drinks | Match start/end crop; no liquid morphing |
| Picadera | 5s, 1280x720, H.264 MP4, ≤1.5MB | 2% push-in across mixed meat and fried sides | Match first/last crop; no food appearing/disappearing |
| Hero background | 8s, 1920x1080, H.264 MP4, ≤3MB | Locked camera; 12–16 low-contrast embers drift | Seamless particle positions; no streak crossing text-safe center |
| Logo shimmer | 4s, transparent WebM with alpha if supported | Static mark; one gold sweep + glow pulse | Exact same mark and brightness at start/end |

No text or pricing should be baked into video. The H.264 MP4 target is the
compatibility fallback; validate muted autoplay/loop on each TV model before
shipping a video scene.

## Source data connection status

`anthony-supermarket/apps/menu/scripts/anthonys-seed.json` and
`anthony-supermarket/apps/superkitchen/src/data/menu.json` are separate menu
sources with different scopes and conflicting prices (for example, Mofongo is
$15.95 in the seed and $14.95 in the ordering app). The premium page also had
placeholder contact data before this update. The signage page therefore stays
LAN-local and static until the owner chooses the authoritative menu source and
confirms the display set. This keeps the current Tizen scene protocol and its
offline behavior unchanged.

Current repo-derived contact: 288 Kearny Ave, Kearny NJ 07032 · (201) 428-1745.
The page uses a catering badge instead of publishing unverified business hours.
