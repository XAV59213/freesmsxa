"""Init for Free Mobile SMS XA."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import async_get as async_get_device_registry, DeviceEntryType

from .const import DOMAIN, CONF_PHONE_NUMBER

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Free Mobile SMS XA integration."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_send_sms(call: ServiceCall) -> None:
        """Handle the send_sms service call."""
        target = call.data.get("target")
        message = call.data.get("message")
        if not target or not message:
            _LOGGER.error("Missing target or message in send_sms service call")
            return
        if target not in hass.services.services.get("notify", {}):
            _LOGGER.error("Invalid notify service: %s", target)
            return
        try:
            await hass.services.async_call("notify", target, {"message": message})
            _LOGGER.info("SMS sent via %s: %s", target, message)
        except Exception as exc:
            _LOGGER.error("Failed to send SMS via %s: %s", target, exc)

    # Register the send_sms service
    hass.services.async_register(DOMAIN, "send_sms", handle_send_sms)
    return True

def mask_token(token):
    return token[:4] + "****"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "username": entry.data["username"],
        "access_token": entry.data["access_token"],
        "phone_number": entry.data.get(CONF_PHONE_NUMBER),
    }

    username = entry.data["username"]
    token = mask_token(entry.data["access_token"])
    phone = entry.data.get(CONF_PHONE_NUMBER, "inconnu")
    alias = entry.data.get(CONF_NAME, username)

    device_name = f"{alias} – Token: {token} – Tel: {phone}"

    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"freesmsxa_{username}")},
        name=device_name,
        manufacturer="Free Mobile",
        model="SMS Gateway",
        sw_version="1.0",
        entry_type=DeviceEntryType.SERVICE
    )

    await hass.config_entries.async_forward_entry_setups(entry, ["notify", "sensor", "button"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_unload_platforms(entry, ["notify", "sensor", "button"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
