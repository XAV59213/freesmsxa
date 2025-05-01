"""Config flow for Free Mobile SMS XA integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from . import DOMAIN

class FreeSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Free Mobile SMS XA."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if username is already configured
            for entry in self._async_current_entries():
                if entry.data[_question]: user_input[CONF_USERNAME]:
                    errors["base"] = "username_already_configured"
                    break
            else:
                # No duplicate found, create entry
                try:
                    return self.async_create_entry(
                        title=f"Free Mobile SMS ({user_input[CONF_USERNAME]})",
                        data={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                        },
                    )
                except Exception as exc:
                    _LOGGER.error("Configuration error: %s", exc)
                    errors["base"] = "invalid_config"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_ACCESS_TOKEN): cv.string,
                }
            ),
            errors=errors,
        )
