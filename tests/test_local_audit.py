"""Audit-only probes: real HA classes, mocked services/executor; never sends an SMS."""
import sys
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch
import json
from pathlib import Path
import pytest

import homeassistant  # Initialize HA compatibility shims before importing the integration.

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from custom_components import freesmsxa as integration
from custom_components.freesmsxa import helpers, config_flow, diagnostics, sensor, button, notify
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.const import CONF_USERNAME, CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import AbortFlow

@pytest.fixture(autouse=True)
def deny_network():
    # Any accidental request fails locally before I/O.
    with patch("requests.get", side_effect=AssertionError("NETWORK FORBIDDEN")):
        yield

@pytest.fixture
def entry():
    e = NS(entry_id="audit-entry", title="Private Alias", unique_id="12345678",
           data={"username":"12345678", "access_token":"SECRET_TOKEN", "name":"Private Alias", "phone_number":"0612345678"},
           options={"test_message":"PRIVATE_TEST_BODY", "debug":False})
    e.runtime_data = integration.FreeSMSRuntimeData(client=Mock(),username="12345678",alias="Private Alias",phone_number="0612345678")
    e.add_update_listener=Mock(return_value=Mock())
    e.async_on_unload=Mock()
    return e

@pytest.mark.parametrize("phone,valid", [("06 12 34 56 78",True),("+33612345678",True),("0033612345678",True),("123",False),("abc",False)])
def test_phone(phone,valid):
    assert helpers.is_valid_fr_phone(phone) is valid

@pytest.mark.parametrize("message,key", [("", "empty_message"),(" ","empty_message"),("x"*1001,"message_too_long")])
def test_message_rejects(message,key):
    with pytest.raises(ServiceValidationError) as err: helpers.validate_message(message)
    assert err.value.translation_key == key

def test_message_trims_and_limit():
    assert helpers.validate_message(" hello ") == "hello"
    assert len(helpers.validate_message("x"*1000)) == 1000

@pytest.mark.parametrize("status,key", [(None,"connection_error"),(400,"invalid_message"),(402,"quota_exceeded"),(403,"invalid_auth"),(500,"server_error"),(418,"api_error")])
def test_status_errors(status,key):
    with pytest.raises(HomeAssistantError) as err: helpers.raise_for_api_status(status)
    assert err.value.translation_key == key

@pytest.mark.asyncio
@pytest.mark.parametrize("codes,expected,calls", [([200],None,1),([500,200],None,2),([500,500],"server_error",2),([403],"invalid_auth",1),([None],"connection_error",1),([418],"api_error",1)])
async def test_send_status(codes,expected,calls):
    hass=NS(async_add_executor_job=AsyncMock(side_effect=[NS(status_code=x) for x in codes]))
    with patch.object(helpers.asyncio,"sleep",new=AsyncMock()):
        if expected:
            with pytest.raises(HomeAssistantError) as err: await helpers.async_send_sms_via_client(hass,Mock(),"hello")
            assert err.value.translation_key==expected
        else: assert await helpers.async_send_sms_via_client(hass,Mock(),"hello")==200
    assert hass.async_add_executor_job.await_count==calls

@pytest.mark.asyncio
async def test_send_transport_error():
    hass=NS(async_add_executor_job=AsyncMock(side_effect=OSError("offline")))
    with pytest.raises(HomeAssistantError) as err: await helpers.async_send_sms_via_client(hass,Mock(),"hello")
    assert err.value.translation_key=="connection_error"

