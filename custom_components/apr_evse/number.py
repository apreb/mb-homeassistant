"""Number platform: live charging current and the user-defined current ceiling."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    AMPS_MAX_HARD,
    AMPS_MIN,
    CMD_AMPS,
    CMD_PAMPS,
    CONF_AMPS_MAX,
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
    """Shared base for the amps sliders (current + ceiling)."""

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = AMPS_MIN
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    @property
    def _ceiling(self) -> int:
        """Absolute upper bound: option override, else config max_evse_amps, else 80."""
        override = self.coordinator.entry.options.get(CONF_AMPS_MAX)
        if override:
            return min(int(override), AMPS_MAX_HARD)
        cfg_max = self.cfg("evse").get("max_evse_amps")
        if isinstance(cfg_max, (int, float)) and cfg_max >= AMPS_MIN:
            return min(int(cfg_max), AMPS_MAX_HARD)
        return AMPS_MAX_HARD


class AprEvseChargingCurrent(_AprEvseAmpsNumber):
    """Live charging-current target (A).

    Firmware rejects any value above ``pamps``, so the slider's upper bound
    tracks the user current limit when the device reports one.
    """

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
    """User-defined maximum charging current (``pamps``).

    The ceiling for ``amps``; itself bounded by the device's configured
    ``max_evse_amps``. Lowering it below the live current pulls the current down.
    """

    _attr_translation_key = "current_limit"
    _attr_entity_category = EntityCategory.CONFIG

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
