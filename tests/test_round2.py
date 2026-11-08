"""Round2: actual HA entries/flow results and typed, bounded SMS calls."""
import sys
from pathlib import Path
from types import MappingProxyType, SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch
import json
import pytest
import pytest_asyncio
import homeassistant
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry,ConfigEntries,SOURCE_USER,SOURCE_REAUTH
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.exceptions import HomeAssistantError
from custom_components.freesmsxa import FreeSMSRuntimeData
from custom_components.freesmsxa import helpers,config_flow,api
from custom_components.freesmsxa.const import API_TIMEOUT



def add_entry(hass,unique_id="12345678"):
    entry=ConfigEntry(domain="freesmsxa",data={"username":"12345678","access_token":"OLD_TOKEN","name":"Keep Alias","phone_number":"0612345678"},title="Keep Alias",unique_id=unique_id,
        options={"test_message":"Keep Body","debug":False},version=1,minor_version=1,source=SOURCE_USER,discovery_keys=MappingProxyType({}),subentries_data=())
    entry.runtime_data=FreeSMSRuntimeData(client=Mock(),username="12345678",alias="Keep Alias",phone_number="0612345678")
    hass.config_entries._entries[entry.entry_id]=entry
    return entry


def native_flow(hass,entry):
    flow=config_flow.FreeSMSConfigFlow()
    flow.hass=hass;flow.handler="freesmsxa"
    flow.context={"source":SOURCE_REAUTH,"entry_id":entry.entry_id,"unique_id":entry.unique_id}
    return flow


@pytest.mark.asyncio
async def test_native_reauth_form_does_not_send(native_hass):
    entry=add_entry(native_hass);flow=native_flow(native_hass,entry)
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock()) as job:
        result=await flow.async_step_reauth(entry.data)
    assert result["type"]=="form" and result["step_id"]=="reauth_confirm"
    assert result["errors"]=={}
    job.assert_not_awaited()
    # Actual schema validates a token; account ID cannot be changed by this form.
    assert result["data_schema"]({"access_token":"new"})=={"access_token":"new"}
    with pytest.raises(Exception):result["data_schema"]({"access_token":"new","username":"different"})


@pytest.mark.asyncio
@pytest.mark.parametrize("status,key",[(400,"invalid_message"),(402,"quota_exceeded"),(403,"invalid_auth"),(500,"server_error"),(418,"api_error")])
async def test_native_reauth_errors_then_success(native_hass,status,key):
    entry=add_entry(native_hass);flow=native_flow(native_hass,entry)
    old_data=dict(entry.data);old_options=dict(entry.options);entry_id=entry.entry_id
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(return_value=NS(status_code=status))) as job,patch.object(native_hass.config_entries,"async_schedule_reload") as reload:
        result=await flow.async_step_reauth_confirm({"access_token":"BAD_TOKEN"})
        assert result["type"]=="form" and result["errors"]["base"]==key
        assert dict(entry.data)==old_data;reload.assert_not_called()
        request=job.call_args.args[0];assert request.keywords["timeout"]==API_TIMEOUT
        job.return_value=NS(status_code=200)
        result=await flow.async_step_reauth_confirm({"access_token":" NEW_TOKEN "})
        assert result["type"]=="abort" and result["reason"]=="reauth_successful"
        reload.assert_called_once_with(entry_id)
    assert entry.data==old_data|{"access_token":"NEW_TOKEN"}
    assert entry.options==old_options and entry.title=="Keep Alias" and entry.unique_id=="12345678"
    assert native_hass.config_entries.async_get_entry(entry_id) is entry
    assert len(native_hass.config_entries.async_entries("freesmsxa"))==1


@pytest.mark.asyncio
async def test_native_reauth_timeout_does_not_save_or_leak(native_hass):
    entry=add_entry(native_hass);flow=native_flow(native_hass,entry)
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(side_effect=TimeoutError("PRIVATE_TOKEN_IN_URL"))):
        result=await flow.async_step_reauth_confirm({"access_token":"NEW"})
    assert result["errors"]=={"base":"connection_error"}
    assert entry.data["access_token"]=="OLD_TOKEN"
    assert "PRIVATE_TOKEN_IN_URL" not in json.dumps({k:v for k,v in result.items() if k!="data_schema"})


