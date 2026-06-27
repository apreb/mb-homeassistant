<img src="brands/custom_integrations/apr_evse/icon.png" alt="APR EVSE" width="96" align="right">

# APR EVSE — Home Assistant integration

Local-push HACS custom integration for the APR EVSE smart charger. Talks to the device over its LAN HTTP + WebSocket API. No cloud, no MQTT, no auth.

## Install (HACS)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo (category: Integration).
2. Install **APR EVSE**, restart Home Assistant.
3. The charger is auto-discovered via zeroconf, or add it manually: Settings → Devices & Services → Add Integration → APR EVSE → host/IP.

## Behaviour

- Snapshot via `GET /api/state` (REST); live deltas via `/ws`. The WS on-connect push is truncated by firmware, so REST is always the source of truth.
- `state.car` / `state.pw` / `state.charge` are conditional: their entities go `unavailable` when the device omits the section.
- **No authentication** on the device API: anyone on the LAN can read state and control the charger.

## Options

- **Poll fallback interval** (default 30 s) — REST poll used when the WebSocket is down; also clears stale conditional sections.
- **Max charging current override** — caps the current slider; `0` uses the device's `max_evse_amps`.

## Entities

Controls: charging current + maximum charging current (`number`), charge mode + schedule (`select`), charging enabled / use car SOC / use price forecast (`switch`).

Sensors: status, charging/grid/PV power, session energy/duration/cost/range, voltage, temperature, electricity price, car/Powerwall SOC, plus Wi-Fi/uptime/RAM/FS/meter diagnostics.

Binary sensors: vehicle connected, charging, fault, cloud connected.