@pytest.mark.asyncio
@pytest.mark.parametrize("success",[True,False])
async def test_record_and_event(entry,success):
    entry.runtime_data.sensor=Mock()
    hass=NS(bus=NS(async_fire=Mock()))
    with patch.object(helpers,"async_send_sms_via_client",new=AsyncMock(return_value=200,side_effect=None if success else HomeAssistantError(translation_domain="freesmsxa",translation_key="invalid_auth"))):
        if success: await helpers.async_send_and_record(hass,entry,"body")
        else:
            with pytest.raises(HomeAssistantError): await helpers.async_send_and_record(hass,entry,"body")
    assert hass.bus.async_fire.call_args.args[0] == ("freesmsxa_sms_sent" if success else "freesmsxa_sms_failed")
    (entry.runtime_data.sensor.notify_sent if success else entry.runtime_data.sensor.notify_failed).assert_called_once()

@pytest.fixture
def flow():
    f=config_flow.FreeSMSConfigFlow()
    f.hass=NS(async_add_executor_job=AsyncMock(return_value=NS(status_code=200)))
    f.async_set_unique_id=AsyncMock()
    f._abort_if_unique_id_configured=Mock()
    f.async_create_entry=Mock(side_effect=lambda **kw:{"type":"create_entry",**kw})
    f.async_show_form=Mock(side_effect=lambda **kw:{"type":"form",**kw})
    return f

@pytest.mark.asyncio
async def test_flow_skips_connection_when_opted_out(flow):
    result=await flow.async_step_user({"username":"12345678","access_token":"bad", "send_test_sms":False})
    assert result["type"]=="create_entry"
    flow.hass.async_add_executor_job.assert_not_awaited()
    flow.async_set_unique_id.assert_awaited_once_with("12345678")
    flow._abort_if_unique_id_configured.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.parametrize("status,key",[(200,None),(400,"invalid_message"),(402,"quota_exceeded"),(403,"invalid_auth"),(500,"server_error"),(418,"api_error")])
async def test_flow_validation(flow,status,key):
    flow.hass.async_add_executor_job.return_value=NS(status_code=status)
    result=await flow.async_step_user({"username":" 12345678 ","access_token":" token ","send_test_sms":True})
    assert result["type"] == ("form" if key else "create_entry")
    if key: assert result["errors"]["base"] == key

@pytest.mark.asyncio
async def test_flow_invalid_phone(flow):
    result=await flow.async_step_user({"username":"12345678","access_token":"token","phone_number":"invalid"})
    assert result["errors"]["phone_number"]=="invalid_phone_number"
    flow.hass.async_add_executor_job.assert_not_awaited()

@pytest.mark.asyncio
async def test_flow_duplicate(flow):
    flow._abort_if_unique_id_configured.side_effect=AbortFlow("already_configured")
    with pytest.raises(AbortFlow): await flow.async_step_user({"username":"12345678","access_token":"token"})
    flow.hass.async_add_executor_job.assert_not_awaited()

@pytest.mark.asyncio
async def test_flow_transport_recovery(flow):
    flow.hass.async_add_executor_job.side_effect=OSError("offline")
    result=await flow.async_step_user({"username":"12345678","access_token":"token"})
    assert result["errors"]["base"]=="connection_error"
    flow.hass.async_add_executor_job.side_effect=None
    assert (await flow.async_step_user({"username":"12345678","access_token":"token"}))["type"]=="create_entry"

@pytest.mark.asyncio
@pytest.mark.parametrize("status",[200,403])
async def test_reconfigure(flow,entry,status):
    flow._get_reconfigure_entry=Mock(return_value=entry)
    flow.async_update_reload_and_abort=Mock(return_value={"type":"abort","reason":"reconfigure_successful"})
    flow.hass.async_add_executor_job.return_value=NS(status_code=status)
    result=await flow.async_step_reconfigure({"access_token":"new", "name":"New Alias","phone_number":"0612345678"})
    assert result["type"] == ("abort" if status==200 else "form")
    if status==200:
        assert flow.async_update_reload_and_abort.call_args.kwargs["data_updates"]["access_token"]=="new"
    else: assert result["errors"]["base"]=="invalid_auth"

