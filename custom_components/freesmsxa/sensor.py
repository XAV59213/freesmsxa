# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Sensor platform for Free Mobile SMS XA integration."""

from __future__ import annotations

from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_ACCESS_TOKEN, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = entry.data.get(CONF_NAME, f"freesmsxa_{username.replace('.', '_').lower()}")
    sensor = FreeSMSStatusSensor(hass, username, access_token, service_name, entry.entry_id)
    async_add_entities([sensor])
    hass.data[DOMAIN].setdefault("sensors", []).append(sensor)

class FreeSMSStatusSensor(SensorEntity):
    """Sensor to display the status of the Free Mobile SMS API."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str, service_name: str, entry_id: str) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._username = username
        self._access_token = access_token
        self.service_name = service_name
        self._state = "Inconnu"
        self._sms_count = 0
        self._last_sent = None
        self._attr_unique_id = f"freesmsxa_{entry_id}_status"
        self._attr_name = f"Free Mobile SMS {username} Status"
        self._attr_icon = "mdi:cellphone-message"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_extra_state_attributes = {
            "last_sent": None,
            "sms_count": 0
        }

    def update_state(self, status: str, last_sent: str | None = None) -> None:
        """Update the sensor state and attributes."""
        self._state = status
        if last_sent:
            self._last_sent = last_sent
            self._sms_count += 1
            self._attr_extra_state_attributes = {
                "last_sent": self._last_sent,
                "sms_count": self._sms_count
            }
        self.async_write_ha_state()

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self._state
