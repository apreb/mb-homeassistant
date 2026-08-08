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

## Push SOC to the charger

Feed the charger's constraints from any HA sensor. Requires firmware 2.1.2608015+, which exposes `POST /api/ext/*`.

### Setup (no automation needed)

Settings → Devices & Services → APR EVSE → **Configure**, then pick:

| Option | Feeds | Pushed |
|---|---|---|
| Car battery level (%) | Car SOC constraint (`Use car SOC` switch) | on change; valid 24 h |
| Home battery level (%) | Home battery SOC for solar charge mode | on change + on the send interval |
| Inverter current (A, signed) | Surplus detection for solar charge mode | with the battery level |
| Home battery send interval | Repeat rate for the two above (1-60 s, default 30) | — |
| Log every value sent | Troubleshooting | — |

Set the send interval to 1-5 s when an inverter current sensor is configured — the charger tracks surplus from that value. 30-60 s is fine for battery level alone; the device drops the data after 60 s.

Turning on the log option writes one line per send to Settings → System → Logs — use it to confirm what the charger receives, then turn it back off:

```
APR EVSE ext/home_battery {'soc': 62, 'pw_amps_now': -8.4}
APR EVSE ext/car_soc 41
```

Each charger has its own Configure page, so a multi-charger install just repeats this per device — no device IDs, no service targets, no YAML.

An unavailable or non-numeric source stops the pushes: the charger expires the value and falls back to its own logic instead of acting on a stale reading.

The current is **signed**, and the sign is load-bearing: positive means the inverter is injecting, negative means it is charging the battery. Below -2 A the charger reads "no surplus" and won't pull for the car, so don't feed it an absolute value.

Skip the home battery options if the charger already polls a local inverter — both write the same state and the last writer wins.

### Services (advanced)

For sources that aren't HA entities, or custom cadence:

| Service | Fields |
|---|---|
| `apr_evse.set_car_soc` | `soc` |
| `apr_evse.set_home_battery_soc` | `soc`, `amps` (optional, signed) |

Targeting is optional — with one charger, omit `target`. With several, target by `device_id`, by any entity of the charger (`entity_id: sensor.apr_evse_status`), or by `area_id`.

```yaml
automation:
  - alias: Mirror home battery SOC to EVSE
    triggers:
      - trigger: time_pattern
        seconds: "/30"
    conditions:
      - condition: template
        value_template: "{{ states('sensor.bms_apr1_soc') | int(-1) >= 0 }}"
    actions:
      - action: apr_evse.set_home_battery_soc
        data:
          soc: "{{ states('sensor.bms_apr1_soc') | int }}"
          amps: "{{ states('sensor.bms_apr1_iac') | float(0) }}"
```

Keep the condition: an `unavailable` source renders as `0` through `| int`, which would tell the charger the battery is empty.

## Dashboard

Example: [`examples/dashboard.yaml`](examples/dashboard.yaml). Conditional sections (car / home battery / PV) auto-hide where the data isn't reported. Change device name `apr_evse` to your own, you can find device slug here: Settings → Devices & Services → APR EVSE → click the device → click any entity → the entity ID is shown 

## Want one?

You love homeassistant so much that you want this EVSE just for the integration? Do reachout to me at https://ww2.missingbolt.com/