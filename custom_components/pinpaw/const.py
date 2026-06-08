"""Constants for the PinPaw integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "pinpaw"

# Config entry keys
CONF_BASE_URL = "base_url"
CONF_API_TOKEN = "api_token"
CONF_USE_WEBSOCKET = "use_websocket"

# Enable near real-time push via WebSocket in addition to REST polling.
DEFAULT_USE_WEBSOCKET = True

# A PinPaw personal access token always carries this prefix.
API_TOKEN_PREFIX = "ppw_pat_"

DEFAULT_BASE_URL = "https://api.pinpaw.io"

# How often the coordinator polls the backend for fresh pet state.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

# Battery level (%) below which the "battery low" binary sensor turns on.
LOW_BATTERY_THRESHOLD = 20
