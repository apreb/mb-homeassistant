from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    AMPS_MAX_HARD,
    AMPS_MIN,
    CMD_AMPS,
    CMD_PAMPS,
    DOMAIN,
)
from .coordinator import AprEvseCoordinator
from .entity import AprEvseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AprEvseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [AprEvseChargingCurrent(coordinator), AprEvseCurrentLimit(coordinator)]
    )


class _AprEvseAmpsNumber(AprEvseEntity, NumberEntity):

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = AMPS_MIN
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    @property
    def _ceiling(self) -> int:
        cfg_max = self.cfg("evse").get("max_evse_amps")
        if isinstance(cfg_max, (int, float)) and cfg_max >= AMPS_MIN:
            return min(int(cfg_max), AMPS_MAX_HARD)
        return AMPS_MAX_HARD


class AprEvseChargingCurrent(_AprEvseAmpsNumber):

    _attr_translation_key = "charging_current"

    def __init__(self, coordinator: AprEvseCoordinator) -> None:
        super().__init__(coordinator, "charging_current")

    @property
    def native_max_value(self) -> float:
        ceiling = self._ceiling
        pamps = self.st("evse").get("pamps")
        if isinstance(pamps, (int, float)) and pamps >= AMPS_MIN:
            return min(ceiling, int(pamps))
        return ceiling

    @property
    def native_value(self) -> float | None:
        val = self.st("evse").get("amps")
        return float(val) if isinstance(val, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        amps = max(AMPS_MIN, min(int(value), int(self.native_max_value)))
        await self.coordinator.api.async_control({CMD_AMPS: amps})
        await self.coordinator.async_request_refresh()


class AprEvseCurrentLimit(_AprEvseAmpsNumber):

    _attr_translation_key = "current_limit"

    def __init__(self, coordinator: AprEvseCoordinator) -> None:
        super().__init__(coordinator, "current_limit")

    @property
    def native_max_value(self) -> float:
        return self._ceiling

    @property
    def native_value(self) -> float | None:
        val = self.st("evse").get("pamps")
        return float(val) if isinstance(val, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        pamps = max(AMPS_MIN, min(int(value), int(self.native_max_value)))
        await self.coordinator.api.async_control({CMD_PAMPS: pamps})
        await self.coordinator.async_request_refresh()
