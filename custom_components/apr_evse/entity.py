"""Base entity + data accessors for APR EVSE."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MAC, DEFAULT_MODEL, DOMAIN, MANUFACTURER
from .coordinator import AprEvseCoordinator


class AprEvseEntity(CoordinatorEntity[AprEvseCoordinator]):
    """Common base: device info, unique_id, and snapshot accessors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AprEvseCoordinator, key: str) -> None:
        super().__init__(coordinator)
        mac = coordinator.entry.data[CONF_MAC]
        self._mac = format_mac(mac)
        self._attr_unique_id = f"{self._mac}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        sys_cfg = self.cfg("sys")
        sys_state = self.st("sys")
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            connections={(CONNECTION_NETWORK_MAC, self._mac)},
            manufacturer=MANUFACTURER,
            model=sys_cfg.get("model", DEFAULT_MODEL),
            name=sys_cfg.get("device_name")
            or self.coordinator.entry.title
            or DEFAULT_MODEL,
            sw_version=sys_state.get("firmware"),
        )

    # --- snapshot accessors -------------------------------------------------

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    def st(self, section: str) -> dict[str, Any]:
        """state.<section> as a dict (empty if absent)."""
        return self._data.get("state", {}).get(section, {}) or {}

    def cfg(self, section: str) -> dict[str, Any]:
        """config.<section> as a dict (empty if absent)."""
        return self._data.get("config", {}).get(section, {}) or {}

    def has_state(self, section: str) -> bool:
        return section in self._data.get("state", {})

    @property
    def evse_state(self) -> int | None:
        val = self.st("evse").get("state")
        return int(val) if isinstance(val, (int, float)) else None