@pytest.mark.asyncio
async def test_native_reauth_wrong_existing_account_aborts(native_hass):
    entry=add_entry(native_hass,unique_id="another-account");flow=native_flow(native_hass,entry)
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(return_value=NS(status_code=200))),patch.object(native_hass.config_entries,"async_schedule_reload") as reload:
        with pytest.raises(AbortFlow) as err:await flow.async_step_reauth_confirm({"access_token":"NEW"})
    assert err.value.reason=="wrong_account"
    assert entry.data["access_token"]=="OLD_TOKEN";reload.assert_not_called()


@pytest.mark.asyncio
async def test_http403_service_starts_native_reauth_and_keeps_error(native_hass):
    body="PRIVATE_BODY"
    entry=add_entry(native_hass)
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(return_value=NS(status_code=403))),patch.object(native_hass.config_entries.flow,"async_init",new=AsyncMock(return_value={"type":"abort"})) as start:
        with pytest.raises(helpers.FreeSMSAuthError) as err:await helpers.async_send_and_record(native_hass,entry,body)
        assert err.value.translation_key=="invalid_auth"
        await native_hass.async_block_till_done()
    start.assert_awaited_once()
    assert start.call_args.kwargs["context"]["source"]==SOURCE_REAUTH
    assert start.call_args.kwargs["context"]["entry_id"]==entry.entry_id
    assert start.call_args.kwargs["data"]["username"]=="12345678"


@pytest.mark.asyncio
@pytest.mark.parametrize("status",[400,402,500,200])
async def test_non_auth_status_never_starts_reauth(native_hass,status):
    entry=add_entry(native_hass)
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(return_value=NS(status_code=status))),patch.object(native_hass.config_entries.flow,"async_init",new=AsyncMock()) as start,patch.object(helpers.asyncio,"sleep",new=AsyncMock()):
        if status==200:await helpers.async_send_and_record(native_hass,entry,"body")
        else:
            with pytest.raises(HomeAssistantError):await helpers.async_send_and_record(native_hass,entry,"body")
        await native_hass.async_block_till_done()
    start.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_executor_client_forwards_connect_and_read_timeout(native_hass):
    client=api.FreeClient("FAKE_USERNAME","FAKE_TOKEN")
    with patch("requests.get",return_value=NS(status_code=200)) as request:
        assert await helpers.async_send_sms_via_client(native_hass,client,"FAKE_BODY")==200
    assert request.call_args.kwargs["timeout"]==API_TIMEOUT
    assert request.call_args.kwargs["params"]["msg"]=="FAKE_BODY"


@pytest.mark.asyncio
async def test_auth_recovery_does_not_send_on_entry_setup(native_hass):
    # The setup contract remains write-only and sends no validation SMS.
    from custom_components import freesmsxa as integration
    entry=add_entry(native_hass)
    with patch.object(integration,"async_get_device_registry",return_value=Mock()),patch.object(native_hass.config_entries,"async_forward_entry_setups",new=AsyncMock()),patch.object(integration,"FreeClient",return_value=Mock()) as client:
        assert await integration.async_setup_entry(native_hass,entry)
        client.return_value.send_sms.assert_not_called()
    # Remove listener registered for this isolated native entry.
    await entry._async_process_on_unload(native_hass)


@pytest.mark.asyncio
async def test_native_user_form_and_duplicate(native_hass):
    entry=add_entry(native_hass)
    flow=config_flow.FreeSMSConfigFlow();flow.hass=native_hass;flow.handler="freesmsxa";flow.context={"source":SOURCE_USER}
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock()) as job:
        result=await flow.async_step_user()
        assert result["type"]=="form" and result["step_id"]=="user"
        with pytest.raises(AbortFlow) as err:await flow.async_step_user({"username":"12345678","access_token":"TOKEN"})
    assert err.value.reason=="already_configured";job.assert_not_awaited()


