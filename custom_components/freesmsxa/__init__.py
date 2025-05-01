# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Support for Free Mobile SMS platform as a notification service in Home Assistant."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .notify import FreeSMSNotificationService, NOTIFY_SCHEMA

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freesmsxa"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Free Mobile SMS from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = entry.data.get(CONF_NAME, f"freesmsxa_{username.replace('.', '_').lower()}")

    try:
        # Create and register the notification service
        notification_service = FreeSMSNotificationService(hass, username, access_token, service_name)
        hass.services.async_register(
            "notify",
            service_name,
            notification_service.async_send_message,
            schema=NOTIFY_SCHEMA,
        )
        _LOGGER.debug("Successfully registered notification service: notify.%s for username %s", service_name, username)

        # Store the service name for unloading
        hass.data[DOMAIN][entry.entry_id] = service_name

        # Add sensor entity
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    except Exception as exc:
        _LOGGER.error("Failed to set up Free Mobile SMS XA for username %s: %s", username, exc)
        return False

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    service_name = hass.data[DOMAIN].pop(entry.entry_id, None)
    if service_name:
        hass.services.async_remove("notify", service_name)
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    return True
