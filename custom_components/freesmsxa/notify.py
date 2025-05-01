# custom_components/freesmsxa/notify.py
"""Notification service for Free Mobile SMS XA integration."""

from __future__ import annotations

from http import HTTPStatus
import logging
import voluptuous as vol

from freesms import FreeClient, FreeSMSError
from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema for the notify service
NOTIFY_SCHEMA = vol.Schema({
    vol.Required("message"): cv.string
})

class FreeSMSNotificationService(BaseNotificationService):
    """Implement a notification service for the Free Mobile SMS device."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str) -> None:
        """Initialize the notification service."""
        self.hass = hass
        self.free_client = FreeClient(username, access_token)
        self._username = username

    @property
    def device_info(self):
        """Return device information to link this service to a device."""
        return {
            "identifiers": {(DOMAIN, f"freesmsxa_{self._username}")},
            "name": f"Free Mobile SMS ({self._username})",
            "manufacturer": "Free Mobile",
            "model": "SMS Gateway",
            "sw_version": "1.0",
        }

    async def async_send_message(self, message: str, **kwargs) -> None:
        """Send a message to the Free Mobile user cell."""
        _LOGGER.debug("Sending SMS to %s with message: %s", self._username, message)
        try:
            resp = await self.hass.async_add_executor_job(
                self.free_client.send_sms, message
            )

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

        except FreeSMSError as exc:
            status = f"Erreur API : {str(exc)}"
            _LOGGER.error("Free Mobile API error for %s: %s", self._username, exc)
        except Exception as exc:
            status = f"Erreur inattendue : {str(exc)}"
            _LOGGER.error("Unexpected error sending SMS to %s: %s", self._username, exc)

        # Fire event to update sensor
        self.hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            {
                "username": self._username,
                "status": status,
                "last_sent": self.hass.loop.time(),
            }
        )
