"""Constants for the APR EVSE integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "apr_evse"
MANUFACTURER: Final = "APR"
DEFAULT_MODEL: Final = "APR EVSE"

# mDNS TXT discovery
DEVICE_TYPE: Final = "aprevse"  # TXT `type` value advertised by firmware

# Config entry / options keys
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_MAC: Final = "mac"
CONF_DEVICE_ID: Final = "device_id"
CONF_NAME: Final = "name"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_AMPS_MAX: Final = "amps_max"

DEFAULT_PORT: Final = 80
# REST poll interval. Acts as the WS backstop: a full snapshot re-fetch that
# clears stale conditional sections (car/pw/charge) the WS deltas can't retract.
DEFAULT_SCAN_INTERVAL: Final = 30
WS_RECONNECT_BACKOFF: Final = (1, 2, 5, 10, 30)

# REST paths
PATH_STATE: Final = "/api/state"
PATH_CONFIG: Final = "/api/config"
PATH_CONTROL: Final = "/api/control"
PATH_WS: Final = "/ws"

# Amps bounds (firmware clamps to [6, 80]; upper further clamped to max_evse_amps)
AMPS_MIN: Final = 6
AMPS_MAX_HARD: Final = 80

# Control command keys
CMD_STATE: Final = "state"
CMD_AMPS: Final = "amps"  # live charging-current target (6..pamps)
CMD_PAMPS: Final = "pamps"  # user-defined current ceiling (6..max_evse_amps)
CMD_MODE: Final = "mode"
CMD_SCHEDULE: Final = "schedule"
CMD_CAR_SOC: Final = "car_soc_toggle"

# evse.state enum -> HA status slug (translation key `evse_status`)
EVSE_STATE_STARTING: Final = (-2, 0)
EVSE_STATE_CHARGING: Final = 3
EVSE_STATE_FAULT_RANGE: Final = range(4, 15)  # 4..14 inclusive
EVSE_STATE_SLEEPING: Final = 254
EVSE_STATE_DISABLED: Final = 255

EVSE_STATE_MAP: Final[dict[int, str]] = {
    -2: "starting",
    0: "starting",
    1: "not_connected",
    2: "connected",
    3: "charging",
    4: "vent_required",
    5: "diode_check_failed",
    6: "gfi_fault",
    7: "no_ground",
    8: "stuck_relay",
    9: "gfi_self_test_failed",
    10: "over_temperature",
    11: "under_voltage",
    12: "over_current",
    13: "evse_over_temperature",
    14: "fault",
    254: "sleeping",
    255: "disabled",
}

# Unique sorted list of status slugs for the enum sensor `options`.
EVSE_STATUS_OPTIONS: Final[list[str]] = sorted(set(EVSE_STATE_MAP.values()))

# Charge mode (constrains.mode / `mode` command)
MODE_OPTIONS: Final[list[str]] = ["normal", "solar"]
# Charge schedule (constrains.scheduler / `schedule` command)
SCHEDULE_OPTIONS: Final[list[str]] = ["off", "scheduler"]
