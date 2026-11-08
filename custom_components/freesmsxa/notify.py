"""Notify entity for Free Mobile SMS XA."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import NotifyEntity
from homeassistant.const import CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FreeSMSConfigEntry
from .helpers import async_send_and_record, build_device_info

_LOGGER = logging.getLogger(__name__)

# Queue commands on this platform to avoid concurrent requests per entry.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeSMSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the notify entity."""
    async_add_entities([FreeSMSNotifyEntity(entry)])


class FreeSMSNotifyEntity(NotifyEntity):
    """Notify entity that sends SMS through Free Mobile."""

    _attr_has_entity_name = True
    _attr_translation_key = "sms"

    def __init__(self, entry: FreeSMSConfigEntry) -> None:
        self._entry = entry
        username = entry.data[CONF_USERNAME]
        alias = entry.data.get(CONF_NAME, username)
        self._username = username
        self._attr_unique_id = f"freesmsxa_notify_{username}"
        self._attr_device_info = build_device_info(username, alias)

    async def async_send_message(self, message: str = "", title: str | None = None, **kwargs: Any) -> None:
        """Send an SMS and record it on the status sensor."""
        _LOGGER.debug("Sending SMS")
        await async_send_and_record(self.hass, self._entry, message, source="notify")
        _LOGGER.debug("SMS sent")
