"""Data update coordinator polling the PinPaw backend.

Location data arrives two ways:
- REST polling every ``DEFAULT_SCAN_INTERVAL`` (authoritative, complete state).
- Optional WebSocket push (near real-time) that optimistically updates
  coordinates and triggers a debounced REST refresh for authoritative state.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PinPawApiError, PinPawAuthError, PinPawClient
from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_USE_WEBSOCKET,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_WEBSOCKET,
    DOMAIN,
)
from .websocket import PinPawWebSocket

_LOGGER = logging.getLogger(__name__)


class PinPawCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Fetches all pets once per interval and indexes them by pet id."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: PinPawClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self.client = client
        self._ws: PinPawWebSocket | None = None

        if entry.data.get(CONF_USE_WEBSOCKET, DEFAULT_USE_WEBSOCKET):
            self._ws = PinPawWebSocket(
                base_url=entry.data[CONF_BASE_URL],
                token=entry.data[CONF_API_TOKEN],
                session=async_get_clientsession(hass),
                on_message=self._handle_push,
            )

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            pets = await self.client.async_get_pets()
        except PinPawAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except PinPawApiError as err:
            raise UpdateFailed(f"Error fetching PinPaw data: {err}") from err

        return {pet["id"]: pet for pet in pets if "id" in pet}

    def start_websocket(self) -> None:
        """Start the push listener (call after the first REST refresh)."""
        if self._ws:
            self._ws.start()

    async def stop_websocket(self) -> None:
        if self._ws:
            await self._ws.stop()

    async def _handle_push(self, payload: dict[str, Any]) -> None:
        """Apply a pushed ``{"positions": [...]}`` frame.

        Frames carrying ``petId`` (PinPaw's normalised shape) are merged in
        place for instant updates. Anything else — frames without a ``petId`` —
        falls back to a debounced authoritative refresh.
        """
        if not self.data:
            return

        positions = payload.get("positions") or []
        updated = False
        needs_refresh = False

        for pos in positions:
            pet_id = pos.get("petId")
            if pet_id in self.data:
                self.data[pet_id].setdefault("latestPosition", {}).update(
                    {
                        k: pos[k]
                        for k in ("latitude", "longitude", "batteryLevel", "charging", "online")
                        if k in pos
                    }
                )
                updated = True
            else:
                # Unknown shape (no petId) — let REST reconcile.
                needs_refresh = True

        if updated:
            self.async_set_updated_data(self.data)
        if needs_refresh:
            await self.async_request_refresh()
