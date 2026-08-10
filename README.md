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

## Push data to the charger

Feed the charger's constraints from any HA sensor. Requires firmware 2.2.+, which exposes `POST /api/ext/*`.

### Setup

Settings → Devices & Services → APR EVSE → **Configure**, then pick:

| Option | Feeds | Pushed |
|---|---|---|
| Car battery level (%) | Car SOC constraint (`Use car SOC` switch) | on refresh; valid 24 h |
| Home battery level (%) | Home battery SOC for solar charge mode | with the inverter power |
| Inverter power (W, signed) | Inverter AC power, and the AC current derived from it | on refresh — sets the pace for the whole set |
| Invert the inverter power sign | Flips the sign of every power sensor before it is sent or converted | — |
| Inverter AC voltage (V) | Divisor for that current | read at send time |
| Inverter phases | 1, or 3 to add a page for the phase 2/3 sensor pairs | — |
| Log every value sent | Troubleshooting | — |

The charger's solar logic runs on **current**, not power, but inverter integrations rarely expose the signed AC busbar current it needs. So pick power + voltage; the integration sends both as measured and the charger divides them itself, the same conversion its own inverter driver does:

```
APR EVSE ext/home_battery {'pw': {'soc': 62, 'p_ac': [-1932, 0, 0], 'v_ac': [230, 0, 0]}}
APR EVSE ext/car_soc 41
```

A zero **voltage** means "no such phase", so the example above is a single-phase feed. Without a voltage sensor only power is sent (graphs keep working, solar charging can't follow your surplus). Voltage readings outside 50-300 V are ignored — pick the AC side, not a DC battery or string voltage.

Both values are **signed**, and the sign is load-bearing: positive means the inverter is injecting, negative means it is charging the battery. Don't feed either an absolute value.

Plenty of integrations use the opposite convention. Turn on **Invert the inverter power sign** for those — it flips every power reading before it is sent and before the current is derived. To check: turn on the log option, and with the sun up and the house battery full, `pw_power_now` should be **positive**.

### Three-phase

Set **Inverter phases** to 3 and a second page asks for phase 2 and 3, each with its own power and voltage. The sensors on the first page are phase 1.

```
APR EVSE ext/home_battery {'pw': {'soc': 50, 'p_ac': [1932, 1863, 1817], 'v_ac': [232, 231, 233]}}
```

Per-phase pairs are required because a current only means something per phase.

The **voltage** is what marks a phase as present — nothing runs at 0 V, while 0 W or 0 A is just an idle phase. So a phase whose voltage sensor is empty or unavailable goes out as 0 and the charger reads the feed as single phase, sizing surplus on phase 1 alone until it comes back.

Requires firmware newer than 2.2.2608001 — older builds only understand the single-value `pw_amps_now` form.

### Timing

There is no send interval. The whole home battery set (level + power + current) goes out every time the **phase 1 inverter power sensor** refreshes — battery level, voltage and the other phases are read at that moment, so everything arrives together and consistent. With no power sensor configured, the battery level sensor sets the pace instead. Repeated identical readings count as refreshes, so a polling sensor keeps feeding the charger even when the value is flat.

So the source sensor's polling rate is the send rate: make the inverter integration as fast as it will go, 1 - 5 s is ideal. Sends closer than 1 s apart are skipped. Anything slower than 60 s leaves gaps — the charger discards home battery data 60 s after the last one and falls back to its own logic.

Turning on the log option writes one line per send to Settings → System → Logs — use it to confirm what the charger receives, then turn it back off.

An unavailable or non-numeric source stops the pushes: the charger expires the value and falls back to its own logic instead of acting on a stale reading.

Skip the home battery options if the charger already polls a local inverter — both write the same state and the last writer wins.



## Dashboard

Example: [`examples/dashboard.yaml`](examples/dashboard.yaml). Conditional sections (car / home battery / PV) auto-hide where the data isn't reported. Change device name `apr_evse` to your own, you can find device slug here: Settings → Devices & Services → APR EVSE → click the device → click any entity → the entity ID is shown 

## Want one?

You love homeassistant so much that you want this EVSE just for the integration? Do reachout to me at https://ww2.missingbolt.com/