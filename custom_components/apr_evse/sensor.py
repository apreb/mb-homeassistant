"""Sensor platform for APR EVSE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfInformation,
    UnitOfLength,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    EVSE_STATE_MAP,
    EVSE_STATUS_OPTIONS,
)
from .coordinator import AprEvseCoordinator
from .entity import AprEvseEntity

METER_STATE_OPTIONS = ["ok", "nok", "dis"]


def _num(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) else None


def _sum_phases(section: dict[str, Any], prefix: str = "p_l") -> float | None:
    vals = [section.get(f"{prefix}{i}") for i in (1, 2, 3)]
    present = [v for v in vals if isinstance(v, (int, float))]
    return float(sum(present)) if present else None


def _charging(entity: "AprEvseSensor") -> bool:
    # Gate session sensors on the live evse state; deltas never retract `charge`.
    return entity.evse_state == 3 and entity.has_state("charge")


@dataclass(frozen=True, kw_only=True)
class AprEvseSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a value extractor and optional availability gate."""

    value_fn: Callable[["AprEvseSensor"], StateType]
    available_fn: Callable[["AprEvseSensor"], bool] | None = None


SENSORS: tuple[AprEvseSensorEntityDescription, ...] = (
    AprEvseSensorEntityDescription(
        key="status",
        translation_key="evse_status",
        device_class=SensorDeviceClass.ENUM,
        options=EVSE_STATUS_OPTIONS,
        value_fn=lambda e: EVSE_STATE_MAP.get(e.evse_state) if e.evse_state is not None else None,
    ),
    AprEvseSensorEntityDescription(
        key="charging_power",
        translation_key="charging_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _sum_phases(e.st("energy")),
    ),
    AprEvseSensorEntityDescription(
        key="session_energy",
        translation_key="session_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda e: _num(e.st("charge").get("energyl")),
        available_fn=_charging,
    ),
    AprEvseSensorEntityDescription(
        key="session_duration",
        translation_key="session_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda e: _num(e.st("charge").get("time")),
        available_fn=_charging,
    ),
    AprEvseSensorEntityDescription(
        key="session_cost",
        translation_key="session_cost",
        icon="mdi:cash",
        suggested_display_precision=2,
        value_fn=lambda e: _num(e.st("charge").get("cost")),
        available_fn=_charging,
    ),
    AprEvseSensorEntityDescription(
        key="range_added",
        translation_key="range_added",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda e: _num(e.st("charge").get("kmh")),
        available_fn=_charging,
    ),
    AprEvseSensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _num(e.st("energy").get("v_l1")),
    ),
    AprEvseSensorEntityDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda e: _sum_phases(e.st("energy"), "i_l"),
    ),
    AprEvseSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _num(e.st("temperature").get("t")),
    ),
    AprEvseSensorEntityDescription(
        key="grid_power",
        translation_key="grid_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _sum_phases(e.st("grid")),
    ),
    AprEvseSensorEntityDescription(
        key="grid_voltage",
        translation_key="grid_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _num(e.st("grid").get("v_l1")),
    ),
    AprEvseSensorEntityDescription(
        key="grid_current",
        translation_key="grid_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda e: _sum_phases(e.st("grid"), "i_l"),
    ),
    AprEvseSensorEntityDescription(
        key="price",
        translation_key="price",
        native_unit_of_measurement="EUR/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=lambda e: _num(e.st("tariff").get("price")),
    ),
    AprEvseSensorEntityDescription(
        key="car_soc",
        translation_key="car_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _num(e.st("car").get("soc")),
        available_fn=lambda e: e.has_state("car"),
    ),
    AprEvseSensorEntityDescription(
        key="powerwall_soc",
        translation_key="powerwall_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _num(e.st("pw").get("soc")),
        available_fn=lambda e: e.has_state("pw"),
    ),
    AprEvseSensorEntityDescription(
        key="pv_power",
        translation_key="pv_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda e: _num(e.st("pw").get("p_pv")),
        available_fn=lambda e: e.has_state("pw"),
    ),
    # --- diagnostics --------------------------------------------------------
    AprEvseSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda e: _num(e.st("wifi").get("rssi")),
    ),
    AprEvseSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda e: _num(e.st("sys").get("uptime")),
    ),
    AprEvseSensorEntityDescription(
        key="free_ram",
        translation_key="free_ram",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda e: _num(e.st("sys").get("ram_f")),
    ),
    AprEvseSensorEntityDescription(
        key="fs_free",
        translation_key="fs_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda e: _num(e.st("sys").get("fs_f")),
    ),
    AprEvseSensorEntityDescription(
        key="grid_meter_state",
        translation_key="grid_meter_state",
        device_class=SensorDeviceClass.ENUM,
        options=METER_STATE_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda e: e.st("grid").get("state"),
    ),
    AprEvseSensorEntityDescription(
        key="energy_meter_state",
        translation_key="energy_meter_state",
        device_class=SensorDeviceClass.ENUM,
        options=METER_STATE_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda e: e.st("energy").get("state"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AprEvseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AprEvseSensor(coordinator, desc) for desc in SENSORS)


class AprEvseSensor(AprEvseEntity, SensorEntity):
    """A single description-driven sensor."""

    entity_description: AprEvseSensorEntityDescription

    def __init__(
        self,
        coordinator: AprEvseCoordinator,
        description: AprEvseSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self)

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self.entity_description.available_fn is not None:
            return self.entity_description.available_fn(self)
        return True
