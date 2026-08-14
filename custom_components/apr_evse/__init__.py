from __future__ import annotations

import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import AprEvseApi
from .const import (
    CONF_HOST,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    KEEPALIVE_TIMEOUT,
    MAX_DEVICE_CONNECTIONS,
)
from .coordinator import AprEvseCoordinator
from .mirror import AprEvseMirror
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    connector = aiohttp.TCPConnector(
        limit=MAX_DEVICE_CONNECTIONS,
        limit_per_host=MAX_DEVICE_CONNECTIONS,
        keepalive_timeout=KEEPALIVE_TIMEOUT,
    )
    session = aiohttp.ClientSession(connector=connector)
    entry.async_on_unload(session.close)

    api = AprEvseApi(
        session,
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
    )

    coordinator = AprEvseCoordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()
    coordinator.start_ws()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    async_setup_services(hass)

    mirror = AprEvseMirror(hass, entry, api)
    await mirror.async_start()
    entry.async_on_unload(mirror.async_stop)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: AprEvseCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        if not hass.data[DOMAIN]:
            async_unload_services(hass)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
