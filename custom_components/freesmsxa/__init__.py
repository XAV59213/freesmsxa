# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Support for Free Mobile SMS platform as a notification device in Home Assistant."""

from __future__ import annotations

from http import HTTPStatus
import logging
import voluptuous as vol

from freesms import FreeClient

from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntryType, async_get as async_get_device_registry
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freesmsxa"
CONF_PHONE_NUMBER = "phone_number"

# Schema for the notify service
NOTIFY_SCHEMA = vol.Schema({
    vol.Required("message"): cv.string
})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Free Mobile SMS from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    name_phone = entry.data.get(CONF_NAME, f"freesmsxa_{username.replace('.', '_').lower()}")
    service_name = f"notify_{name_phone}"

    # Create a device in the device registry
    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"freesmsxa_{username}")},
        name=f"Free Mobile SMS ({name_phone})",
        manufacturer="Free Mobile",
        model="SMS Gateway",
        sw_version="1.0",
        entry_type=DeviceEntryType.SERVICE,
    )

    # Create and register the notification service
    notification_service = FreeSMSNotificationService(hass, username, access_token, service_name)
    hass.services.async_register(
        "notify",
        service_name,
        notification_service.async_send_message,
        schema=NOTIFY_SCHEMA,
    )
    _LOGGER.debug("Registered notification service: notify.%s", service_name)

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
        _LOGGER.debug("Unregistered notification service: notify.%s", service_name)

    # Unload sensor platform
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    return True

class FreeSMSNotificationService(BaseNotificationService):
    """Implement a notification service for the Free Mobile SMS device."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str, service_name: str) -> None:
        """Initialize the notification service."""
        self.hass = hass
        self.free_client = FreeClient(username, access_token)
        self.service_name = service_name
        self._username = username

    async def async_send_message(self, message: str, **kwargs: ConfigType) -> None:
        """Send a message to the Free Mobile user cell."""
        _LOGGER.debug("Attempting to send SMS to %s with message: %s", self._username, message)
        try:
            resp = await self.hass.async_add_executor_job(
                self.free_client.send_sms, message
            )

            status = "OK"
            if resp.status_code == HTTPStatus.BAD_REQUEST:
                status = "Erreur : Paramètre manquant"
                _LOGGER.error("At least one parameter is missing")
            elif resp.status_code == HTTPStatus.PAYMENT_REQUIRED:
                status = "Erreur : Limite d'envoi atteinte"
                _LOGGER.error("Too many SMS sent in a short time")
            elif resp.status_code == HTTPStatus.FORBIDDEN:
                status = "Erreur : Identifiants incorrects"
                _LOGGER.error("Wrong username or password")
            elif resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
                status = "Erreur : Serveur indisponible"
                _LOGGER.error("Server error, try later")

        except Exception as exc:
            status = f"Erreur : {str(exc)}"
            _LOGGER.error("Failed to send SMS to %s: %s", self._username, exc)

        # Update sensor state via event
        hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            {
                "username": self._username,
                "status": status,
                "last_sent": hass.loop.time(),
            }
        )
