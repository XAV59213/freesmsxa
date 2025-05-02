"""Notify platform for Free Mobile SMS XA."""

from __future__ import annotations
import logging
from http import HTTPStatus

from freesms import FreeClient
from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import DOMAIN
from .sensor import update_sensor_state

_LOGGER = logging.getLogger(__name__)

async def async_get_service(hass: HomeAssistant, config: dict, discovery_info: DiscoveryInfoType | None = None) -> BaseNotificationService:
    if discovery_info is None:
        return None
    entry_id = discovery_info["entry_id"]
    data = hass.data[DOMAIN][entry_id]
    return FreeSMSNotificationService(hass, data["username"], data["access_token"])

class FreeSMSNotificationService(BaseNotificationService):
    def __init__(self, hass: HomeAssistant, username: str, access_token: str) -> None:
        self.hass = hass
        self.free_client = FreeClient(username, access_token)
        self._username = username

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"freesmsxa_{self._username}")},
            "name": f"Free Mobile SMS ({self._username})",
            "manufacturer": "Free Mobile",
            "model": "SMS Gateway",
            "sw_version": "1.0",
        }

    def send_message(self, message: str = "", **kwargs) -> None:
        _LOGGER.debug("Sending SMS to %s: %s", self._username, message)
        try:
            resp = self.free_client.send_sms(message)
            if resp.status_code == HTTPStatus.OK:
                _LOGGER.info("SMS sent for %s", self._username)
                update_sensor_state(self.hass, self._username)
            else:
                _LOGGER.warning("Failed to send SMS (%s): %s", self._username, resp.status_code)
        except Exception as exc:
            _LOGGER.error("Error sending SMS to %s: %s", self._username, exc)
