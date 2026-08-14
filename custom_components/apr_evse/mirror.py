from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    Event,
    EventStateChangedData,
    EventStateReportedData,
    HomeAssistant,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_state_report_event,
)

from .api import AprEvseApi, AprEvseError
from .const import (
    CAR_SOC_REFRESH_INTERVAL,
    CONF_CAR_SOC_ENTITY,
    CONF_HOME_BATTERY_INVERT_POWER,
    CONF_HOME_BATTERY_PHASES,
    CONF_HOME_BATTERY_SOC_ENTITY,
    CONF_LOG_PUSHES,
    DEFAULT_HOME_BATTERY_PHASES,
    EXT_CAR_SOC,
    EXT_FIELD_POWER_AC,
    EXT_FIELD_SOC,
    EXT_FIELD_VOLTAGE_AC,
    EXT_HOME_BATTERY,
    EXT_SECTION_PW,
    HOME_BATTERY_PHASE_KEYS,
    HOME_BATTERY_PHASE_OPTIONS,
    HOME_BATTERY_VOLTAGE_MAX,
    HOME_BATTERY_VOLTAGE_MIN,
    LEGACY_CONF_HOME_BATTERY_AMPS_ENTITY,
    MIN_HOME_BATTERY_PUSH_SPACING,
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
        self._invert_power = bool(opts.get(CONF_HOME_BATTERY_INVERT_POWER))
        try:
            phases = int(opts.get(CONF_HOME_BATTERY_PHASES, DEFAULT_HOME_BATTERY_PHASES))
        except (TypeError, ValueError):
            phases = 1
        if str(phases) not in HOME_BATTERY_PHASE_OPTIONS:
            phases = 1
        self._phase_entities: list[tuple[str | None, str | None]] = [
            (opts.get(power_key) or None, opts.get(voltage_key) or None)
            for power_key, voltage_key in HOME_BATTERY_PHASE_KEYS[:phases]
        ]
        self._legacy_amps_entity: str | None = opts.get(
            LEGACY_CONF_HOME_BATTERY_AMPS_ENTITY
        )
        self._voltage_warned = False
        self._trigger_entity = next(
            (power for power, _ in self._phase_entities if power), self._soc_entity
        )
        self._last_home_battery_push = float("-inf")
        self._last_car_soc: int | None = None
        self._last_car_push = float("-inf")
        self._log_level = logging.INFO if opts.get(CONF_LOG_PUSHES) else logging.DEBUG
        self._unsubs: list[Any] = []

    @property
    def _tracked(self) -> list[str]:
        return [
            entity_id
            for entity_id in (self._car_entity, self._trigger_entity)
            if entity_id
        ]

    async def async_start(self) -> None:
        if self._legacy_amps_entity:
            _LOGGER.warning(
                "%s: the inverter current option was replaced by inverter power "
                "+ voltage (the current is now derived from them). %s is no "
                "longer sent -- reconfigure the integration to restore it",
                self._log_name,
                self._legacy_amps_entity,
            )

        if not self._tracked:
            return

        self._unsubs.append(
            async_track_state_change_event(
                self.hass, self._tracked, self._handle_state_change
            )
        )
        if self._trigger_entity:
            self._unsubs.append(
                async_track_state_report_event(
                    self.hass, [self._trigger_entity], self._handle_trigger_report
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
            self._last_car_soc = None
            return
        percent = int(_clamp(soc, 0, 100))
        now = self.hass.loop.time()
        if (
            percent == self._last_car_soc
            and now - self._last_car_push < CAR_SOC_REFRESH_INTERVAL
        ):
            return
        if await self._async_send(EXT_CAR_SOC, percent):
            self._last_car_soc = percent
            self._last_car_push = now

    async def _async_push_home_battery(self) -> None:
        now = self.hass.loop.time()
        if now - self._last_home_battery_push < MIN_HOME_BATTERY_PUSH_SPACING:
            return

        soc = self._value(self._soc_entity)
        if soc is None:
            return
        section: dict[str, Any] = {EXT_FIELD_SOC: int(_clamp(soc, 0, 100))}
        p_ac, v_ac = self._phase_readings()
        if p_ac is not None:
            section[EXT_FIELD_POWER_AC] = p_ac
            section[EXT_FIELD_VOLTAGE_AC] = v_ac
        self._last_home_battery_push = now
        await self._async_send(EXT_HOME_BATTERY, {EXT_SECTION_PW: section})

    def _phase_readings(self) -> tuple[list[int] | None, list[int]]:
        p_ac = [0, 0, 0]
        v_ac = [0, 0, 0]
        unusable_voltage: list[str] = []
        got_power = False

        for index, (power_entity, voltage_entity) in enumerate(self._phase_entities):
            power = self._value(power_entity)
            if power is None:
                continue
            if self._invert_power:
                power = -power
            p_ac[index] = int(round(power))
            got_power = True

            voltage = self._value(voltage_entity)
            if (
                voltage is None
                or not HOME_BATTERY_VOLTAGE_MIN <= voltage <= HOME_BATTERY_VOLTAGE_MAX
            ):
                unusable_voltage.append(
                    f"L{index + 1}: "
                    f"{'not configured' if voltage_entity is None else voltage}"
                )
                continue
            v_ac[index] = int(round(voltage))

        if unusable_voltage:
            if not self._voltage_warned:
                self._voltage_warned = True
                _LOGGER.warning(
                    "%s: no usable inverter voltage (%s), sending power only. The "
                    "charger derives the current from power / voltage and needs "
                    "it to size solar charging",
                    self._log_name,
                    ", ".join(unusable_voltage),
                )
        else:
            self._voltage_warned = False

        if not got_power:
            return None, v_ac
        return p_ac, v_ac

    async def _async_send(self, topic: str, payload: dict[str, Any] | int) -> bool:
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
            return False
        _LOGGER.log(self._log_level, "%s ext/%s %s", self._log_name, topic, payload)
        return True


    async def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        if entity_id == self._car_entity:
            await self._async_push_car()
        if entity_id == self._trigger_entity:
            await self._async_push_home_battery()

    async def _handle_trigger_report(
        self, _event: Event[EventStateReportedData]
    ) -> None:
        await self._async_push_home_battery()
