"""Diagnostics for Free Mobile SMS XA."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from . import FreeSMSConfigEntry

TO_REDACT = {CONF_ACCESS_TOKEN, "access_token", "token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FreeSMSConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, without secrets."""
    runtime = entry.runtime_data
    sensor = getattr(runtime, "sensor", None)
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "unique_id": entry.unique_id,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "runtime": {
            "alias": runtime.alias,
            "username": runtime.username,
            "has_phone_number": bool(runtime.phone_number),
            "has_client": runtime.client is not None,
        },
        "sensor": None
        if sensor is None
        else {
            "state": sensor.state,
            "sms_count": sensor.sms_count,
            "sms_today": sensor.sms_today,
            "quota_status": sensor.quota_status,
            "sms_log": sensor.sms_log,
        },
    }
