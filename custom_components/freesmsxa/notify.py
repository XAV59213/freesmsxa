# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Notification service for Free Mobile SMS XA integration."""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
import logging

from freesms import FreeClient, FreeSMSError
import voluptuous as vol

from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Define the schema for the notify service
NOTIFY_SCHEMA = vol.Schema({
    vol.Required("message"): cv.string
})

class FreeSMSNotificationService(BaseNotificationService):
    """Implement a notification service for the Free Mobile SMS service."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str, service_name: str) -> None:
        """Initialize the service."""
        self.hass = hass
        self.free_client = FreeClient(username, access_token)
        self.service_name = service_name
        self._username = username

    async def async_send_message(self, message: str, **kwargs) -> None:
        """Send a message to the Free Mobile user cell."""
        _LOGGER.debug("Attempting to send SMS to %s with message: %s", self._username, message)
        try:
            # Send SMS using the FreeClient
            resp = await self.hass.async_add_executor_job(
                self.free_client.send_sms, message
            )

            # Handle response status
            status = "OK"
            if resp.status_code == HTTPStatus.BAD_REQUEST:
                status = "Erreur : Paramètre manquant"
                _LOGGER.error("At least one parameter is missing for %s", self._username)
            elif resp.status_code == HTTPStatus.PAYMENT_REQUIRED:
                status = "Erreur : Limite d'envoi atteinte"
                _LOGGER.error("Too many SMS sent in a short time for %s", self._username)
            elif resp.status_code == HTTPStatus.FORBIDDEN:
                status = "Erreur : Identifiants incorrects"
                _LOGGER.error("Wrong username or password for %s", self._username)
            elif resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
                status = "Erreur : Serveur indisponible"
                _LOGGER.error("Server error for %s, try later", self._username)

            # Update sensor state
            sensor = self.hass.data.get("freesmsxa", {}).get(f"{self._username}_sensor")
            if sensor:
                sensor.update_state(status, datetime.now().isoformat())
            else:
                _LOGGER.warning("No sensor found for service %s", self.service_name)

        except FreeSMSError as exc:
            status = f"Erreur API : {str(exc)}"
            _LOGGER.error("Free Mobile API error for %s: %s", self._username, exc)
            if sensor:
                sensor.update_state(status, datetime.now().isoformat())
        except Exception as exc:
            status = f"Erreur inattendue : {str(exc)}"
            _LOGGER.error("Unexpected error sending SMS to %s: %s", self._username, exc)
            if sensor:
                sensor.update_state(status, datetime.now().isoformat())
