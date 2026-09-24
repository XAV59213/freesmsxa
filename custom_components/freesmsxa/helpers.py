"""Shared helpers for Free Mobile SMS XA."""

from __future__ import annotations

import logging
import re
from http import HTTPStatus

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import (
    DOMAIN,
    EVENT_SMS_FAILED,
    EVENT_SMS_SENT,
    LOGGER_NAME,
    MANUFACTURER,
    MODEL,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)

PHONE_PATTERN = re.compile(r"^(?:\+33|0033|0)[1-9]\d{8}$")


def normalize_phone(phone: str) -> str:
    """Strip spaces, dots and dashes from a phone number."""
    return re.sub(r"[\s.\-]", "", phone or "")


def is_valid_fr_phone(phone: str) -> bool:
    """Return True if the number looks like a French mobile/landline."""
    return bool(PHONE_PATTERN.fullmatch(normalize_phone(phone)))


def build_device_info(username: str, alias: str) -> DeviceInfo:
    """Return the shared DeviceInfo for a Free Mobile line."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"freesmsxa_{username}")},
        name=f"Free Mobile SMS ({alias})",
        manufacturer=MANUFACTURER,
        model=MODEL,
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
    )


def apply_debug_logging(enabled: bool) -> None:
    """Raise or restore the integration logger level."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if enabled else logging.INFO)
    _LOGGER.info("Debug logging %s", "enabled" if enabled else "disabled")


def async_get_entry_by_username(
    hass: HomeAssistant, username: str
) -> ConfigEntry | None:
    """Find a config entry by Free Mobile username."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("username") == username:
            return entry
    return None


def _error_key_for_status(status: int | None) -> str:
    if status == HTTPStatus.FORBIDDEN:
        return "invalid_auth"
    if status == HTTPStatus.BAD_REQUEST:
        return "invalid_message"
    if status == HTTPStatus.PAYMENT_REQUIRED:
        return "quota_exceeded"
    return "api_error"


async def async_send_sms_via_client(hass: HomeAssistant, client, message: str) -> None:
    """Send an SMS and raise a translated HomeAssistantError on failure."""
    _LOGGER.debug("Calling Free Mobile API, length=%s", len(message or ""))
    try:
        response = await hass.async_add_executor_job(client.send_sms, message)
    except Exception as err:  # noqa: BLE001 - library can raise various errors
        _LOGGER.exception("Free Mobile API request failed")
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="connection_error",
        ) from err

    status = getattr(response, "status_code", None)
    _LOGGER.debug("Free Mobile API status=%s", status)
    if status == HTTPStatus.OK:
        return
    key = _error_key_for_status(status)
    if key == "api_error":
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"status": str(status)},
        )
    raise HomeAssistantError(translation_domain=DOMAIN, translation_key=key)


async def async_send_and_record(
    hass: HomeAssistant,
    entry: ConfigEntry,
    message: str,
    *,
    source: str = "notify",
) -> None:
    """Send an SMS and update the status sensor / events."""
    runtime = getattr(entry, "runtime_data", None)
    sensor = getattr(runtime, "sensor", None) if runtime else None
    alias = getattr(runtime, "alias", None) if runtime else entry.title
    client = runtime.client if runtime is not None else None
    if client is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="connection_error",
        )

    try:
        await async_send_sms_via_client(hass, client, message)
    except HomeAssistantError as err:
        error_key = getattr(err, "translation_key", None) or "api_error"
        if sensor is not None:
            sensor.notify_failed(message, error_key)
        hass.bus.async_fire(
            EVENT_SMS_FAILED,
            {
                "alias": alias,
                "source": source,
                "message": message,
                "error": error_key,
            },
        )
        raise

    if sensor is not None:
        sensor.notify_sent(message)
    hass.bus.async_fire(
        EVENT_SMS_SENT,
        {"alias": alias, "source": source, "message": message},
    )
