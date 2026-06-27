"""Select platform: charge mode and schedule."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_MODE,
    CMD_SCHEDULE,
    DOMAIN,
    MODE_OPTIONS,
    SCHEDULE_OPTIONS,
)
from .coordinator import AprEvseCoordinator
from .entity import AprEvseEntity


@dataclass(frozen=True, kw_only=True)
class AprEvseSelectEntityDescription(SelectEntityDescription):
    """Maps an integer state field to/from a list of option slugs."""

    command_key: str
    state_field: str  # field inside state.constrains


SELECTS: tuple[AprEvseSelectEntityDescription, ...] = (
    AprEvseSelectEntityDescription(
        key="charge_mode",
        translation_key="charge_mode",
        options=MODE_OPTIONS,
        command_key=CMD_MODE,
        state_field="mode",
    ),
    AprEvseSelectEntityDescription(
        key="schedule",
        translation_key="schedule",
        options=SCHEDULE_OPTIONS,
        command_key=CMD_SCHEDULE,
        state_field="scheduler",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AprEvseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AprEvseSelect(coordinator, desc) for desc in SELECTS)


class AprEvseSelect(AprEvseEntity, SelectEntity):
    """A single description-driven select."""

    entity_description: AprEvseSelectEntityDescription

    def __init__(
        self,
        coordinator: AprEvseCoordinator,
        description: AprEvseSelectEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        idx = self.st("constrains").get(self.entity_description.state_field)
        options = self.entity_description.options
        if isinstance(idx, int) and 0 <= idx < len(options):
            return options[idx]
        return None

    async def async_select_option(self, option: str) -> None:
        idx = self.entity_description.options.index(option)
        await self.coordinator.api.async_control(
            {self.entity_description.command_key: idx}
        )
        await self.coordinator.async_request_refresh()
