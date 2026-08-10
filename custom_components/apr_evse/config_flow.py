from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import AprEvseApi, AprEvseConnectionError
from .const import (
    CONF_CAR_SOC_ENTITY,
    CONF_DEVICE_ID,
    CONF_HOME_BATTERY_INVERT_POWER,
    CONF_HOME_BATTERY_PHASES,
    CONF_HOME_BATTERY_POWER_ENTITY,
    CONF_HOME_BATTERY_POWER_ENTITY_L2,
    CONF_HOME_BATTERY_POWER_ENTITY_L3,
    CONF_HOME_BATTERY_SOC_ENTITY,
    CONF_HOME_BATTERY_VOLTAGE_ENTITY,
    CONF_HOME_BATTERY_VOLTAGE_ENTITY_L2,
    CONF_HOME_BATTERY_VOLTAGE_ENTITY_L3,
    CONF_HOST,
    CONF_LOG_PUSHES,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    DEFAULT_HOME_BATTERY_PHASES,
    DEFAULT_PORT,
    DEVICE_TYPE,
    DOMAIN,
    HOME_BATTERY_PHASE_OPTIONS,
    HOME_BATTERY_PHASES_THREE,
)

_LOGGER = logging.getLogger(__name__)


async def _probe(hass, host: str, port: int) -> dict[str, Any]:
    api = AprEvseApi(async_get_clientsession(hass), host=host, port=port)
    data = await api.async_get_state()
    sys_cfg = (data.get("config") or {}).get("sys") or {}
    mac = sys_cfg.get("mac")
    if not mac:
        raise AprEvseConnectionError("device did not report a MAC")
    return {
        CONF_MAC: mac,
        CONF_NAME: sys_cfg.get("device_name") or "APR EVSE",
    }


class AprEvseConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            try:
                identity = await _probe(self.hass, host, port)
            except AprEvseConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(format_mac(identity[CONF_MAC]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=identity[CONF_NAME],
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_MAC: identity[CONF_MAC],
                        CONF_NAME: identity[CONF_NAME],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        props = discovery_info.properties
        if props.get("type") != DEVICE_TYPE:
            return self.async_abort(reason="not_apr_evse")

        mac = props.get("mac")
        if not mac:
            return self.async_abort(reason="no_mac")

        host = (
            str(discovery_info.ip_address)
            if getattr(discovery_info, "ip_address", None)
            else discovery_info.host
        )
        port = discovery_info.port or DEFAULT_PORT
        name = props.get("device_name") or "APR EVSE"

        await self.async_set_unique_id(format_mac(mac))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._discovery = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_MAC: mac,
            CONF_NAME: name,
            CONF_DEVICE_ID: props.get("device_id"),
        }
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            try:
                await _probe(
                    self.hass, self._discovery[CONF_HOST], self._discovery[CONF_PORT]
                )
            except AprEvseConnectionError:
                return self.async_abort(reason="cannot_connect")
            return self.async_create_entry(
                title=self._discovery[CONF_NAME], data=self._discovery
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"name": self._discovery[CONF_NAME]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AprEvseOptionsFlow()


_SOURCE_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["sensor", "number", "input_number"])
)

_PHASES_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=HOME_BATTERY_PHASE_OPTIONS,
        mode=selector.SelectSelectorMode.DROPDOWN,
        translation_key="home_battery_phases",
    )
)


def _picker(opts: dict[str, Any], key: str) -> Any:
    return vol.Optional(key, description={"suggested_value": opts.get(key)})


class AprEvseOptionsFlow(OptionsFlow):

    def __init__(self) -> None:
        self._main_input: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            cleaned = {k: v for k, v in user_input.items() if v not in (None, "")}
            if (
                cleaned.get(CONF_HOME_BATTERY_PHASES) == HOME_BATTERY_PHASES_THREE
                and cleaned.get(CONF_HOME_BATTERY_POWER_ENTITY)
            ):
                self._main_input = cleaned
                return await self.async_step_phases()
            return self.async_create_entry(title="", data=cleaned)

        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    _picker(opts, CONF_CAR_SOC_ENTITY): _SOURCE_SELECTOR,
                    _picker(opts, CONF_HOME_BATTERY_SOC_ENTITY): _SOURCE_SELECTOR,
                    _picker(opts, CONF_HOME_BATTERY_POWER_ENTITY): _SOURCE_SELECTOR,
                    vol.Optional(
                        CONF_HOME_BATTERY_INVERT_POWER,
                        default=opts.get(CONF_HOME_BATTERY_INVERT_POWER, False),
                    ): selector.BooleanSelector(),
                    _picker(opts, CONF_HOME_BATTERY_VOLTAGE_ENTITY): _SOURCE_SELECTOR,
                    vol.Optional(
                        CONF_HOME_BATTERY_PHASES,
                        default=opts.get(
                            CONF_HOME_BATTERY_PHASES, DEFAULT_HOME_BATTERY_PHASES
                        ),
                    ): _PHASES_SELECTOR,
                    vol.Optional(
                        CONF_LOG_PUSHES,
                        default=opts.get(CONF_LOG_PUSHES, False),
                    ): selector.BooleanSelector(),
                }
            ),
        )

    async def async_step_phases(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            cleaned = {k: v for k, v in user_input.items() if v not in (None, "")}
            return self.async_create_entry(
                title="", data={**self._main_input, **cleaned}
            )

        opts = self.config_entry.options
        return self.async_show_form(
            step_id="phases",
            data_schema=vol.Schema(
                {
                    _picker(opts, CONF_HOME_BATTERY_POWER_ENTITY_L2): _SOURCE_SELECTOR,
                    _picker(
                        opts, CONF_HOME_BATTERY_VOLTAGE_ENTITY_L2
                    ): _SOURCE_SELECTOR,
                    _picker(opts, CONF_HOME_BATTERY_POWER_ENTITY_L3): _SOURCE_SELECTOR,
                    _picker(
                        opts, CONF_HOME_BATTERY_VOLTAGE_ENTITY_L3
                    ): _SOURCE_SELECTOR,
                }
            ),
        )
