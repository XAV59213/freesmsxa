"""Init file for Free Mobile SMS XA."""

from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import DeviceEntryType, async_get as async_get_device_registry

from .notify import FreeSMSNotificationService

_LOGGER = logging.getLogger(__name__)
DOMAIN = "freesmsxa"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = entry.data.get("name") or f"freesmsxa_{username.replace('.', '_').lower()}"

    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"freesmsxa_{username}")},
        name=f"Free Mobile SMS ({username})",
        manufacturer="Free Mobile",
        model="SMS Gateway",
        sw_version="1.0",
        entry_type=DeviceEntryType.SERVICE,
    )

    notification_service = FreeSMSNotificationService(hass, username, access_token)

    async def handle_send_message(service_call: ServiceCall) -> None:
        message = service_call.data.get("message")
        if not message:
            _LOGGER.error("Missing required 'message' in service call data")
            return
        result = await notification_service.async_send_message(message)
        hass.bus.async_fire(f"{DOMAIN}_status_update", result)

    hass.services.async_register(
        "notify",
        service_name,
        handle_send_message,
    )

    async def handle_send_sms(call: ServiceCall) -> None:
        target = call.data.get("target")
        message = call.data.get("message")
        if not target or not message:
            _LOGGER.error("Missing 'target' or 'message'")
            return
        if not hass.services.has_service("notify", target):
            _LOGGER.error("Service notify.%s not found", target)
            return
        await hass.services.async_call("notify", target, {"message": message}, blocking=True)

    hass.services.async_register(DOMAIN, "send_sms", handle_send_sms)
    _LOGGER.info("Registered generic service freesmsxa.send_sms")

    hass.data[DOMAIN][entry.entry_id] = {
        "service_name": service_name,
    }

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN].pop(entry.entry_id, {})
    service_name = data.get("service_name")
    if service_name:
        hass.services.async_remove("notify", service_name)
    return True
