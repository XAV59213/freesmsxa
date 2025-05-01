# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Support for Free Mobile SMS platform as a notification device in Home Assistant."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntryType, async_get as async_get_device_registry
from homeassistant.helpers.typing import ConfigType

from .notify import FreeSMSNotificationService

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freesmsxa"
CONF_PHONE_NUMBER = "phone_number"

# Schema for the notify service
NOTIFY_SCHEMA = vol.Schema({
    vol.Required("message"): str
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Free Mobile SMS from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = f"freesmsxa_{username.replace('.', '_').lower()}"

    # Create a device in the device registry
    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"freesmsxa_{username}")},
        name=f"Free Mobile SMS ({username})",
        manufacturer="Free Mobile",
        model="SMS Gateway",
        sw_version="1.0",
        entry_type=DeviceEntryType.SERVICE,
    )

    # Create and register the notification service
    notification_service = FreeSMSNotificationService(hass, username, access_token)
    async def handle_send_message(service_call: ServiceCall) -> None:
        """Handle the service call to send a message."""
        try:
            # Convert ReadOnlyDict to mutable dict
            data = NOTIFY_SCHEMA(dict(service_call.data))
            message = data["message"]
        except vol.Invalid as exc:
            _LOGGER.error("Invalid service call data: %s", exc)
            return

        result = await notification_service.async_send_message(message)
        hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            result
        )

    hass.services.async_register(
        "notify",
        service_name,
        handle_send_message,
        schema=NOTIFY_SCHEMA,
    )
    _LOGGER.info("Registered notification service: notify.%s with schema: %s", service_name, NOTIFY_SCHEMA)

    # Store the service name for unloading
    hass.data[DOMAIN][entry.entry_id] = {
        "service_name": service_name,
    }

    # Set up sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].pop(entry.entry_id, {})
    service_name = data.get("service_name")
    if service_name:
        hass.services.async_remove("notify", service_name)
        _LOGGER.debug("Unregistered notification service: %s", service_name)

    # Unload sensor platform
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    return True
