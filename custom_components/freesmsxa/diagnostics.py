"""Diagnostics for Free Mobile SMS XA."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import FreeSMSConfigEntry
from .const import CONF_DEBUG, CONF_PHONE_NUMBER, CONF_TEST_MESSAGE

TO_REDACT = {
    CONF_ACCESS_TOKEN,
    "access_token",
    "token",
    "username",
    "unique_id",
    "title",
    "phone_number",
    "message",
    "sms_log",
    "name",
    "alias",
    CONF_TEST_MESSAGE,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FreeSMSConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, without secrets."""
    runtime = getattr(entry, "runtime_data", None)
    sensor = getattr(runtime, "sensor", None)
    api_reachable = getattr(runtime, "api_reachable", None)
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "unique_id": entry.unique_id,
                # Only export known configuration fields. Legacy or future arbitrary
                # fields must not accidentally introduce private values or keys.
                "data": {
                    key: entry.data[key]
                    for key in (
                        CONF_USERNAME,
                        CONF_ACCESS_TOKEN,
                        CONF_NAME,
                        CONF_PHONE_NUMBER,
                    )
                    if key in entry.data
                },
                "options": {
                    CONF_DEBUG: bool(entry.options.get(CONF_DEBUG, False)),
                    CONF_TEST_MESSAGE: entry.options.get(CONF_TEST_MESSAGE),
                },
            },
            TO_REDACT,
        ),
        "runtime": async_redact_data(
            {
                "alias": getattr(runtime, "alias", None),
                "username": getattr(runtime, "username", None),
                "has_phone_number": bool(getattr(runtime, "phone_number", None)),
                "has_client": getattr(runtime, "client", None) is not None,
                "api_reachable": api_reachable if isinstance(api_reachable, bool) else None,
            },
            TO_REDACT,
        ),
        "sensor": None
        if sensor is None
        else {
            # RestoreEntity can restore a state written by an older version.
            # Do not export an arbitrary restored string in a public diagnostic.
            "state": sensor.state
            if sensor.state in {"Idle", "Last sent", "Quota", "Error"}
            else "unknown",
            "sms_count": sensor.sms_count,
            "sms_today": sensor.sms_today,
            "quota_status": sensor.quota_status
            if sensor.quota_status in {"ok", "throttled"}
            else "unknown",
        },
    }
