# APR EVSE — Home Assistant integration


Local-push HACS custom integration for the APR EVSE smart charger. Talks to the device over its LAN HTTP + WebSocket API. No cloud.

## Install (HACS)

[![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=apreb&repository=mb-homeassistant&category=integration)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo (category: Integration).
2. Install **APR EVSE**, restart Home Assistant.
3. The charger is auto-discovered via zeroconf, or add it manually: Settings → Devices & Services → Add Integration → APR EVSE → host/IP.

## Behaviour

- Snapshot via `GET /api/state` (REST); live deltas via `/ws`. The WS on-connect push is truncated by firmware, so REST is always the source of truth.
- `state.car` / `state.pw` / `state.charge` are conditional: their entities go `unavailable` when the device omits the section.

## Dashboard

Example: [`examples/dashboard.yaml`](examples/dashboard.yaml). Conditional sections (car / powerwall / PV) auto-hide where the data isn't reported. Change device name `apr_evse` to your own, you can find device slug here: Settings → Devices & Services → APR EVSE → click the device → click any entity → the entity ID is shown 

## Options

- **Poll fallback interval** (default 30 s) — REST poll used when the WebSocket is down; also clears stale conditional sections.


