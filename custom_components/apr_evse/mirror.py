from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .api import AprEvseApi, AprEvseError
from .const import (
    CONF_CAR_SOC_ENTITY,
    CONF_HOME_BATTERY_AMPS_ENTITY,
    CONF_HOME_BATTERY_INTERVAL,
    CONF_HOME_BATTERY_SOC_ENTITY,
    CONF_LOG_PUSHES,
    DEFAULT_HOME_BATTERY_INTERVAL,
    EXT_CAR_SOC,
    EXT_FIELD_AMPS,
    EXT_FIELD_SOC,
    EXT_HOME_BATTERY,
    HOME_BATTERY_AMPS_MAX,
    HOME_BATTERY_AMPS_MIN,
    HOME_BATTERY_INTERVAL_MAX,
    HOME_BATTERY_INTERVAL_MIN,
)

_LOGGER = logging.getLogger(__name__)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


class AprEvseMirror:

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: AprEvseApi
    ) -> None:
        self.hass = hass
        self.api = api
        self._log_name = entry.title
        opts = entry.options
        self._car_entity: str | None = opts.get(CONF_CAR_SOC_ENTITY)
        self._soc_entity: str | None = opts.get(CONF_HOME_BATTERY_SOC_ENTITY)
        self._amps_entity: str | None = opts.get(CONF_HOME_BATTERY_AMPS_ENTITY)
        self._interval = int(
            _clamp(
                opts.get(CONF_HOME_BATTERY_INTERVAL, DEFAULT_HOME_BATTERY_INTERVAL),
                HOME_BATTERY_INTERVAL_MIN,
                HOME_BATTERY_INTERVAL_MAX,
            )
        )
        self._log_level = logging.INFO if opts.get(CONF_LOG_PUSHES) else logging.DEBUG
        self._unsubs: list[Any] = []

    @property
    def _tracked(self) -> list[str]:
        return [
            entity_id
            for entity_id in (self._car_entity, self._soc_entity, self._amps_entity)
            if entity_id
        ]

    async def async_start(self) -> None:
        if not self._tracked:
            return

        self._unsubs.append(
            async_track_state_change_event(
                self.hass, self._tracked, self._handle_state_change
            )
        )
        if self._soc_entity:
            self._unsubs.append(
                async_track_time_interval(
                    self.hass,
                    self._handle_keepalive,
                    timedelta(seconds=self._interval),
                )
            )

        await self._async_push_car()
        await self._async_push_home_battery()

    def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()


    def _value(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None


    async def _async_push_car(self) -> None:
        soc = self._value(self._car_entity)
        if soc is None:
            return
        await self._async_send(EXT_CAR_SOC, int(_clamp(soc, 0, 100)))

    async def _async_push_home_battery(self) -> None:
        soc = self._value(self._soc_entity)
        if soc is None:
            return
        payload: dict[str, Any] = {EXT_FIELD_SOC: int(_clamp(soc, 0, 100))}
        amps = self._value(self._amps_entity)
        if amps is not None:
            payload[EXT_FIELD_AMPS] = round(
                _clamp(amps, HOME_BATTERY_AMPS_MIN, HOME_BATTERY_AMPS_MAX), 1
            )
        await self._async_send(EXT_HOME_BATTERY, payload)

    async def _async_send(self, topic: str, payload: dict[str, Any] | int) -> None:
        try:
            await self.api.async_ext(topic, payload)
        except AprEvseError as err:
            _LOGGER.log(
                self._log_level,
                "%s ext/%s %s FAILED: %s",
                self._log_name,
                topic,
                payload,
                err,
            )
        else:
            _LOGGER.log(
                self._log_level, "%s ext/%s %s", self._log_name, topic, payload
            )


    async def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        if entity_id == self._car_entity:
            await self._async_push_car()
        if entity_id in (self._soc_entity, self._amps_entity):
            await self._async_push_home_battery()

    async def _handle_keepalive(self, _now: Any) -> None:
        await self._async_push_home_battery()
