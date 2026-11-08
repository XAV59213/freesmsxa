"""Config flow and options for Free Mobile SMS XA."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import FreeSMSConfigEntry

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    API_STATUS_OK,
    API_TIMEOUT,
    CONF_DEBUG,
    CONF_PHONE_NUMBER,
    CONF_SEND_TEST_SMS,
    CONF_TEST_MESSAGE,
    DEFAULT_TEST_MESSAGE,
    DEFAULT_LINE_NAME,
    DOMAIN,
)
from .api import FreeClient
from .schema import Optional, Required, Schema
from .helpers import error_key_for_status, is_valid_fr_phone


def _map_status_error(status: int | None) -> str | None:
    if status == API_STATUS_OK:
        return None
    return error_key_for_status(status)


class FreeSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            token = user_input[CONF_ACCESS_TOKEN].strip()
            phone = (user_input.get(CONF_PHONE_NUMBER) or "").strip()
            alias = (user_input.get(CONF_NAME) or "").strip() or DEFAULT_LINE_NAME
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
                            partial(client.send_sms, "Configuration du compte OK", timeout=API_TIMEOUT)
                        )
                        mapped = _map_status_error(response.status_code)
                        if mapped:
                            errors["base"] = mapped
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
                    options={
                        CONF_TEST_MESSAGE: DEFAULT_TEST_MESSAGE,
                        CONF_DEBUG: False,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=Schema(
                {
                    Required(CONF_USERNAME): str,
                    Required(CONF_ACCESS_TOKEN): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                    Optional(CONF_NAME): str,
                    Optional(CONF_PHONE_NUMBER): str,
                    Optional(CONF_SEND_TEST_SMS, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
                        partial(client.send_sms, "Reconfiguration du compte OK", timeout=API_TIMEOUT)
                    )
                    mapped = _map_status_error(response.status_code)
                    if mapped:
                        errors["base"] = mapped
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
            data_schema=Schema(
                {
                    Required(CONF_ACCESS_TOKEN): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                    Optional(
                        CONF_NAME, default=entry.data.get(CONF_NAME, "")
                    ): str,
                    Optional(
                        CONF_PHONE_NUMBER,
                        default=entry.data.get(CONF_PHONE_NUMBER) or "",
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Recover credentials for the existing line, never create another entry."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate a replacement token only after explicit form submission.

        This API cannot validate silently: submission sends one real validation
        SMS in production. Opening the form or loading an entry never sends one.
        The username is fixed to the existing entry so the line cannot change.
        """
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = str(user_input[CONF_ACCESS_TOKEN]).strip()
            try:
                client = FreeClient(entry.data[CONF_USERNAME], token)
                response = await self.hass.async_add_executor_job(
                    partial(client.send_sms, "Réauthentification du compte OK", timeout=API_TIMEOUT)
                )
                mapped = _map_status_error(response.status_code)
                if mapped:
                    errors["base"] = mapped
            except Exception:  # noqa: BLE001 - never expose request URLs/secrets
                errors["base"] = "connection_error"
            if not errors:
                await self.async_set_unique_id(entry.data[CONF_USERNAME])
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_ACCESS_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=Schema({
                Required(CONF_ACCESS_TOKEN): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: FreeSMSConfigEntry) -> FreeSMSOptionsFlowHandler:
        """Return the options flow."""
        return FreeSMSOptionsFlowHandler()


class FreeSMSOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle options for an existing entry."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=Schema(
                {
                    Optional(
                        CONF_TEST_MESSAGE,
                        default=self.config_entry.options.get(
                            CONF_TEST_MESSAGE, DEFAULT_TEST_MESSAGE
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                    Optional(
                        CONF_DEBUG,
                        default=self.config_entry.options.get(CONF_DEBUG, False),
                    ): bool,
                }
            ),
        )
