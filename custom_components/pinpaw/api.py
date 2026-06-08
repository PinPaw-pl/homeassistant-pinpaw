"""Thin async client for the PinPaw public API.

Only the endpoints needed by the Home Assistant integration are wrapped.
Authentication uses a long-lived personal access token (``ppw_pat_…``)
sent as a Bearer credential.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class PinPawApiError(Exception):
    """Generic API failure."""


class PinPawAuthError(PinPawApiError):
    """Raised when the token is rejected (HTTP 401/403)."""


class PinPawClient:
    """Minimal client wrapping the PinPaw REST API."""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = api_token
        self._session = session

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method, url, headers=self._headers, **kwargs
            ) as resp:
                if resp.status in (401, 403):
                    raise PinPawAuthError(f"Authentication failed ({resp.status})")
                if resp.status >= 400:
                    body = await resp.text()
                    raise PinPawApiError(f"{method} {path} -> {resp.status}: {body}")
                if resp.status == 204:
                    return None
                return await resp.json()
        except aiohttp.ClientError as err:
            raise PinPawApiError(f"Network error calling {path}: {err}") from err

    async def async_validate(self) -> dict[str, Any]:
        """Verify the token by fetching the current user. Used by config flow."""
        return await self._request("GET", "/api/auth/me")

    async def async_get_pets(self) -> list[dict[str, Any]]:
        """Return all pets with device status, latest position and interval.

        ``GET /api/pets`` already includes ``deviceStatus``, ``latestPosition``
        (lat/lon, batteryLevel, charging, online) and ``trackingInterval``.
        """
        return await self._request("GET", "/api/pets")

    async def async_set_tracking_interval(self, pet_id: int, seconds: int) -> None:
        """Push a new reporting interval to the device."""
        await self._request(
            "PUT",
            f"/api/pets/{pet_id}/tracking-interval",
            json={"trackingInterval": seconds},
        )
