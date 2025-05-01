# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Support for Free Mobile SMS platform as a notification service in Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_ACCESS_TOKEN, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freesmsxa"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Free Mobile SMS from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = entry.data.get(CONF_NAME, f"freesmsxa_{username.replace('.', '_').lower()}")

    # Store configuration for notify platform
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_USERNAME: username,
        CONF_ACCESS_TOKEN: access_token,
        CONF_NAME: service_name
    }

    # Add sensor entity
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "notify"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    await hass.config_entries.async_unload_platforms(entry, ["sensor", "notify"])
    return True