@pytest.mark.asyncio
async def test_setup_runtime_without_connection(entry):
    hass=NS(config_entries=NS(async_forward_entry_setups=AsyncMock()))
    reg=Mock()
    with patch.object(integration,"async_get_device_registry",return_value=reg),patch.object(integration,"async_migrate_notify_name"),patch.object(integration,"FreeClient",return_value=Mock()) as client:
        assert await integration.async_setup_entry(hass,entry) is True
        client.return_value.send_sms.assert_not_called()
    assert isinstance(entry.runtime_data,integration.FreeSMSRuntimeData)
    hass.config_entries.async_forward_entry_setups.assert_awaited_once()
    entry.async_on_unload.assert_not_called()

@pytest.mark.asyncio
async def test_unload(entry):
    hass=NS(config_entries=NS(async_unload_platforms=AsyncMock(return_value=True)))
    assert await integration.async_unload_entry(hass,entry) is True
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(entry,["notify","sensor","button"])

@pytest.mark.asyncio
async def test_action_registered_without_entry():
    hass=NS(data={},services=NS(async_register=Mock()))
    with patch.object(integration.JSModuleRegistration,"async_register",new=AsyncMock()):
        assert await integration.async_setup(hass,{})
    assert hass.services.async_register.call_args.args[:2] == ("freesmsxa","send_sms")
    handler=hass.services.async_register.call_args.args[2]
    hass.services.has_service=Mock(return_value=False)
    hass.states=NS(get=Mock(return_value=None))
    with pytest.raises(ServiceValidationError) as err: await handler(NS(data={"target":"missing","message":"body"}))
    assert err.value.translation_key=="invalid_target"

@pytest.mark.asyncio
async def test_platform_entities(entry):
    added=[]
    for module in (sensor,button,notify):
        await module.async_setup_entry(NS(),entry,added.extend)
    assert len(added)==5
    assert len({e.unique_id for e in added})==5
    assert len({tuple(e.device_info["identifiers"])[0] for e in added})==1
    assert notify.FreeSMSNotifyEntity(entry).has_entity_name is True
    assert all(e.available for e in added)

def test_status_privacy_counters_and_error_availability(entry):
    s=sensor.FreeSMSSensor(entry)
    s._publish=Mock(side_effect=s._refresh_attributes)
    s.notify_sent("PRIVATE_BODY")
    assert s.sms_count==1 and s.sms_today==1
    s.notify_failed("PRIVATE_BODY","connection_error")
    assert s.available is True  # recording a local error does not invent a transport observation
    attrs=s.extra_state_attributes
    assert "username" not in attrs and "phone_number" not in attrs
    assert "PRIVATE_BODY" not in json.dumps(attrs)
    assert attrs["alias"]=="Private Alias"

def test_history_bounded(entry):
    s=sensor.FreeSMSSensor(entry);s._publish=Mock()
    for i in range(60):s.notify_sent("body")
    assert len(s.sms_log)==50

@pytest.mark.asyncio
async def test_diagnostics_redaction_and_custom_test_message(entry):
    result=await diagnostics.async_get_config_entry_diagnostics(NS(),entry)
    text=json.dumps(result)
    for secret in ("12345678","SECRET_TOKEN","Private Alias","0612345678"):assert secret not in text
    # User-authored test SMS bodies are private too.
    assert "PRIVATE_TEST_BODY" not in text

def test_translated_exceptions_exist():
    data=json.loads((ROOT/"custom_components/freesmsxa/strings.json").read_text())
    assert {"invalid_target","empty_message","message_too_long","connection_error","api_error",*helpers.API_STATUS_ERRORS.values()} <= set(data["exceptions"])


