"""Round7: truthful schema types, checked migration contract and storage privacy."""
from inspect import signature
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch
import json

import pytest
from homeassistant.core import State
from homeassistant.data_entry_flow import InvalidData
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.util import dt as dt_util
from custom_components import freesmsxa as integration
from custom_components.freesmsxa import schema, migration, sensor, diagnostics, config_flow
from test_round2 import add_entry
from test_round3 import attach_to_native_platform
from test_round5 import old_notify
from test_round6 import prepare_native_entry


def test_schema_is_ha_runtime_engine_not_a_static_alias():
    assert schema.Schema is type(cv.PLATFORM_SCHEMA)
    engine = schema._ENGINE
    assert schema.Schema is engine.Schema
    required = schema.Required("required")
    optional = schema.Optional("optional", default="kept")
    assert isinstance(required, engine.Required) and isinstance(optional, engine.Optional)
    validator = schema.Schema({required: str, optional: str})
    assert validator({"required": "value"}) == {"required": "value", "optional": "kept"}
    for value in ({}, {"required": []}, {"required": "x", "extra": "reject"}):
        with pytest.raises(engine.Invalid): validator(value)


@pytest.mark.parametrize("factory", [None, lambda *a, **kw: []])
def test_invalid_marker_contract_fails_without_fallback(factory):
    with patch.object(schema._ENGINE, "Required", factory):
        with pytest.raises(TypeError, match="HA validation marker"):
            schema.Required("PRIVATE_FIELD")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [{"username": [], "access_token": "FAKE"}, {"access_token": "FAKE"},
    {"username": "87654321", "access_token": []}, {"username": "87654321", "access_token": "FAKE", "extra": "PRIVATE"}])
async def test_real_flow_manager_rejects_bad_schema_input_in_native_exception_family(native_hass, bad):
    hass = native_hass
    await prepare_native_entry(hass)
    with patch.object(config_flow, "FreeClient") as client:
        flow = await hass.config_entries.flow.async_init("freesmsxa", context={"source": "user"})
        assert flow["type"] == "form"
        assert isinstance(flow["data_schema"], schema.Schema)
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(flow["flow_id"], bad)
        client.assert_not_called()
        hass.config_entries.flow.async_abort(flow["flow_id"])


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [{}, {"message": "PRIVATE_BODY"}, {"target": "notify.x", "message": []},
    {"target": "notify.x", "message": "PRIVATE_BODY", "unknown": True}])
