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
CONF_CAR_SOC_ENTITY: Final = "car_soc_entity"
CONF_HOME_BATTERY_SOC_ENTITY: Final = "home_battery_soc_entity"
CONF_HOME_BATTERY_POWER_ENTITY: Final = "home_battery_power_entity"
CONF_HOME_BATTERY_VOLTAGE_ENTITY: Final = "home_battery_voltage_entity"
CONF_HOME_BATTERY_POWER_ENTITY_L2: Final = "home_battery_power_entity_l2"
CONF_HOME_BATTERY_VOLTAGE_ENTITY_L2: Final = "home_battery_voltage_entity_l2"
CONF_HOME_BATTERY_POWER_ENTITY_L3: Final = "home_battery_power_entity_l3"
CONF_HOME_BATTERY_VOLTAGE_ENTITY_L3: Final = "home_battery_voltage_entity_l3"
CONF_HOME_BATTERY_INVERT_POWER: Final = "home_battery_invert_power"
CONF_HOME_BATTERY_PHASES: Final = "home_battery_phases"
HOME_BATTERY_PHASE_KEYS: Final[tuple[tuple[str, str], ...]] = (
    (CONF_HOME_BATTERY_POWER_ENTITY, CONF_HOME_BATTERY_VOLTAGE_ENTITY),
    (CONF_HOME_BATTERY_POWER_ENTITY_L2, CONF_HOME_BATTERY_VOLTAGE_ENTITY_L2),
    (CONF_HOME_BATTERY_POWER_ENTITY_L3, CONF_HOME_BATTERY_VOLTAGE_ENTITY_L3),
)
LEGACY_CONF_HOME_BATTERY_AMPS_ENTITY: Final = "home_battery_amps_entity"
CONF_LOG_PUSHES: Final = "log_pushes"

DEFAULT_PORT: Final = 80
SCAN_INTERVAL: Final = 30
WS_RECONNECT_BACKOFF: Final = (1, 2, 5, 10, 30)

PATH_STATE: Final = "/api/state"
PATH_CONFIG: Final = "/api/config"
PATH_CONTROL: Final = "/api/control"
PATH_EXT: Final = "/api/ext"
PATH_WS: Final = "/ws"

AMPS_MIN: Final = 6
AMPS_MAX_HARD: Final = 80

CMD_STATE: Final = "state"
CMD_AMPS: Final = "amps"
CMD_PAMPS: Final = "pamps"
CMD_MODE: Final = "mode"
CMD_SCHEDULE: Final = "schedule"
CMD_CAR_SOC: Final = "car_soc_toggle"

EXT_CAR_SOC: Final = "car_soc"
EXT_HOME_BATTERY: Final = "home_battery"

SERVICE_SET_CAR_SOC: Final = "set_car_soc"
SERVICE_SET_HOME_BATTERY_SOC: Final = "set_home_battery_soc"
ATTR_SOC: Final = "soc"
ATTR_AMPS: Final = "amps"
ATTR_POWER: Final = "power"

EXT_SECTION_PW: Final = "pw"
EXT_FIELD_SOC: Final = "soc"
EXT_FIELD_POWER_AC: Final = "p_ac"
EXT_FIELD_VOLTAGE_AC: Final = "v_ac"
EXT_FIELD_CURRENT_AC: Final = "i_ac"
HOME_BATTERY_AMPS_MIN: Final = -100
HOME_BATTERY_AMPS_MAX: Final = 100
HOME_BATTERY_POWER_MIN: Final = -32768
HOME_BATTERY_POWER_MAX: Final = 32767
HOME_BATTERY_VOLTAGE_MIN: Final = 50
HOME_BATTERY_VOLTAGE_MAX: Final = 300
DEFAULT_HOME_BATTERY_PHASES: Final = "1"
HOME_BATTERY_PHASES_THREE: Final = "3"
HOME_BATTERY_PHASE_OPTIONS: Final[list[str]] = [
    DEFAULT_HOME_BATTERY_PHASES,
    HOME_BATTERY_PHASES_THREE,
]
MIN_HOME_BATTERY_PUSH_SPACING: Final = 1.0

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
