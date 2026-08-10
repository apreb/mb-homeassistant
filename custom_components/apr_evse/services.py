from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import ATTR_AREA_ID, ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .api import AprEvseError
from .const import (
    ATTR_AMPS,
    ATTR_POWER,
    ATTR_SOC,
    DOMAIN,
    EXT_CAR_SOC,
    EXT_FIELD_CURRENT_AC,
    EXT_FIELD_POWER_AC,
    EXT_FIELD_SOC,
    EXT_HOME_BATTERY,
    EXT_SECTION_PW,
    HOME_BATTERY_AMPS_MAX,
    HOME_BATTERY_AMPS_MIN,
    HOME_BATTERY_POWER_MAX,
    HOME_BATTERY_POWER_MIN,
    SERVICE_SET_CAR_SOC,
    SERVICE_SET_HOME_BATTERY_SOC,
)
from .coordinator import AprEvseCoordinator

_TARGET_SCHEMA = {
    vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Optional(ATTR_AREA_ID): vol.All(cv.ensure_list, [cv.string]),
}
_SOC = vol.All(vol.Coerce(int), vol.Range(min=0, max=100))

CAR_SOC_SERVICE_SCHEMA = vol.Schema({**_TARGET_SCHEMA, vol.Required(ATTR_SOC): _SOC})

HOME_BATTERY_SERVICE_SCHEMA = vol.Schema(
    {
        **_TARGET_SCHEMA,
        vol.Required(ATTR_SOC): _SOC,
        vol.Optional(ATTR_AMPS): vol.All(
            vol.Coerce(float),
            vol.Range(min=HOME_BATTERY_AMPS_MIN, max=HOME_BATTERY_AMPS_MAX),
        ),
        vol.Optional(ATTR_POWER): vol.All(
            vol.Coerce(int),
            vol.Range(min=HOME_BATTERY_POWER_MIN, max=HOME_BATTERY_POWER_MAX),
        ),
    }
)


def _coordinators(hass: HomeAssistant, call: ServiceCall) -> list[AprEvseCoordinator]:
    entries: dict[str, AprEvseCoordinator] = hass.data.get(DOMAIN, {})
    if not entries:
        raise HomeAssistantError("No APR EVSE device is set up")

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    device_ids: dict[str, None] = dict.fromkeys(call.data.get(ATTR_DEVICE_ID, []))

    for entity_id in call.data.get(ATTR_ENTITY_ID, []):
        entity = ent_reg.async_get(entity_id)
        if entity is None or entity.device_id is None:
            raise ServiceValidationError(f"Unknown entity: {entity_id}")
        device_ids[entity.device_id] = None

    for area_id in call.data.get(ATTR_AREA_ID, []):
        for device in dr.async_entries_for_area(dev_reg, area_id):
            if any(entry_id in entries for entry_id in device.config_entries):
                device_ids[device.id] = None

    if not device_ids:
        return list(entries.values())

    found: list[AprEvseCoordinator] = []
    for device_id in device_ids:
        device = dev_reg.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown device ID: {device_id}")
        coordinator = next(
            (entries[entry_id] for entry_id in device.config_entries if entry_id in entries),
            None,
        )
        if coordinator is None:
            raise ServiceValidationError(
                f"Device {device.name or device_id} is not a loaded APR EVSE"
            )
        found.append(coordinator)

    return found


async def _async_push(
    hass: HomeAssistant, call: ServiceCall, topic: str, payload: dict[str, Any] | int
) -> None:
    for coordinator in _coordinators(hass, call):
        try:
            await coordinator.api.async_ext(topic, payload)
        except AprEvseError as err:
            raise HomeAssistantError(f"Failed to send {topic} to the charger: {err}") from err


def async_setup_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_CAR_SOC):
        return

    async def handle_set_car_soc(call: ServiceCall) -> None:
        await _async_push(hass, call, EXT_CAR_SOC, call.data[ATTR_SOC])

    async def handle_set_home_battery_soc(call: ServiceCall) -> None:
        section: dict[str, Any] = {EXT_FIELD_SOC: call.data[ATTR_SOC]}
        if ATTR_POWER in call.data:
            section[EXT_FIELD_POWER_AC] = [call.data[ATTR_POWER], 0, 0]
        if ATTR_AMPS in call.data:
            section[EXT_FIELD_CURRENT_AC] = [call.data[ATTR_AMPS], 0, 0]
        await _async_push(hass, call, EXT_HOME_BATTERY, {EXT_SECTION_PW: section})

    hass.services.async_register(
        DOMAIN, SERVICE_SET_CAR_SOC, handle_set_car_soc, schema=CAR_SOC_SERVICE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HOME_BATTERY_SOC,
        handle_set_home_battery_soc,
        schema=HOME_BATTERY_SERVICE_SCHEMA,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    hass.services.async_remove(DOMAIN, SERVICE_SET_CAR_SOC)
    hass.services.async_remove(DOMAIN, SERVICE_SET_HOME_BATTERY_SOC)
