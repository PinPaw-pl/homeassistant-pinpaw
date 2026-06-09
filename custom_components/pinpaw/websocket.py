"""WebSocket listener for near real-time position push.

This supplements the REST polling in the coordinator. The PinPaw backend
proxies device updates over ``/api/socket?jwt=<token>``; the same personal
access token used for REST is accepted on the WebSocket handshake.

The stream is heterogeneous: the first frame is PinPaw's normalised
``{"positions": [{petId, latitude, ...}]}`` and later frames may omit ``petId``.
We optimistically apply what we can parse and let the coordinator pull
authoritative state via a (debounced) REST refresh.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Reconnect backoff bounds (seconds).
_MIN_BACKOFF = 2
_MAX_BACKOFF = 60


class PinPawWebSocket:
    """Maintains a WebSocket connection and forwards position frames."""

    def __init__(
        self,
        base_url: str,
        token: str,
        session: aiohttp.ClientSession,
        on_message: Callable[[dict], Awaitable[None]],
    ) -> None:
        # http(s):// -> ws(s)://
        ws_base = base_url.rstrip("/")
        if ws_base.startswith("https"):
            ws_base = "wss" + ws_base[5:]
        elif ws_base.startswith("http"):
            ws_base = "ws" + ws_base[4:]
        self._url = f"{ws_base}/api/socket?jwt={token}"
        self._session = session
        self._on_message = on_message
        self._task: asyncio.Task | None = None
        self._closing = False

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._closing = True
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        backoff = _MIN_BACKOFF
        while not self._closing:
            try:
                async with self._session.ws_connect(self._url, heartbeat=30) as ws:
                    _LOGGER.debug("PinPaw WebSocket connected")
                    backoff = _MIN_BACKOFF
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._dispatch(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the listener alive
                _LOGGER.debug("PinPaw WebSocket error: %s", err)

            if self._closing:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)

    async def _dispatch(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(payload, dict) and "positions" in payload:
            await self._on_message(payload)
