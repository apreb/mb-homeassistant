from __future__ import annotations

from typing import Final

DOMAIN: Final = "apr_evse"
MANUFACTURER: Final = "APR"
DEFAULT_MODEL: Final = "APR EVSE"

DEVICE_TYPE: Final = "aprevse"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_MAC: Final = "mac"
CONF_DEVICE_ID: Final = "device_id"
CONF_NAME: Final = "name"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_AMPS_MAX: Final = "amps_max"

DEFAULT_PORT: Final = 80
DEFAULT_SCAN_INTERVAL: Final = 30
WS_RECONNECT_BACKOFF: Final = (1, 2, 5, 10, 30)

PATH_STATE: Final = "/api/state"
PATH_CONFIG: Final = "/api/config"
PATH_CONTROL: Final = "/api/control"
PATH_WS: Final = "/ws"

AMPS_MIN: Final = 6
AMPS_MAX_HARD: Final = 80

CMD_STATE: Final = "state"
CMD_AMPS: Final = "amps"
CMD_PAMPS: Final = "pamps"
CMD_MODE: Final = "mode"
CMD_SCHEDULE: Final = "schedule"
CMD_CAR_SOC: Final = "car_soc_toggle"

EVSE_STATE_STARTING: Final = (-2, 0)
EVSE_STATE_CHARGING: Final = 3
EVSE_STATE_FAULT_RANGE: Final = range(4, 15)
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

EVSE_STATUS_OPTIONS: Final[list[str]] = sorted(set(EVSE_STATE_MAP.values()))

MODE_OPTIONS: Final[list[str]] = ["normal", "solar"]
SCHEDULE_OPTIONS: Final[list[str]] = ["off", "scheduler"]
