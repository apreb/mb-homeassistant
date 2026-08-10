from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AprEvseApi, AprEvseConnectionError
from .const import DOMAIN, SCAN_INTERVAL, WS_RECONNECT_BACKOFF

_LOGGER = logging.getLogger(__name__)


def _deep_merge(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class AprEvseCoordinator(DataUpdateCoordinator[dict[str, Any]]):

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: AprEvseApi,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.entry = entry
        self.api = api
        self.ws_connected = False
        self._ws_task: asyncio.Task | None = None
        self._stop = False

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_state()
        except AprEvseConnectionError as err:
            raise UpdateFailed(str(err)) from err


    def start_ws(self) -> None:
        if self._ws_task is None:
            self._stop = False
            self._ws_task = self.entry.async_create_background_task(
                self.hass, self._ws_loop(), f"{DOMAIN}_ws"
            )

    async def async_shutdown(self) -> None:
        self._stop = True
        if self._ws_task:
            self._ws_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ws_task
            self._ws_task = None
        await super().async_shutdown()

    async def _ws_loop(self) -> None:
        attempt = 0
        while not self._stop:
            try:
                async with await self.api.async_ws_connect() as ws:
                    attempt = 0
                    self.ws_connected = True
                    await self.async_request_refresh()
                    async for msg in ws:
                        if self._stop:
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self._handle_ws_text(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSING,
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except (AprEvseConnectionError, aiohttp.ClientError, OSError) as err:
                _LOGGER.debug("WS error, will reconnect: %s", err)
            finally:
                self.ws_connected = False

            if self._stop:
                break
            delay = WS_RECONNECT_BACKOFF[min(attempt, len(WS_RECONNECT_BACKOFF) - 1)]
            attempt += 1
            await asyncio.sleep(delay)

    def _handle_ws_text(self, raw: str) -> None:
        try:
            delta = json.loads(raw)
        except (ValueError, TypeError):
            _LOGGER.debug("Dropping unparseable WS frame (%d bytes)", len(raw))
            return
        if not isinstance(delta, dict):
            return
        base = dict(self.data) if self.data else {}
        merged = _deep_merge(base, delta)
        self.async_set_updated_data(merged)
