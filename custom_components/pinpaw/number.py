"""Number entity to control the device reporting interval."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PinPawConfigEntry
from .entity import PinPawEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PinPawConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        PinPawIntervalNumber(coordinator, pet_id) for pet_id in coordinator.data
    )


class PinPawIntervalNumber(PinPawEntity, NumberEntity):
    """Reporting interval in seconds, written back to the device."""

    _attr_translation_key = "tracking_interval"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 10
    _attr_native_max_value = 3600
    _attr_native_step = 10
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator, pet_id: int) -> None:
        super().__init__(coordinator, pet_id)
        self._attr_unique_id = f"{pet_id}_tracking_interval"

    @property
    def native_value(self) -> float | None:
        return self.pet.get("trackingInterval")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_set_tracking_interval(
            self._pet_id, int(value)
        )
        await self.coordinator.async_request_refresh()
