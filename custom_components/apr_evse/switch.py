"""Switch platform: charging enable, car-SOC constraint, forecast constraint."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_CAR_SOC, CMD_FORECAST, CMD_STATE, DOMAIN
from .coordinator import AprEvseCoordinator
from .entity import AprEvseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AprEvseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AprEvseChargingSwitch(coordinator),
            AprEvseCarSocSwitch(coordinator),
            AprEvseForecastSwitch(coordinator),
        ]
    )


class AprEvseChargingSwitch(AprEvseEntity, SwitchEntity):
    """Master enable. Off => sleeping/disabled (evse.state 254/255)."""

    _attr_translation_key = "charging_enabled"

    def __init__(self, coordinator: AprEvseCoordinator) -> None:
        super().__init__(coordinator, "charging_enabled")

    @property
    def is_on(self) -> bool | None:
        s = self.evse_state
        if s is None or s <= 0:  # not reported / ESP32 starting
            return None
        return s not in (254, 255)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_control({CMD_STATE: 1})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_control({CMD_STATE: 0})
        await self.coordinator.async_request_refresh()


class AprEvseCarSocSwitch(AprEvseEntity, SwitchEntity):
    """Use car SOC as a charge constraint. Only readable when car SOC is fresh."""

    _attr_translation_key = "use_car_soc"

    def __init__(self, coordinator: AprEvseCoordinator) -> None:
        super().__init__(coordinator, "use_car_soc")

    @property
    def available(self) -> bool:
        return super().available and self.has_state("car")

    @property
    def is_on(self) -> bool | None:
        val = self.st("car").get("enabled")
        return bool(val) if isinstance(val, (int, bool)) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_control({CMD_CAR_SOC: 1})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_control({CMD_CAR_SOC: 0})
        await self.coordinator.async_request_refresh()


class AprEvseForecastSwitch(AprEvseEntity, SwitchEntity):
    """Use price forecast as a constraint.

    The firmware exposes no readback for this flag, so this is an assumed-state
    switch: it reflects the last command issued, not confirmed device state.
    """

    _attr_translation_key = "use_price_forecast"
    _attr_assumed_state = True

    def __init__(self, coordinator: AprEvseCoordinator) -> None:
        super().__init__(coordinator, "use_price_forecast")
        self._attr_is_on = None

    @property
    def is_on(self) -> bool | None:
        return self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_control({CMD_FORECAST: 1})
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.async_control({CMD_FORECAST: 0})
        self._attr_is_on = False
        self.async_write_ha_state()
