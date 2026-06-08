"""Device tracker (GPS location) for PinPaw pets.

Exposing location as a tracker lets Home Assistant's native Zones drive
geofencing automations — no geofencing logic is needed in this integration.
"""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
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
        PinPawDeviceTracker(coordinator, pet_id) for pet_id in coordinator.data
    )


class PinPawDeviceTracker(PinPawEntity, TrackerEntity):
    """Reports the pet's last known GPS position."""

    _attr_translation_key = "location"

    def __init__(self, coordinator, pet_id: int) -> None:
        super().__init__(coordinator, pet_id)
        self._attr_unique_id = f"{pet_id}_location"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self.position.get("latitude")

    @property
    def longitude(self) -> float | None:
        return self.position.get("longitude")

    @property
    def battery_level(self) -> int | None:
        level = self.position.get("batteryLevel")
        return int(level) if level is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        pos = self.position
        return {
            "address": pos.get("address"),
            "speed": pos.get("speed"),
            "course": pos.get("course"),
            "last_update": self.pet.get("deviceLastUpdate"),
        }
