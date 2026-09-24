"""Shared helpers for Free Mobile SMS XA."""

from __future__ import annotations

import logging
import re
from http import HTTPStatus

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL, VERSION

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


def async_get_entry_by_username(
    hass: HomeAssistant, username: str
) -> ConfigEntry | None:
    """Find a config entry by Free Mobile username."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("username") == username:
            return entry
    return None


async def async_send_sms_via_client(hass: HomeAssistant, client, message: str) -> None:
    """Send an SMS and raise a translated HomeAssistantError on failure."""
    try:
        response = await hass.async_add_executor_job(client.send_sms, message)
    except Exception as err:  # noqa: BLE001 - library can raise various errors
        _LOGGER.exception("Free Mobile API request failed")
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="connection_error",
        ) from err

    status = getattr(response, "status_code", None)
    if status == HTTPStatus.OK:
        return
    if status == HTTPStatus.FORBIDDEN:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="invalid_auth",
        )
    if status == HTTPStatus.BAD_REQUEST:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="invalid_message",
        )
    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="api_error",
        translation_placeholders={"status": str(status)},
    )
