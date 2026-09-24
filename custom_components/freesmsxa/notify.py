"""Notify entity for Free Mobile SMS XA."""

from __future__ import annotations

import logging

from homeassistant.components.notify import NotifyEntity
from homeassistant.const import CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FreeSMSConfigEntry
from .helpers import async_send_and_record, build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeSMSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the notify entity."""
    async_add_entities([FreeSMSNotifyEntity(entry)])


class FreeSMSNotifyEntity(NotifyEntity):
    """Notify entity that sends SMS through Free Mobile."""

    _attr_has_entity_name = False

    def __init__(self, entry: FreeSMSConfigEntry) -> None:
        self._entry = entry
        username = entry.data[CONF_USERNAME]
        alias = entry.data.get(CONF_NAME, username)
        self._username = username
        self._attr_name = alias
        self._attr_unique_id = f"freesmsxa_notify_{username}"
        self._attr_device_info = build_device_info(username, alias)

    async def async_send_message(self, message: str = "", **kwargs) -> None:
        """Send an SMS and record it on the status sensor."""
        _LOGGER.debug("Sending SMS to %s: %s", self._username, message)
        await async_send_and_record(self.hass, self._entry, message, source="notify")
        _LOGGER.info("SMS sent for %s", self._username)
