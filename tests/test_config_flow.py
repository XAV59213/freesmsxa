from unittest.mock import patch
import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from custom_components.freesmsxa.config_flow import FreeSMSConfigFlow, DOMAIN

@pytest.mark.asyncio
async def test_config_flow_success(hass):
    """Test successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "freesms.FreeClient.send_sms",
        return_value=type("Response", (), {"status_code": 200})()
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "12345678",
                "access_token": "test_token",
                "name": "mon_telephone"
            }
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Free Mobile SMS (12345678)"
    assert result["data"] == {
        "username": "12345678",
        "access_token": "test_token",
        "name": "mon_telephone"
    }
