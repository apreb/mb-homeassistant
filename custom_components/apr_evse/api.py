"""Thin async client for the APR EVSE local HTTP + WebSocket API.

No auth: every endpoint is open on the LAN by design.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    DEFAULT_PORT,
    PATH_CONTROL,
    PATH_STATE,
    PATH_WS,
)

_LOGGER = logging.getLogger(__name__)


class AprEvseError(Exception):
    """Base error talking to the device."""


class AprEvseConnectionError(AprEvseError):
    """Could not reach the device."""


class AprEvseApi:
    """REST + WS client. One instance per config entry."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = DEFAULT_PORT,
        timeout: float = 5.0,
    ) -> None:
        self._session = session
        self._host = host
        self._port = port
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def base_url(self) -> str:
        if self._port and self._port != 80:
            return f"http://{self._host}:{self._port}"
        return f"http://{self._host}"

    @property
    def ws_url(self) -> str:
        host = f"{self._host}:{self._port}" if self._port and self._port != 80 else self._host
        return f"ws://{host}{PATH_WS}"

    async def async_get_state(self) -> dict[str, Any]:
        """Full authoritative snapshot: {"ts", "state", "config"} (4096 buf)."""
        return await self._get_json(PATH_STATE)

    async def async_control(self, payload: dict[str, int]) -> int:
        """POST a flat control object. Returns the count of accepted keys.

        Firmware replies {"parsed":N} (200) or 404 when zero keys matched.
        """
        try:
            async with self._session.post(
                f"{self.base_url}{PATH_CONTROL}",
                json=payload,
                timeout=self._timeout,
            ) as resp:
                if resp.status == 404:
                    _LOGGER.warning("Control rejected (no keys accepted): %s", payload)
                    return 0
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                return int(data.get("parsed", 0)) if isinstance(data, dict) else 0
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise AprEvseConnectionError(f"control failed: {err}") from err

    async def async_ws_connect(self) -> aiohttp.ClientWebSocketResponse:
        """Open the delta stream. Caller owns the lifecycle."""
        try:
            return await self._session.ws_connect(self.ws_url, heartbeat=30)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise AprEvseConnectionError(f"ws connect failed: {err}") from err

    async def _get_json(self, path: str) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{self.base_url}{path}", timeout=self._timeout
            ) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise AprEvseConnectionError(f"GET {path} failed: {err}") from err