@pytest.mark.asyncio
@pytest.mark.parametrize("fallback_alias",[True,False])
async def test_diagnostics_all_alias_and_legacy_paths(entry,fallback_alias):
    secret="PRIVATE_USER_ID_87654321"
    entry.data.update(username=secret,access_token="PRIVATE_API_KEY",name=secret if fallback_alias else "PRIVATE_ALIAS",phone_number="PRIVATE_PHONE")
    entry.data["PRIVATE_LEGACY_KEY"]={"value":"PRIVATE_LEGACY_VALUE"}
    entry.options.update(test_message="PRIVATE_SMS_CONTENT",legacy="PRIVATE_OPTION")
    entry.title=entry.data["name"];entry.unique_id=secret
    entry.runtime_data.username=secret;entry.runtime_data.alias=entry.data["name"]
    entry.runtime_data.sensor=NS(state="PRIVATE_RESTORED_STATE",sms_count=3,sms_today=1,quota_status="PRIVATE_RESTORED_QUOTA")
    result=await diagnostics.async_get_config_entry_diagnostics(NS(),entry)
    assert "PRIVATE_" not in json.dumps(result)
    assert result["sensor"]["state"]=="unknown"
    assert result["sensor"]["quota_status"]=="unknown"
    assert result["sensor"]["sms_count"]==3
    assert result["runtime"]["has_client"] is True

@pytest.mark.asyncio
async def test_api_exception_never_logs_or_chains_request_secrets(caplog):
    import logging,traceback
    secret="PRIVATE_BODY_AND_TOKEN_IN_REQUEST_URL"
    caplog.set_level(logging.DEBUG,logger="custom_components.freesmsxa")
    hass=NS(async_add_executor_job=AsyncMock(side_effect=OSError("https://example.invalid/?pass="+secret)))
    with pytest.raises(HomeAssistantError) as err:
        await helpers.async_send_sms_via_client(hass,Mock(),"PRIVATE_SMS_BODY")
    assert secret not in caplog.text
    assert "PRIVATE_SMS_BODY" not in caplog.text
    assert secret not in "".join(traceback.format_exception(err.value))
    assert err.value.__cause__ is None and err.value.__suppress_context__

@pytest.mark.asyncio
async def test_notify_debug_logs_no_user_or_sms(entry,caplog):
    import logging
    caplog.set_level(logging.DEBUG,logger="custom_components.freesmsxa")
    entry.data["username"]="PRIVATE_USER_ID"
    entity=notify.FreeSMSNotifyEntity(entry);entity.hass=NS()
    with patch.object(notify,"async_send_and_record",new=AsyncMock()) as send:
        await entity.async_send_message("PRIVATE_BODY")
        send.assert_awaited_once_with(entity.hass,entry,"PRIVATE_BODY",source="notify")
    assert "PRIVATE_USER_ID" not in caplog.text and "PRIVATE_BODY" not in caplog.text

@pytest.mark.parametrize("module,limit",[(sensor,0),(button,1),(notify,1)])
def test_explicit_platform_concurrency(module,limit):
    assert module.PARALLEL_UPDATES==limit

@pytest.mark.parametrize("filename",["strings.json","translations/fr.json","translations/en.json"])
def test_every_form_field_has_context(filename):
    data=json.loads((ROOT/"custom_components/freesmsxa"/filename).read_text())
    for group in ["config","options"]:
        for step in data[group]["step"].values():
            assert set(step["data"]) <= set(step["data_description"])


def test_existing_entity_identifiers_preserved(entry):
    s=sensor.FreeSMSSensor(entry)
    assert s.unique_id=="freesmsxa_audit-entry_status"
    assert button.TestSMSButton(entry).unique_id=="freesmsxa_test_button_audit-entry"
    assert notify.FreeSMSNotifyEntity(entry).unique_id=="freesmsxa_notify_12345678"
    assert s.extra_state_attributes["alias"]=="Private Alias"


@pytest.mark.asyncio
async def test_diagnostics_without_loaded_runtime(entry):
    del entry.runtime_data
    result=await diagnostics.async_get_config_entry_diagnostics(NS(),entry)
    assert result["sensor"] is None
    assert result["runtime"]["has_client"] is False
    assert "SECRET_TOKEN" not in json.dumps(result)
    assert "PRIVATE_TEST_BODY" not in json.dumps(result)