@pytest.mark.asyncio
async def test_native_options_form_and_result(native_hass):
    entry=add_entry(native_hass)
    flow=config_flow.FreeSMSConfigFlow.async_get_options_flow(entry)
    flow.hass=native_hass;flow.handler=entry.entry_id;flow.context={"source":"init"}
    result=await flow.async_step_init()
    assert result["type"]=="form"
    values={"test_message":"New test body","debug":True}
    assert result["data_schema"](values)==values
    result=await flow.async_step_init(values)
    assert result["type"]=="create_entry" and result["data"]==values


@pytest.mark.asyncio
async def test_native_reconfigure_forms_errors_and_update(native_hass):
    from homeassistant.config_entries import SOURCE_RECONFIGURE
    entry=add_entry(native_hass)
    flow=config_flow.FreeSMSConfigFlow();flow.hass=native_hass;flow.handler="freesmsxa"
    flow.context={"source":SOURCE_RECONFIGURE,"entry_id":entry.entry_id,"unique_id":entry.unique_id}
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock()) as job,patch.object(native_hass.config_entries,"async_schedule_reload") as reload:
        assert (await flow.async_step_reconfigure())["type"]=="form"
        result=await flow.async_step_reconfigure({"access_token":"NEW","phone_number":"invalid"})
        assert result["errors"]=={"phone_number":"invalid_phone_number"};job.assert_not_awaited()
        job.side_effect=TimeoutError("PRIVATE_URL")
        result=await flow.async_step_reconfigure({"access_token":"NEW"})
        assert result["errors"]=={"base":"connection_error"}
        job.side_effect=None;job.return_value=NS(status_code=200)
        result=await flow.async_step_reconfigure({"access_token":"NEW"})
        assert result["type"]=="abort" and result["reason"]=="reconfigure_successful"
        assert job.call_args.args[0].keywords["timeout"]==API_TIMEOUT
    assert entry.data["username"]=="12345678" and entry.data["access_token"]=="NEW"
    assert entry.data["name"]=="Keep Alias";reload.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy",[True,False])
async def test_native_send_sms_service_dispatches_and_propagates(native_hass,legacy):
    from custom_components import freesmsxa as integration
    received=[]
    fail=False
    async def notify_handler(call):
        received.append(dict(call.data))
        if fail:raise HomeAssistantError(translation_domain="freesmsxa",translation_key="server_error")
    native_hass.services.async_register("notify","papa" if legacy else "send_message",notify_handler)
    if not legacy:native_hass.states.async_set("notify.papa","unknown")
    with patch.object(integration.JSModuleRegistration,"async_register",new=AsyncMock()):
        assert await integration.async_setup(native_hass,{})
    await native_hass.services.async_call("freesmsxa","send_sms",{"target":"notify.papa","message":"body"},blocking=True)
    assert received[0]["message"]=="body"
    if not legacy:assert received[0]["entity_id"]=="notify.papa"
    fail=True
    with pytest.raises(HomeAssistantError) as err:
        await native_hass.services.async_call("freesmsxa","send_sms",{"target":"papa","message":"body"},blocking=True)
    assert err.value.translation_key=="server_error"


@pytest.mark.asyncio
async def test_native_service_unknown_target_is_validation_error(native_hass):
    from custom_components import freesmsxa as integration
    from homeassistant.exceptions import ServiceValidationError
    with patch.object(integration.JSModuleRegistration,"async_register",new=AsyncMock()):await integration.async_setup(native_hass,{})
    with pytest.raises(ServiceValidationError) as err:
        await native_hass.services.async_call("freesmsxa","send_sms",{"target":"unknown","message":"body"},blocking=True)
    assert err.value.translation_key=="invalid_target"


