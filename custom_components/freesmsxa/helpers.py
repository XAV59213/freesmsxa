"""Shared helpers for Free Mobile SMS XA."""

from __future__ import annotations

import asyncio
import logging
import re
from functools import partial
from typing import TYPE_CHECKING, NoReturn

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import (
    API_RETRY_DELAY,
    API_RETRY_STATUSES,
    API_STATUS_ERRORS,
    API_STATUS_OK,
    API_TIMEOUT,
    DOMAIN,
    DEFAULT_LINE_NAME,
    EVENT_SMS_FAILED,
    EVENT_SMS_SENT,
    LOGGER_NAME,
    MANUFACTURER,
    MODEL,
    SMS_MAX_LENGTH,
    VERSION,
)

from .api import SMSClient

if TYPE_CHECKING:
    from . import FreeSMSConfigEntry


class FreeSMSAuthError(HomeAssistantError):
    """The Free Mobile API rejected the credentials (HTTP 403)."""


_LOGGER = logging.getLogger(__name__)

PHONE_PATTERN = re.compile(r"^(?:\+33|0033|0)[1-9]\d{8}$")


def normalize_phone(phone: str) -> str:
    """Strip spaces, dots and dashes from a phone number."""
    return re.sub(r"[\s.\-]", "", phone or "")


def is_valid_fr_phone(phone: str) -> bool:
    """Return True if the number looks like a French mobile/landline."""
    return bool(PHONE_PATTERN.fullmatch(normalize_phone(phone)))


def build_device_info(username: str, alias: str | None) -> DeviceInfo:
    """Return the shared DeviceInfo for a Free Mobile line."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"freesmsxa_{username}")},
        name=(
            DEFAULT_LINE_NAME
            if not alias or not alias.strip() or alias.strip() in (username, DEFAULT_LINE_NAME)
            else f"Free Mobile SMS ({alias})"
        ),
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


def validate_message(message: str) -> str:
    """Normalize and validate an SMS body before calling the API."""
    text = (message or "").strip()
    if not text:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="empty_message",
        )
    if len(text) > SMS_MAX_LENGTH:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="message_too_long",
            translation_placeholders={"max": str(SMS_MAX_LENGTH)},
        )
    return text


def error_key_for_status(status: int | None) -> str:
    """Map a Free Mobile HTTP status to a translation key."""
    if status is None:
        return "connection_error"
    return API_STATUS_ERRORS.get(int(status), "api_error")


def raise_for_api_status(status: int | None) -> NoReturn:
    """Raise a translated HomeAssistantError for a non-success API status."""
    key = error_key_for_status(status)
    if key == "invalid_auth":
        raise FreeSMSAuthError(translation_domain=DOMAIN, translation_key=key)
    if key == "api_error":
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"status": str(status)},
        )
    raise HomeAssistantError(translation_domain=DOMAIN, translation_key=key)


async def async_send_sms_via_client(hass: HomeAssistant, client: SMSClient, message: str) -> int:
    """Send an SMS. Returns HTTP 200 or raises HomeAssistantError."""
    text = validate_message(message)
    _LOGGER.debug("Calling Free Mobile API, length=%s", len(text))

    last_status: int | None = None
    attempts = 2
    for attempt in range(1, attempts + 1):
        try:
            response = await hass.async_add_executor_job(partial(client.send_sms, text, timeout=API_TIMEOUT))
        except Exception:  # noqa: BLE001 - library can raise various errors
            # requests exceptions can include the full URL with API credentials
            # and the SMS text. Never log or chain that exception for users.
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from None

        last_status = getattr(response, "status_code", None)
        _LOGGER.debug("Free Mobile API status=%s attempt=%s", last_status, attempt)

        if last_status == API_STATUS_OK:
            return API_STATUS_OK

        if last_status in API_RETRY_STATUSES and attempt < attempts:
            _LOGGER.debug(
                "Free Mobile API HTTP %s, retrying in %ss", last_status, API_RETRY_DELAY
            )
            await asyncio.sleep(API_RETRY_DELAY)
            continue
        break

    raise_for_api_status(last_status)


async def async_send_and_record(
    hass: HomeAssistant,
    entry: FreeSMSConfigEntry,
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
        status = await async_send_sms_via_client(hass, client, message)
    except (HomeAssistantError, ServiceValidationError) as err:
        error_key = getattr(err, "translation_key", None) or "api_error"
        if runtime is not None:
            if error_key == "connection_error":
                runtime.record_api_reachability(False)
            elif error_key in {
                "invalid_auth", "invalid_message", "quota_exceeded", "server_error", "api_error"
            }:
                # Receiving an HTTP error still proves transport reachability.
                # It does not prove credentials/quota/delivery are healthy.
                runtime.record_api_reachability(True)
        if isinstance(err, FreeSMSAuthError):
            # Service-call errors do not automatically start config-entry reauth.
            # HA deduplicates any reauth/reconfigure flow already in progress.
            entry.async_start_reauth(hass)
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

    if runtime is not None:
        runtime.record_api_reachability(True)
    if sensor is not None:
        sensor.notify_sent(message)
    hass.bus.async_fire(
        EVENT_SMS_SENT,
        {
            "alias": alias,
            "source": source,
            "message": message,
            "status": status,
        },
    )
