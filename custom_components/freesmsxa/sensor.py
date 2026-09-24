"""Sensors for Free Mobile SMS XA."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import FreeSMSConfigEntry
from .const import SMS_LOG_MAX
from .helpers import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeSMSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SMS sensors."""
    status = FreeSMSSensor(entry)
    count = FreeSMSCountSensor(entry, status)
    today = FreeSMSTodaySensor(entry, status)
    status.bind(count, today)
    entry.runtime_data.sensor = status
    async_add_entities([status, count, today])


class FreeSMSSensor(RestoreEntity, SensorEntity):
    """Status sensor that tracks sent SMS and history."""

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
        self._sms_today = 0
        self._sms_today_date: str | None = None
        self._last_sent: str | None = None
        self._last_error: str | None = None
        self._quota_status = "ok"
        self._sms_log: list[dict] = []
        self._count_entity: FreeSMSCountSensor | None = None
        self._today_entity: FreeSMSTodaySensor | None = None
        self._attr_unique_id = f"freesmsxa_{entry.entry_id}_status"
        self._attr_native_value = "Idle"
        self._attr_device_info = build_device_info(username, alias)
        self._refresh_attributes()

    def bind(self, count: FreeSMSCountSensor, today: FreeSMSTodaySensor) -> None:
        """Attach numeric sensors that mirror these counters."""
        self._count_entity = count
        self._today_entity = today

    @property
    def sms_count(self) -> int:
        return self._sms_count

    @property
    def sms_today(self) -> int:
        self._rollover_today()
        return self._sms_today

    @property
    def quota_status(self) -> str:
        return self._quota_status

    @property
    def sms_log(self) -> list[dict]:
        return list(self._sms_log)

    def _rollover_today(self) -> None:
        today = dt_util.now().date().isoformat()
        if self._sms_today_date != today:
            self._sms_today_date = today
            self._sms_today = 0

    async def async_added_to_hass(self) -> None:
        """Restore counter and log after a restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        attrs = last_state.attributes
        self._sms_count = int(attrs.get("sms_count") or 0)
        self._sms_today = int(attrs.get("sms_today") or 0)
        self._sms_today_date = attrs.get("sms_today_date")
        self._last_sent = attrs.get("last_sent")
        self._last_error = attrs.get("last_error")
        self._quota_status = attrs.get("quota_status") or "ok"
        log = attrs.get("sms_log") or []
        if isinstance(log, list):
            self._sms_log = log[:SMS_LOG_MAX]
        if last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
        self._rollover_today()
        self._refresh_attributes()

    def notify_sent(self, message: str = "") -> None:
        """Record a successfully sent SMS."""
        self._rollover_today()
        self._sms_count += 1
        self._sms_today += 1
        self._last_sent = dt_util.now().isoformat()
        self._last_error = None
        self._quota_status = "ok"
        self._sms_log.insert(
            0,
            {
                "message": message or "SMS envoyé",
                "time": self._last_sent,
                "status": "sent",
                "length": len(message or ""),
            },
        )
        self._sms_log = self._sms_log[:SMS_LOG_MAX]
        self._attr_native_value = "Last sent"
        self._publish()

    def notify_failed(self, message: str, error_key: str) -> None:
        """Record a failed SMS attempt."""
        self._last_error = error_key
        if error_key == "quota_exceeded":
            self._quota_status = "throttled"
            self._attr_native_value = "Quota"
        else:
            self._attr_native_value = "Error"
        self._sms_log.insert(
            0,
            {
                "message": message or "",
                "time": dt_util.now().isoformat(),
                "status": "failed",
                "error": error_key,
                "length": len(message or ""),
            },
        )
        self._sms_log = self._sms_log[:SMS_LOG_MAX]
        self._publish()

    def _publish(self) -> None:
        self._refresh_attributes()
        self.async_write_ha_state()
        if self._count_entity is not None and self._count_entity.hass:
            self._count_entity.async_write_ha_state()
        if self._today_entity is not None and self._today_entity.hass:
            self._today_entity.async_write_ha_state()

    def _refresh_attributes(self) -> None:
        self._attr_extra_state_attributes = {
            "sms_count": self._sms_count,
            "sms_today": self._sms_today,
            "sms_today_date": self._sms_today_date,
            "last_sent": self._last_sent,
            "last_error": self._last_error,
            "quota_status": self._quota_status,
            "alias": self._alias,
            "username": self._username,
            "phone_number": self._phone_number or "Non renseigné",
            "sms_log": self._sms_log,
        }


class FreeSMSCountSensor(RestoreEntity, SensorEntity):
    """Total number of SMS sent by this line."""

    _attr_has_entity_name = True
    _attr_translation_key = "sms_count"
    _attr_icon = "mdi:counter"
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "SMS"

    def __init__(self, entry: FreeSMSConfigEntry, status: FreeSMSSensor) -> None:
        username = entry.data[CONF_USERNAME]
        alias = entry.data.get(CONF_NAME, username)
        self._status = status
        self._attr_unique_id = f"freesmsxa_{entry.entry_id}_sms_count"
        self._attr_device_info = build_device_info(username, alias)

    @property
    def native_value(self) -> int:
        return self._status.sms_count


class FreeSMSTodaySensor(RestoreEntity, SensorEntity):
    """Number of SMS sent today (local time)."""

    _attr_has_entity_name = True
    _attr_translation_key = "sms_today"
    _attr_icon = "mdi:calendar-today"
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "SMS"

    def __init__(self, entry: FreeSMSConfigEntry, status: FreeSMSSensor) -> None:
        username = entry.data[CONF_USERNAME]
        alias = entry.data.get(CONF_NAME, username)
        self._status = status
        self._attr_unique_id = f"freesmsxa_{entry.entry_id}_sms_today"
        self._attr_device_info = build_device_info(username, alias)

    @property
    def native_value(self) -> int:
        return self._status.sms_today
