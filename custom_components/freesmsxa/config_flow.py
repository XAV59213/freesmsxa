"""Config flow and options for Free Mobile SMS XA."""

from __future__ import annotations
import voluptuous as vol
from http import HTTPStatus
from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from freesms import FreeClient

from .const import DOMAIN, CONF_PHONE_NUMBER

class FreeSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                client = FreeClient(user_input[CONF_USERNAME], user_input[CONF_ACCESS_TOKEN])
                response = await self.hass.async_add_executor_job(
                    client.send_sms, "Test Free Mobile SMS XA"
                )
                if response.status_code == HTTPStatus.FORBIDDEN:
                    errors["base"] = "invalid_auth"
                elif response.status_code != HTTPStatus.OK:
                    errors["base"] = "api_error"
                else:
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME, user_input[CONF_USERNAME]),
                        data=user_input,
                    )
            except Exception:
                errors["base"] = "connection_error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_ACCESS_TOKEN): str,
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_PHONE_NUMBER): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FreeSMSOptionsFlowHandler(config_entry)

class FreeSMSOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_NAME, default=self.config_entry.data.get(CONF_NAME, "")): str,
                vol.Optional(CONF_PHONE_NUMBER, default=self.config_entry.data.get(CONF_PHONE_NUMBER, "")): str,
            })
        )
