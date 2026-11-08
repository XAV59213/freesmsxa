"""Sensors for Free Mobile SMS XA."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import CONF_NAME, CONF_USERNAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import FreeSMSConfigEntry
from .const import API_STATUS_ERRORS, SMS_LOG_MAX
from .helpers import build_device_info


_RESTORABLE_ERRORS = frozenset(API_STATUS_ERRORS.values()) | {
    "connection_error", "api_error", "empty_message", "message_too_long"
}


def _restored_count(value: object) -> int:
    """Accept persisted integer counters, not malformed or private strings."""
    if not isinstance(value, (int, str)) or isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        return 0


def _restored_time(value: object) -> str | None:
    """Do not republish arbitrary legacy strings as timestamps."""
    if isinstance(value, str) and dt_util.parse_datetime(value) is not None:
        return value
    return None


def _restored_error(value: object) -> str | None:
    """Only integration error keys belong in persisted public metadata."""
    return value if isinstance(value, str) and value in _RESTORABLE_ERRORS else None


PARALLEL_UPDATES = 0


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
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["Idle", "Last sent", "Quota", "Error"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    # Keep personal data out of the recorder / history database.
    _unrecorded_attributes = frozenset({"sms_log"})

    def __init__(self, entry: FreeSMSConfigEntry) -> None:
        username = entry.data[CONF_USERNAME]
        alias = entry.data.get(CONF_NAME, username)
        self._runtime = entry.runtime_data
        self._removed = False
        self._username = username
        self._alias = alias
        self._phone_number = entry.runtime_data.phone_number
        self._sms_count = 0
        self._sms_today = 0
        self._sms_today_date: str | None = None
        self._last_sent: str | None = None
        self._last_error: str | None = None
        self._quota_status = "ok"
        self._sms_log: list[dict[str, Any]] = []
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
    def available(self) -> bool:
        """Only this remote-status view becomes unavailable on observed failure.

        Locally recorded counters remain valid. Sending actions stay available
        so an explicit retry can establish recovery without a background SMS.
        None means no observation since setup, not a known connection failure.
        """
        return super().available and self._runtime.api_reachable is not False

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
    def sms_log(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._sms_log]

    def _rollover_today(self) -> None:
        today = dt_util.now().date().isoformat()
        if self._sms_today_date != today:
            self._sms_today_date = today
            self._sms_today = 0

    async def async_added_to_hass(self) -> None:
        """Restore counter and log after a restart."""
        await super().async_added_to_hass()
        self._removed = False
        self.async_on_remove(self._mark_removed)
        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        attrs = last_state.attributes
        self._sms_count = _restored_count(attrs.get("sms_count"))
        self._sms_today = _restored_count(attrs.get("sms_today"))
        self._sms_today_date = attrs.get("sms_today_date")
        self._last_sent = _restored_time(attrs.get("last_sent"))
        self._last_error = _restored_error(attrs.get("last_error"))
        quota = attrs.get("quota_status")
        self._quota_status = quota if quota in ("ok", "throttled") else "ok"
        log = attrs.get("sms_log") or []
        self._sms_log = []
        if isinstance(log, list):
            # Old snapshots are untrusted input: field-name filtering alone can
            # retain a URL/message inside error/time or an unknown nested field.
            for item in log[:SMS_LOG_MAX]:
                if not isinstance(item, dict) or item.get("status") not in ("sent", "failed"):
                    continue
                clean: dict[str, Any] = {"status": item["status"]}
                if (timestamp := _restored_time(item.get("time"))) is not None:
                    clean["time"] = timestamp
                if "length" in item:
                    clean["length"] = _restored_count(item["length"])
                if (error := _restored_error(item.get("error"))) is not None:
                    clean["error"] = error
                self._sms_log.append(clean)
        if last_state.state in self._attr_options:
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
                "time": dt_util.now().isoformat(),
                "status": "failed",
                "error": error_key,
                "length": len(message or ""),
            },
        )
        self._sms_log = self._sms_log[:SMS_LOG_MAX]
        self._publish()

    def _mark_removed(self) -> None:
        """An in-flight send may finish after this entity has been removed."""
        self._removed = True

    def _publish(self) -> None:
        self._refresh_attributes()
        # The status entity can be disabled or not added yet. Keep the runtime
        # counters usable without writing a state for a detached entity.
        if getattr(self, "hass", None) is not None and not self._removed:
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
            "api_reachable": self._runtime.api_reachable,
            "sms_log": self._sms_log,
        }


class FreeSMSCountSensor(RestoreEntity, SensorEntity):
    """Total number of SMS sent by this line."""

    _attr_has_entity_name = True
    _attr_translation_key = "sms_count"
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
