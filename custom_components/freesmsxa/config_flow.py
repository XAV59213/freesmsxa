# custom_components/freesmsxa/config_flow.py
"""Config flow for Free Mobile SMS XA integration."""

from __future__ import annotations

from http import HTTPStatus
import re
import unicodedata
import voluptuous as vol

from freesms import FreeClient

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from . import DOMAIN, CONF_PHONE_NUMBER

def clean_device_name(name: str, username: str) -> str:
    """Clean and normalize a device name."""
    if not name:
        return f"freesmsxa_{username.replace('.', '_').lower()}"
    # Remove accents
    name = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    # Convert to lowercase, replace spaces and special characters with underscores
    name = re.sub(r'[^a-z0-9]', '_', name.lower())
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name).strip('_')
    return name

def validate_phone_number(phone: str) -> str:
    """Validate and normalize a French phone number."""
    # Remove spaces and other non-digit characters except '+'
    cleaned = re.sub(r'[^\d+]', '', phone)
    # Check if it matches French mobile number format
    if re.match(r'^\+33[6-7]\d{8}$', cleaned) or re.match(r'^0[6-7]\d{8}$', cleaned):
        # Convert to international format if needed
        if cleaned.startswith('0'):
            cleaned = '+33' + cleaned[1:]
        return cleaned
    raise vol.Invalid("Numéro de téléphone invalide. Utilisez un format français (ex : +33612345678 ou 0612345678).")

class FreeSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Free Mobile SMS XA."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate device name if provided
            device_name = user_input.get(CONF_NAME)
            device_name = clean_device_name(device_name, user_input[CONF_USERNAME])
            if not device_name:
                errors["name"] = "invalid_service_name"
            else:
                # Check if device name is already used
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_NAME) == device_name:
                        errors["name"] = "service_name_already_configured"
                        break

            # Check if identifier is already configured
            for entry in self._async_current_entries():
                if entry.data[CONF_USERNAME] == user_input[CONF_USERNAME]:
                    errors["username"] = "username_already_configured"
                    break

            # Validate phone number if provided
            phone_number = user_input.get(CONF_PHONE_NUMBER)
            if phone_number:
                try:
                    user_input[CONF_PHONE_NUMBER] = validate_phone_number(phone_number)
                except vol.Invalid:
                    errors["phone_number"] = "invalid_phone_number"

            if not errors:
                # Test credentials with a test SMS
                try:
                    client = FreeClient(user_input[CONF_USERNAME], user_input[CONF_ACCESS_TOKEN])
                    resp = await self.hass.async_add_executor_job(
                        client.send_sms, "Test de configuration Free Mobile SMS XA"
                    )
                    if resp.status_code == HTTPStatus.FORBIDDEN:
                        errors["base"] = "invalid_credentials"
                    elif resp.status_code == HTTPStatus.OK:
                        # Credentials are valid, create entry
                        return self.async_create_entry(
                            title=f"Free Mobile SMS ({user_input[CONF_USERNAME]})",
                            data={
                                CONF_USERNAME: user_input[CONF_USERNAME],
                                CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                                CONF_NAME: device_name,
                                CONF_PHONE_NUMBER: user_input.get(CONF_PHONE_NUMBER),
                            },
                        )
                    else:
                        errors["base"] = "api_error"
                except Exception as exc:
                    _LOGGER.error("Error testing credentials: %s", exc)
                    errors["base"] = "invalid_config"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_ACCESS_TOKEN): cv.string,
                    vol.Optional(CONF_NAME): cv.string,
                    vol.Optional(CONF_PHONE_NUMBER): cv.string,
                }
            ),
            errors=errors,
        )