async def test_real_integration_service_rejects_invalid_data_before_any_send(native_hass, bad):
    hass = native_hass
    entry = await prepare_native_entry(hass)
    with patch.object(integration, "FreeClient") as client, patch.object(integration.JSModuleRegistration, "async_register", new=AsyncMock()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        # Native validator errors are intercepted by the normal HA service layer.
        with pytest.raises((schema._ENGINE.Invalid, HomeAssistantError)):
            await hass.services.async_call("freesmsxa", "send_sms", bad, blocking=True)
        client.return_value.send_sms.assert_not_called()
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("update", [None, lambda entity_id, *, name, has_entity_name: None])
def test_private_contract_api_drift_fails_closed_before_updating(update):
    registry = NS(_async_update_entity=update)
    with pytest.raises(ConfigEntryError) as error:
        migration._preserve_compat_name(registry, "notify.fake", "PRIVATE_NAME", "PRIVATE_CACHE")
    assert error.value.translation_key == "unsupported_ha_contract"
    assert "PRIVATE" not in str(error.value)


def test_private_signature_introspection_failure_is_safe():
    with patch.object(migration, "signature", side_effect=ValueError("PRIVATE_SIGNATURE")):
        with pytest.raises(ConfigEntryError) as error:
            migration._preserve_compat_name(NS(_async_update_entity=Mock()), "notify.fake", "PRIVATE", "PRIVATE")
    assert "PRIVATE" not in str(error.value) and error.value.__suppress_context__


@pytest.mark.asyncio
async def test_native_private_update_contract_matches_only_supported_ha(native_hass):
    registry = er.async_get(native_hass)
    entry = add_entry(native_hass)
    old = old_notify(native_hass, entry, "Keep Alias", name="Chosen")
    if hasattr(old, "compat_name"):
        assert "compat_name" in signature(registry._async_update_entity).parameters
        old = registry._async_update_entity(old.entity_id, compat_name="Actual legacy display")
        migration.async_migrate_notify_name(native_hass, entry)
        new = registry.async_get(old.entity_id)
        assert new.compat_name == old.compat_name and new.name == old.name
        assert new.aliases == old.aliases and new.entity_id == old.entity_id and new.unique_id == old.unique_id
    else:
        assert "compat_name" not in signature(registry._async_update_entity).parameters
        with patch.object(migration, "_preserve_compat_name", side_effect=AssertionError("must not enter on old HA")):
            migration.async_migrate_notify_name(native_hass, entry)
        assert registry.async_get(old.entity_id).has_entity_name


@pytest.mark.parametrize("value,expected", [("42",42), (0,0), (-2,0), ("PRIVATE_COUNTER",0), (None,0), ([],0), (True,0), (1.5,0)])
def test_restored_counters_recover_without_private_values_or_crash(value, expected):
    assert sensor._restored_count(value) == expected


@pytest.mark.asyncio
async def test_restore_metadata_is_allowlisted_and_diagnostics_and_storage_do_not_republish_private_values(native_hass):
    entry = add_entry(native_hass)
    entity = sensor.FreeSMSSensor(entry)
    entity.hass = native_hass
    entity.entity_id = "sensor.round7_restored"
    today = dt_util.now().date().isoformat()
    time = dt_util.now().isoformat()
    original = {"sms_count":"23", "sms_today":"4", "sms_today_date":today,
        "last_sent":"PRIVATE_URL?pass=PRIVATE_TOKEN", "last_error":"PRIVATE_URL?msg=PRIVATE_BODY", "quota_status":"PRIVATE_QUOTA",
        "sms_log":[{"time":time,"status":"failed","error":"quota_exceeded","length":8,"message":"PRIVATE_BODY","arbitrary":{"PRIVATE_KEY":"PRIVATE_VALUE"}},
            {"time":"PRIVATE_TIME","status":"sent","length":"bad PRIVATE_LENGTH","error":"PRIVATE_ERROR"},
            {"status":"PRIVATE_STATUS","message":"PRIVATE_BODY"}, "PRIVATE_ITEM"]}
    before = json.dumps(original, sort_keys=True)
    with patch.object(entity,"async_get_last_state",new=AsyncMock(return_value=State(entity.entity_id,"Error",original))):
        await attach_to_native_platform(entity, native_hass, entity.entity_id)
        first = entity.sms_log
        # Re-adding the same instance must replace, not append, restored history.
        await entity.async_added_to_hass()
    assert json.dumps(original, sort_keys=True) == before  # never mutate the loaded backup object
    assert entity.sms_count == 23 and entity.sms_today == 4
    assert entity.sms_log == first == [{"time":time,"status":"failed","error":"quota_exceeded","length":8}, {"status":"sent","length":0}]
    assert entity.extra_state_attributes["last_sent"] is None and entity.extra_state_attributes["last_error"] is None
    copy = entity.sms_log; copy[0]["error"]="PRIVATE_MUTATION"
    assert entity.sms_log[0]["error"] == "quota_exceeded"
    entry.runtime_data.sensor=entity
    diagnostic=await diagnostics.async_get_config_entry_diagnostics(native_hass,entry)
    entity.async_write_ha_state()
    serialized = json.dumps({"attrs":dict(native_hass.states.get(entity.entity_id).attributes),"diagnostics":diagnostic}, default=str)
    assert "PRIVATE" not in serialized and "OLD_TOKEN" not in serialized and "Keep Body" not in serialized
    assert entity.native_value == "Error" and entity.quota_status == "ok"
    await entity.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_valid_persisted_metadata_and_ids_remain_unchanged(native_hass):
    entry=add_entry(native_hass); entity=sensor.FreeSMSSensor(entry); entity.hass=native_hass;entity.entity_id="sensor.round7_valid"
    timestamp=dt_util.now().isoformat(); attrs={"sms_count":12,"sms_today":2,"sms_today_date":dt_util.now().date().isoformat(),
        "last_sent":timestamp,"last_error":"invalid_auth","quota_status":"throttled", "sms_log":[{"time":timestamp,"status":"failed","length":5,"error":"invalid_auth"}]}
    unique=entity.unique_id
    with patch.object(entity,"async_get_last_state",new=AsyncMock(return_value=State(entity.entity_id,"Quota",attrs))):
        await entity.async_added_to_hass()
    assert entity.sms_count==12 and entity.sms_today==2 and entity.native_value=="Quota" and entity.unique_id==unique
    assert all(entity.extra_state_attributes[k]==v for k,v in attrs.items())
    entry.runtime_data.client.send_sms.assert_not_called()
    await entity.async_will_remove_from_hass()


@pytest.mark.asyncio
@pytest.mark.parametrize("record", [{"status":"sent"}, {"status":"failed","error":"connection_error"}])
async def test_legacy_history_without_optional_metadata_is_retained(native_hass, record):
    entry=add_entry(native_hass); entity=sensor.FreeSMSSensor(entry); entity.hass=native_hass; entity.entity_id="sensor.round7_legacy"
    with patch.object(entity,"async_get_last_state",new=AsyncMock(return_value=State(entity.entity_id,"Idle",{"sms_log":[record]}))):
        await entity.async_added_to_hass()
    assert entity.sms_log==[record]
    entry.runtime_data.client.send_sms.assert_not_called()
    await entity.async_will_remove_from_hass()


def test_fail_closed_contract_error_is_localized_in_both_languages():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/"custom_components/freesmsxa"
    for name in ["strings.json","translations/en.json","translations/fr.json"]:
        text=json.loads((root/name).read_text())["exceptions"]["unsupported_ha_contract"]["message"]
        assert text and "{name}" not in text and "{compat_name}" not in text
