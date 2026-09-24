"""Sensor for Free Mobile SMS XA."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import FreeSMSConfigEntry
from .helpers import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeSMSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SMS status sensor."""
    sensor = FreeSMSSensor(entry)
    entry.runtime_data.sensor = sensor
    async_add_entities([sensor])


class FreeSMSSensor(RestoreEntity, SensorEntity):
    """Status sensor that tracks sent SMS."""

    _attr_has_entity_name = True
    _attr_translation_key = "sms_status"
    _attr_icon = "mdi:message-text"
    _attr_should_poll = False

    def __init__(self, entry: FreeSMSConfigEntry) -> None:
        username = entry.data[CONF_USERNAME]
        alias = entry.data.get(CONF_NAME, username)
        self._username = username
        self._alias = alias
        self._phone_number = entry.runtime_data.phone_number
        self._sms_count = 0
        self._last_sent: str | None = None
        self._sms_log: list[dict] = []
        self._attr_unique_id = f"freesmsxa_{entry.entry_id}_status"
        self._attr_native_value = "Idle"
        self._attr_device_info = build_device_info(username, alias)
        self._refresh_attributes()

    async def async_added_to_hass(self) -> None:
        """Restore counter and log after a restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        attrs = last_state.attributes
        self._sms_count = int(attrs.get("sms_count") or 0)
        self._last_sent = attrs.get("last_sent")
        log = attrs.get("sms_log") or []
        if isinstance(log, list):
            self._sms_log = log[:10]
        if last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
        self._refresh_attributes()

    def notify_sent(self, message: str = "") -> None:
        """Record a successfully sent SMS."""
        self._sms_count += 1
        self._last_sent = dt_util.now().isoformat()
        self._sms_log.insert(
            0, {"message": message or "SMS envoyé", "time": self._last_sent}
        )
        self._sms_log = self._sms_log[:10]
        self._attr_native_value = "Last sent"
        self._refresh_attributes()
        self.async_write_ha_state()

    def _refresh_attributes(self) -> None:
        self._attr_extra_state_attributes = {
            "sms_count": self._sms_count,
            "last_sent": self._last_sent,
            "alias": self._alias,
            "username": self._username,
            "phone_number": self._phone_number or "Non renseigné",
            "sms_log": self._sms_log,
        }
