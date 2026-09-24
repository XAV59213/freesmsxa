"""Config flow and options for Free Mobile SMS XA."""

from __future__ import annotations

from http import HTTPStatus

from freesms import FreeClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_PHONE_NUMBER,
    CONF_SEND_TEST_SMS,
    CONF_TEST_MESSAGE,
    DEFAULT_TEST_MESSAGE,
    DOMAIN,
)
from .helpers import is_valid_fr_phone


class FreeSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            token = user_input[CONF_ACCESS_TOKEN].strip()
            phone = (user_input.get(CONF_PHONE_NUMBER) or "").strip()
            alias = (user_input.get(CONF_NAME) or "").strip() or username
            send_test = user_input.get(CONF_SEND_TEST_SMS, True)

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            if phone and not is_valid_fr_phone(phone):
                errors[CONF_PHONE_NUMBER] = "invalid_phone_number"
            else:
                try:
                    client = FreeClient(username, token)
                    if send_test:
                        response = await self.hass.async_add_executor_job(
                            client.send_sms, "Configuration du compte OK"
                        )
                        if response.status_code == HTTPStatus.FORBIDDEN:
                            errors["base"] = "invalid_auth"
                        elif response.status_code != HTTPStatus.OK:
                            errors["base"] = "api_error"
                except Exception:  # noqa: BLE001
                    errors["base"] = "connection_error"

            if not errors:
                return self.async_create_entry(
                    title=alias,
                    data={
                        CONF_USERNAME: username,
                        CONF_ACCESS_TOKEN: token,
                        CONF_NAME: alias,
                        CONF_PHONE_NUMBER: phone or None,
                    },
                    options={CONF_TEST_MESSAGE: DEFAULT_TEST_MESSAGE},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_ACCESS_TOKEN): str,
                    vol.Optional(CONF_NAME): str,
                    vol.Optional(CONF_PHONE_NUMBER): str,
                    vol.Optional(CONF_SEND_TEST_SMS, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Allow updating token, alias and phone number."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_ACCESS_TOKEN].strip()
            phone = (user_input.get(CONF_PHONE_NUMBER) or "").strip()
            alias = (user_input.get(CONF_NAME) or "").strip() or entry.data.get(
                CONF_NAME, entry.data[CONF_USERNAME]
            )

            if phone and not is_valid_fr_phone(phone):
                errors[CONF_PHONE_NUMBER] = "invalid_phone_number"
            else:
                try:
                    client = FreeClient(entry.data[CONF_USERNAME], token)
                    response = await self.hass.async_add_executor_job(
                        client.send_sms, "Reconfiguration du compte OK"
                    )
                    if response.status_code == HTTPStatus.FORBIDDEN:
                        errors["base"] = "invalid_auth"
                    elif response.status_code != HTTPStatus.OK:
                        errors["base"] = "api_error"
                except Exception:  # noqa: BLE001
                    errors["base"] = "connection_error"

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    title=alias,
                    data_updates={
                        CONF_ACCESS_TOKEN: token,
                        CONF_NAME: alias,
                        CONF_PHONE_NUMBER: phone or None,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_TOKEN): str,
                    vol.Optional(
                        CONF_NAME, default=entry.data.get(CONF_NAME, "")
                    ): str,
                    vol.Optional(
                        CONF_PHONE_NUMBER,
                        default=entry.data.get(CONF_PHONE_NUMBER) or "",
                    ): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow."""
        return FreeSMSOptionsFlowHandler()


class FreeSMSOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for an existing entry."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TEST_MESSAGE,
                        default=self.config_entry.options.get(
                            CONF_TEST_MESSAGE, DEFAULT_TEST_MESSAGE
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                }
            ),
        )
