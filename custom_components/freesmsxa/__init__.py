"""Support for Free Mobile SMS platform as a notification service in Home Assistant."""

from __future__ import annotations

from http import HTTPStatus
import logging

from freesms import FreeClient

from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Free Mobile SMS from a config entry."""
    hass.data.setdefault("freesmsxa", {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    
    # Create a unique service name based on the username
    service_name = f"freesmsxa_{username.replace('.', '_').lower()}"
    
    # Create and register the notification service
    hass.services.async_register(
        "notify",
        service_name,
        FreeSMSNotificationService(hass, username, access_token).async_send_message,
        schema=None,
    )
    
    # Store the service name for unloading
    hass.data["freesmsxa"][entry.entry_id] = service_name
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    service_name = hass.data["freesmsxa"].pop(entry.entry_id, None)
    if service_name:
        hass.services.async_remove("notify", service_name)
    return True

class FreeSMSNotificationService(BaseNotificationService):
    """Implement a notification service for the Free Mobile SMS service."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str) -> None:
        """Initialize the service."""
        self.hass = hass
        self.free_client = FreeClient(username, access_token)

    async def async_send_message(self, message: str, **kwargs: any) -> None:
        """Send a message to the Free Mobile user cell."""
        try:
            resp = await self.hass.async_add_executor_job(
                self.free_client.send_sms, message
            )

            if resp.status_code == HTTPStatus.BAD_REQUEST:
                _LOGGER.error("At least one parameter is missing")
            elif resp.status_code == HTTPStatus.PAYMENT_REQUIRED:
                _LOGGER.error("Too many SMS sent in a short time")
            elif resp.status_code == HTTPStatus.FORBIDDEN:
                _LOGGER.error("Wrong username or password")
            elif resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
                _LOGGER.error("Server error, try later")
        except Exception as exc:
            _LOGGER.error("Failed to send SMS: %s", exc)
