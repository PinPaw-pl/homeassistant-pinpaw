"""Config flow for the PinPaw integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PinPawApiError, PinPawAuthError, PinPawClient
from .const import (
    API_TOKEN_PREFIX,
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_USE_WEBSOCKET,
    DEFAULT_BASE_URL,
    DEFAULT_USE_WEBSOCKET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_USE_WEBSOCKET, default=DEFAULT_USE_WEBSOCKET): bool,
    }
)


class PinPawConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the PinPaw config flow: paste a personal access token."""

    VERSION = 1

    async def _validate(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, str]]:
        """Validate input. Returns (entry_data, account, errors)."""
        errors: dict[str, str] = {}
        token = user_input[CONF_API_TOKEN].strip()
        base_url = user_input[CONF_BASE_URL].strip()

        if not token.startswith(API_TOKEN_PREFIX):
            errors[CONF_API_TOKEN] = "invalid_token_format"
            return None, {}, errors

        client = PinPawClient(base_url, token, async_get_clientsession(self.hass))
        try:
            account = await client.async_validate()
        except PinPawAuthError:
            errors["base"] = "invalid_auth"
            return None, {}, errors
        except PinPawApiError:
            errors["base"] = "cannot_connect"
            return None, {}, errors

        data = {
            CONF_BASE_URL: base_url,
            CONF_API_TOKEN: token,
            CONF_USE_WEBSOCKET: user_input.get(
                CONF_USE_WEBSOCKET, DEFAULT_USE_WEBSOCKET
            ),
        }
        return data, account, errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data, account, errors = await self._validate(user_input)
            if data is not None:
                await self.async_set_unique_id(str(account.get("id")))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=account.get("username") or "PinPaw",
                    data=data,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change server URL / token / WebSocket without re-adding."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            data, account, errors = await self._validate(user_input)
            if data is not None:
                # Make sure the token still points at the same PinPaw account.
                await self.async_set_unique_id(str(account.get("id")))
                self._abort_if_unique_id_mismatch(reason="account_mismatch")
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )
