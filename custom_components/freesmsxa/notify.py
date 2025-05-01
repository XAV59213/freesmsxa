# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Notification platform for Free Mobile SMS XA integration."""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
import logging

from freesms import FreeClient

from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_ACCESS_TOKEN, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> BaseNotificationService | None:
    """Get the Free Mobile SMS XA notification service."""
    _LOGGER.debug("Attempting to set up notify service with discovery_info: %s", discovery_info)
    if discovery_info is None:
        _LOGGER.error("No discovery_info provided for notify service")
        return None

    username = discovery_info[CONF_USERNAME]
    access_token = discovery_info[CONF_ACCESS_TOKEN]
    service_name = discovery_info.get(CONF_NAME, f"freesmsxa_{username.replace('.', '_').lower()}")

    _LOGGER.debug("Setting up notify service: notify.%s for username %s", service_name, username)
    return FreeSMSNotificationService(hass, username, access_token, service_name)

class FreeSMSNotificationService(BaseNotificationService):
    """Implement a notification service for the Free Mobile SMS service."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str, service_name: str) -> None:
        """Initialize the service."""
        self.hass = hass
        self.free_client = FreeClient(username, access_token)
        self.service_name = service_name
        self._username = username

    async def async_send_message(self, message: str, **kwargs: any) -> None:
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

            # Update sensor state
            sensor = next(
                (entity for entity in self.hass.data[DOMAIN].get("sensors", [])
                 if entity.service_name == self.service_name), None
            )
            if sensor:
                sensor.update_state(status, datetime.now().isoformat())

        except Exception as exc:
            status = f"Erreur : {str(exc)}"
            _LOGGER.error("Failed to send SMS to %s: %s", self._username, exc)
            if sensor:
                sensor.update_state(status, datetime.now().isoformat())
