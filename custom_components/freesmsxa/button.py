"""Button entity to test SMS sending."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_NAME, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FreeSMSConfigEntry
from .const import CONF_TEST_MESSAGE, DEFAULT_TEST_MESSAGE
from .helpers import async_send_and_record, build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeSMSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the test SMS button."""
    async_add_entities([TestSMSButton(entry)])


class TestSMSButton(ButtonEntity):
    """Button that sends the configured test SMS."""

    _attr_has_entity_name = True
    _attr_translation_key = "test_sms"
    _attr_icon = "mdi:message-alert-outline"

    def __init__(self, entry: FreeSMSConfigEntry) -> None:
        self._entry = entry
        username = entry.data[CONF_USERNAME]
        alias = entry.data.get(CONF_NAME, username)
        self._username = username
        self._attr_unique_id = f"freesmsxa_test_button_{entry.entry_id}"
        self._attr_device_info = build_device_info(username, alias)

    async def async_press(self) -> None:
        """Send the current test message from options."""
        message = self._entry.options.get(CONF_TEST_MESSAGE, DEFAULT_TEST_MESSAGE)
        await async_send_and_record(self.hass, self._entry, message, source="button")
        self._attr_icon = "mdi:check-circle-outline"
        self.async_write_ha_state()
