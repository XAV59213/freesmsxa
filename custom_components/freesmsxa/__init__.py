"""Init for Free Mobile SMS XA."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .const import (
    ATTR_MESSAGE,
    ATTR_TARGET,
    CONF_DEBUG,
    CONF_PHONE_NUMBER,
    DOMAIN,
    PLATFORMS,
    SERVICE_SEND_SMS,
)
from .api import FreeClient, SMSClient
from .frontend import JSModuleRegistration
from .helpers import apply_debug_logging, build_device_info
from .migration import async_migrate_notify_name
from .schema import Required, Schema

if TYPE_CHECKING:
    from .sensor import FreeSMSSensor

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class FreeSMSRuntimeData:
    """Runtime data attached to a config entry."""

    client: SMSClient
    username: str
    alias: str
    phone_number: str | None
    sensor: FreeSMSSensor | None = field(default=None)
    # Last observed transport reachability, not live delivery capability.
    api_reachable: bool | None = None

    def record_api_reachability(self, reachable: bool) -> None:
        """Record completed attempts without polling or disabling retry commands."""
        previous = self.api_reachable
        self.api_reachable = reachable
        if previous is reachable:
            return
        if not reachable:
            _LOGGER.info("Free Mobile API connection unavailable")
        elif previous is False:
            _LOGGER.info("Free Mobile API connection restored")


type FreeSMSConfigEntry = ConfigEntry[FreeSMSRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Free Mobile SMS XA integration."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_send_sms(call: ServiceCall) -> None:
        """Handle the send_sms service call."""
        target = str(call.data[ATTR_TARGET]).strip()
        message = call.data[ATTR_MESSAGE]

        if target.startswith("notify."):
            service_name = target.split(".", 1)[1]
            entity_id = target
        else:
            service_name = target
            entity_id = f"notify.{target}"

        if hass.services.has_service("notify", service_name):
            await hass.services.async_call(
                "notify", service_name, {"message": message}, blocking=True
            )
            return

        if hass.states.get(entity_id) is not None and hass.services.has_service(
            "notify", "send_message"
        ):
            await hass.services.async_call(
                "notify",
                "send_message",
                {"entity_id": entity_id, "message": message},
                blocking=True,
            )
            return

        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_target",
            translation_placeholders={"target": target},
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_SMS,
        handle_send_sms,
        schema=Schema(
            {
                Required(ATTR_TARGET): cv.string,
                Required(ATTR_MESSAGE): cv.string,
            }
        ),
    )
    await JSModuleRegistration(hass).async_register()
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FreeSMSConfigEntry) -> bool:
    """Set up a config entry."""
    username = entry.data[CONF_USERNAME]
    alias = entry.data.get(CONF_NAME, username)
    phone_number = entry.data.get(CONF_PHONE_NUMBER)
    client = FreeClient(username, entry.data[CONF_ACCESS_TOKEN])

    apply_debug_logging(bool(entry.options.get(CONF_DEBUG, False)))

    entry.runtime_data = FreeSMSRuntimeData(
        client=client,
        username=username,
        alias=alias,
        phone_number=phone_number,
    )

    device_registry = async_get_device_registry(hass)
    device_info = build_device_info(username, alias)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=device_info["identifiers"],
        name=device_info["name"],
        manufacturer=device_info["manufacturer"],
        model=device_info["model"],
        sw_version=device_info["sw_version"],
        entry_type=device_info["entry_type"],
    )

    async_migrate_notify_name(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FreeSMSConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
