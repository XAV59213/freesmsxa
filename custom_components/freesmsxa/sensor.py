"""Sensor for Free Mobile SMS XA."""

from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

sensors = {}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    username = entry.data[CONF_USERNAME]
    sensor = FreeSMSSensor(entry.entry_id, username)
    sensors[username] = sensor
    async_add_entities([sensor])

def update_sensor_state(hass: HomeAssistant, username: str):
    if username in sensors:
        sensors[username].notify_sent()

class FreeSMSSensor(SensorEntity):
    def __init__(self, entry_id: str, username: str):
        self._attr_name = f"Free Mobile SMS {username} Status"
        self._attr_unique_id = f"freesmsxa_{entry_id}_status"
        self._attr_icon = "mdi:message-text"
        self._attr_extra_state_attributes = {
            "sms_count": 0,
            "last_sent": None,
            "username": username,
        }
        self._state = "Idle"
        self._username = username
        self._sms_count = 0

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"freesmsxa_{self._username}")},
            "name": f"Free Mobile SMS ({self._username})",
            "manufacturer": "Free Mobile",
            "model": "SMS Gateway",
            "sw_version": "1.0",
        }

    @property
    def state(self):
        return self._state

    def notify_sent(self):
        self._sms_count += 1
        self._attr_extra_state_attributes["sms_count"] = self._sms_count
        self._attr_extra_state_attributes["last_sent"] = datetime.now().isoformat()
        self._state = "Last sent"
        self.async_write_ha_state()
