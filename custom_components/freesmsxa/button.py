"""Button entity to test SMS sending."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from http import HTTPStatus
from freesms import FreeClient
from .const import DOMAIN
from .sensor import update_sensor_state

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    entry_id = entry.entry_id
    test_message = entry.options.get("test_message", "Test SMS envoyé depuis Home Assistant")
    async_add_entities([TestSMSButton(username, access_token, entry_id, test_message)])

class TestSMSButton(ButtonEntity):
    def __init__(self, username: str, token: str, entry_id: str, test_message: str):
        self._username = username
        self._token = token
        self._entry_id = entry_id
        self._test_message = test_message
        self._attr_name = f"Test SMS ({username})"
        self._attr_unique_id = f"freesmsxa_test_button_{entry_id}"
        self._attr_icon = "mdi:message-alert-outline"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"freesmsxa_{self._username}")},
            "name": f"Free Mobile SMS ({self._username})",
            "manufacturer": "Free Mobile",
            "model": "SMS Gateway",
            "sw_version": "1.0",
        }

    async def async_press(self) -> None:
        from freesms import FreeClient
        client = FreeClient(self._username, self._token)
        resp = await self.hass.async_add_executor_job(client.send_sms, self._test_message)
        if resp.status_code == HTTPStatus.OK:
            update_sensor_state(self.hass, self._username, self._test_message)
            self._attr_icon = "mdi:check-circle-outline"
        else:
            self._attr_icon = "mdi:alert-circle-outline"
        self.async_write_ha_state()