@pytest.mark.asyncio
async def test_native_transport_failure_then_recovery_no_auto_sms(native_hass,caplog):
    import logging,traceback,requests
    entry=add_entry(native_hass);entry.runtime_data.client=api.FreeClient("FAKE_USER","FAKE_TOKEN")
    sensor=Mock();entry.runtime_data.sensor=sensor
    caplog.set_level(logging.DEBUG,logger="custom_components.freesmsxa")
    body="PRIVATE_BODY"
    with patch("requests.get",side_effect=[requests.exceptions.Timeout("PRIVATE_URL_WITH_BODY_AND_TOKEN"),NS(status_code=200)]) as request,patch.object(native_hass.config_entries.flow,"async_init",new=AsyncMock()) as reauth:
        with pytest.raises(HomeAssistantError) as err:await helpers.async_send_and_record(native_hass,entry,body)
        assert err.value.translation_key=="connection_error"
        assert "PRIVATE_" not in caplog.text and "PRIVATE_" not in "".join(traceback.format_exception(err.value))
        # Only the explicit next user action probes recovery; no polling/background SMS.
        assert request.call_count==1
        await helpers.async_send_and_record(native_hass,entry,body)
        assert request.call_count==2
        await native_hass.async_block_till_done();reauth.assert_not_awaited()
    sensor.notify_failed.assert_called_once_with("PRIVATE_BODY","connection_error")
    sensor.notify_sent.assert_called_once_with("PRIVATE_BODY")


@pytest.mark.asyncio
async def test_native_options_manager_reloads_once_only_on_change(native_hass):
    entry=add_entry(native_hass)
    flow=config_flow.FreeSMSConfigFlow.async_get_options_flow(entry)
    flow.hass=native_hass;flow.handler=entry.entry_id;flow.context={"source":"init"}
    assert not entry.update_listeners
    values={"test_message":"Changed","debug":True}
    with patch.object(native_hass.config_entries,"async_schedule_reload") as reload:
        result=await flow.async_step_init(values)
        await native_hass.config_entries.options.async_finish_flow(flow,result)
        assert entry.options==values
        reload.assert_called_once_with(entry.entry_id)
        result=await flow.async_step_init(values)
        await native_hass.config_entries.options.async_finish_flow(flow,result)
        reload.assert_called_once()


@pytest.mark.asyncio
async def test_403_does_not_duplicate_pending_native_reauth(native_hass):
    entry=add_entry(native_hass)
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(return_value=NS(status_code=403))),patch.object(ConfigEntry,"async_get_active_flows",return_value=iter([{"context":{"source":SOURCE_REAUTH}}])),patch.object(native_hass.config_entries.flow,"async_init",new=AsyncMock()) as start:
        with pytest.raises(helpers.FreeSMSAuthError):await helpers.async_send_and_record(native_hass,entry,"body")
        await native_hass.async_block_till_done()
    start.assert_not_awaited()


@pytest.mark.asyncio
async def test_native_initial_user_network_error_then_creation(native_hass):
    flow=config_flow.FreeSMSConfigFlow();flow.hass=native_hass;flow.handler="freesmsxa";flow.context={"source":SOURCE_USER}
    values={"username":" 12345678 ","access_token":" TOKEN ","name":"Keep Alias","send_test_sms":True}
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(side_effect=TimeoutError("PRIVATE_REQUEST"))) as job:
        result=await flow.async_step_user(values)
        assert result["type"]=="form" and result["errors"]=={"base":"connection_error"}
        job.side_effect=None;job.return_value=NS(status_code=200)
        result=await flow.async_step_user(values)
        assert result["type"]=="create_entry"
        assert result["data"]["username"]=="12345678" and result["data"]["access_token"]=="TOKEN"
        assert result["title"]=="Keep Alias"
        assert job.call_args.args[0].keywords["timeout"]==API_TIMEOUT


@pytest.mark.asyncio
async def test_native_reauth_same_key_reloads_after_notifications_reenabled(native_hass):
    # HTTP403 also occurs when the provider's SMS option is disabled; after it
    # is re-enabled the correct key may be unchanged. Successful reauth must reload.
    entry=add_entry(native_hass);flow=native_flow(native_hass,entry)
    before=dict(entry.data)
    with patch.object(native_hass,"async_add_executor_job",new=AsyncMock(return_value=NS(status_code=200))),patch.object(native_hass.config_entries,"async_schedule_reload") as reload:
        result=await flow.async_step_reauth_confirm({"access_token":"OLD_TOKEN"})
    assert result["type"]=="abort" and result["reason"]=="reauth_successful"
    assert entry.data==before
    reload.assert_called_once_with(entry.entry_id)
