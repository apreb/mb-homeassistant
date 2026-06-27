"""Binary sensor platform for APR EVSE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AprEvseCoordinator
from .entity import AprEvseEntity


def _vehicle_connected(e: "AprEvseBinarySensor") -> bool | None:
    s = e.evse_state
    if s is None:
        return None
    return 2 <= s <= 14  # plugged states + fault states (exclude sleep/disabled)


def _charging(e: "AprEvseBinarySensor") -> bool | None:
    return None if e.evse_state is None else e.evse_state == 3


def _fault(e: "AprEvseBinarySensor") -> bool | None:
    s = e.evse_state
    return None if s is None else 4 <= s <= 14


@dataclass(frozen=True, kw_only=True)
class AprEvseBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Binary sensor description with an is_on extractor."""

    is_on_fn: Callable[["AprEvseBinarySensor"], bool | None]


BINARY_SENSORS: tuple[AprEvseBinarySensorEntityDescription, ...] = (
    AprEvseBinarySensorEntityDescription(
        key="vehicle_connected",
        translation_key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        is_on_fn=_vehicle_connected,
    ),
    AprEvseBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        is_on_fn=_charging,
    ),
    AprEvseBinarySensorEntityDescription(
        key="fault",
        translation_key="fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=_fault,
    ),
    AprEvseBinarySensorEntityDescription(
        key="mqtt_connected",
        translation_key="mqtt_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_on_fn=lambda e: e.st("mqtt").get("state") == "connected",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AprEvseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AprEvseBinarySensor(coordinator, desc) for desc in BINARY_SENSORS
    )


class AprEvseBinarySensor(AprEvseEntity, BinarySensorEntity):
    """A single description-driven binary sensor."""

    entity_description: AprEvseBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: AprEvseCoordinator,
        description: AprEvseBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self)
