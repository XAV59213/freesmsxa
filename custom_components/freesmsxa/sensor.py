"""Sensor for Free Mobile SMS XA."""

from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_PHONE_NUMBER

sensors = {}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    username = entry.data[CONF_USERNAME]
    phone_number = entry.data.get(CONF_PHONE_NUMBER)
    alias = entry.data.get(CONF_NAME, username)
    sensor = FreeSMSSensor(entry.entry_id, username, phone_number, alias)
    sensors[username] = sensor
    async_add_entities([sensor])

def update_sensor_state(hass: HomeAssistant, username: str):
    if username in sensors:
        sensors[username].notify_sent()

class FreeSMSSensor(SensorEntity):
    def __init__(self, entry_id: str, username: str, phone_number: str | None, alias: str):
        self._attr_name = f"Free Mobile SMS {alias} Status"
        self._attr_unique_id = f"freesmsxa_{entry_id}_status"
        self._attr_icon = "mdi:message-text"
        self._username = username
        self._alias = alias
        self._phone_number = phone_number
        self._sms_count = 0
        self._last_sent = None
        self._state = "Idle"

        self._attr_extra_state_attributes = {
            "sms_count": self._sms_count,
            "last_sent": self._last_sent,
            "alias": self._alias,
            "username": self._username,
            "phone_number": self._phone_number or "Non renseigné",
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"freesmsxa_{self._username}")},
            "name": f"Free Mobile SMS ({self._alias})",
            "manufacturer": "Free Mobile",
            "model": "SMS Gateway",
            "sw_version": "1.0",
        }

    @property
    def state(self):
        return self._state

    def notify_sent(self):
        self._sms_count += 1
        self._last_sent = datetime.now().isoformat()
        self._state = "Last sent"
        self._attr_extra_state_attributes.update({
            "sms_count": self._sms_count,
            "last_sent": self._last_sent,
        })
        self.async_write_ha_state()
