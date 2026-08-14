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
- Two TCP connections per charger, no more: the WebSocket, and one keep-alive socket every REST call and data push queues on.

## Push data to the charger

Feed the charger's constraints from any HA sensor. Requires firmware 2.2.+, which exposes `POST /api/ext/*`. The home battery options additionally need a build newer than 2.2.2608001, which is where the charger learned the per-phase payload; car battery level works on any 2.2.

### Setup

Settings → Devices & Services → APR EVSE → **Configure**, then pick:

| Option | Feeds | Pushed |
|---|---|---|
| Car battery level (%) | Car SOC constraint (`Use car SOC` switch) | on change of whole %, plus hourly; valid 24 h |
| Home battery level (%) | Home battery SOC for solar charge mode | with the inverter power |
| Inverter power (W, signed) | Inverter AC power, and the current the charger derives from it | on refresh — sets the pace for the whole set |
| Invert the inverter power sign | Flips the sign of every power sensor before it is sent | — |
| Inverter AC voltage (V) | The charger's divisor, and what marks a phase as present | read at send time |
| Inverter phases | 1, or 3 to add a page for the phase 2/3 sensor pairs | — |
| Log every value sent | Troubleshooting | — |

The charger's solar logic runs on **current**, not power. When real power approaches zero, reactive current circulation, driven further by small phase mismatch introduced by the inverter, becomes the dominant component. This phenomenon, easily confirmed by the utility grid meter, results in unusual high current reporting at very low real power figures, preventing the algorithm to fully zero out the real power. One possible solution is to calculate current from real power figures, pick power + voltage; the integration sends both as measured and the charger divides them itself, the same conversion its own inverter driver does:

```
APR EVSE ext/home_battery {'pw': {'soc': 62, 'p_ac': [-1932, 0, 0], 'v_ac': [230, 0, 0]}}
APR EVSE ext/car_soc 41
```

Power is **signed**, and the sign is load-bearing: positive means the inverter is injecting, negative means it is charging the battery. Don't feed it an absolute value — the charger reads the sign to decide whether there is surplus for the car, and carries it into the derived current.

Plenty of integrations use the opposite convention. Turn on **Invert the inverter power sign** for those. To check: turn on the log option, and with the sun up and the house battery full, the `p_ac` values should be **positive**.

### Three-phase

Set **Inverter phases** to 3 and a second page asks for phase 2 and 3, each with its own power and voltage. The sensors on the first page are phase 1.

```
APR EVSE ext/home_battery {'pw': {'soc': 50, 'p_ac': [1932, 1863, 1817], 'v_ac': [232, 231, 233]}}
```

## Dashboard

Example: [`examples/dashboard.yaml`](examples/dashboard.yaml). Conditional sections (car / home battery / PV) auto-hide where the data isn't reported. Change device name `apr_evse` to your own, you can find device slug here: Settings → Devices & Services → APR EVSE → click the device → click any entity → the entity ID is shown 

## Want one?

You love homeassistant so much that you want this EVSE just for the integration? Do reachout to me at https://ww2.missingbolt.com/