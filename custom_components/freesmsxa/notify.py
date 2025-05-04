"""Notify entity for Free Mobile SMS XA."""

import logging
from http import HTTPStatus

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME, CONF_NAME
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .sensor import update_sensor_state
from freesms import FreeClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    alias = entry.data.get(CONF_NAME, username).lower()  # Normaliser en minuscules
    async_add_entities([
        FreeSMSNotifyEntity(hass, username, access_token, alias)
    ])

class FreeSMSNotifyEntity(NotifyEntity):
    def __init__(self, hass: HomeAssistant, username: str, access_token: str, alias: str):
        self.hass = hass
        self._username = username
        self._access_token = access_token
        self._alias = alias
        self.free_client = FreeClient(username, access_token)
        self._attr_name = f"{self._alias}_sms"  # Génère un nom comme "papa_sms"
        self._attr_translation_key = self._alias  # Utilise l'alias comme clé de traduction (ex: "papa")

    @property
    def unique_id(self) -> str:
        return f"freesmsxa_notify_{self._username}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"freesmsxa_{self._username}")},
            "name": f"Free Mobile SMS ({self._alias})",
            "manufacturer": "Free Mobile",
            "model": "SMS Gateway",
            "sw_version": "1.0",
        }

    async def async_send_message(self, message: str = "", **kwargs) -> None:
        _LOGGER.debug("Sending SMS to %s: %s", self._username, message)
        try:
            resp = await self.hass.async_add_executor_job(self.free_client.send_sms, message)
            if resp.status_code == HTTPStatus.OK:
                _LOGGER.info("SMS sent for %s", self._username)
                update_sensor_state(self.hass, self._username, message)
            else:
                _LOGGER.warning("Failed to send SMS to %s (%s)", self._username, resp.status_code)
        except Exception as exc:
            _LOGGER.error("Error sending SMS to %s: %s", self._username, exc)
