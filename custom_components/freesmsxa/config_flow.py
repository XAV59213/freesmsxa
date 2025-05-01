# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Config flow for Free Mobile SMS XA integration."""

from __future__ import annotations

from http import HTTPStatus
import re
import unicodedata
import voluptuous as vol
import logging

from freesms import FreeClient

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

def clean_service_name(name: str) -> str:
    """Clean and normalize a service name."""
    # Remove accents
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    # Convert to lowercase, replace spaces and special characters with underscores
    name = re.sub(r'[^a-z0-9]', '_', name.lower())
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name).strip('_')
    return name

class FreeSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Free Mobile SMS XA."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate service name if provided
            service_name = user_input.get(CONF_NAME)
            if service_name:
                service_name = clean_service_name(service_name)
                _LOGGER.debug("Normalized service name: %s (original: %s)", service_name, user_input[CONF_NAME])
                if not service_name:
                    errors["name"] = "invalid_service_name"
                else:
                    # Check if service name is already used
                    for entry in self._async_current_entries():
                        if entry.data.get(CONF_NAME) == service_name:
                            errors["name"] = "service_name_already_configured"
                            break

            # Check if username is already configured
            for entry in self._async_current_entries():
                if entry.data[CONF_USERNAME] == user_input[CONF_USERNAME]:
                    errors["username"] = "username_already_configured"
                    break

            if not errors:
                # Test credentials with a test SMS
                try:
                    client = FreeClient(user_input[CONF_USERNAME], user_input[CONF_ACCESS_TOKEN])
                    resp = await self.hass.async_add_executor_job(
                        client.send_sms, "Test de configuration Free Mobile SMS XA"
                    )
                    if resp.status_code == HTTPStatus.FORBIDDEN:
                        errors["base"] = "invalid_credentials"
                    elif resp.status_code == HTTPStatus.OK:
                        # Credentials are valid, create entry
                        _LOGGER.debug("Creating config entry for username %s with service name %s", user_input[CONF_USERNAME], service_name)
                        return self.async_create_entry(
                            title=f"Free Mobile SMS ({user_input[CONF_USERNAME]})",
                            data={
                                CONF_USERNAME: user_input[CONF_USERNAME],
                                CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                                CONF_NAME: service_name,
                            },
                        )
                    else:
                        errors["base"] = "api_error"
                except Exception as exc:
                    _LOGGER.error("Error testing credentials for username %s: %s", user_input[CONF_USERNAME], exc)
                    errors["base"] = "invalid_config"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_ACCESS_TOKEN): cv.string,
                    vol.Optional(CONF_NAME): cv.string,
                }
            ),
            errors=errors,
        )
