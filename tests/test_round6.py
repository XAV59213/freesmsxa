"""Round6: public-first migration, native entry lifecycle and stable enum states."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import loader
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.core import State
from custom_components import freesmsxa as integration
from custom_components.freesmsxa import migration, sensor, config_flow
from test_round2 import add_entry
from test_round5 import old_notify, native_notify

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [None, "Custom name", "", "12345678"])
async def test_normal_migration_uses_public_api_without_manufacturing_compat_cache(native_hass, name):
    entry = add_entry(native_hass)
    old = old_notify(native_hass, entry, "Keep Alias", name=name)
    registry = er.async_get(native_hass)
    with patch.object(registry, "async_update_entity", wraps=registry.async_update_entity) as update:
        migration.async_migrate_notify_name(native_hass, entry)
    update.assert_called_once_with(old.entity_id, name="Keep Alias" if name is None else name, has_entity_name=True)
    new = registry.async_get(old.entity_id)
    assert getattr(new, "compat_name", None) is None
    assert new.aliases == old.aliases
    platform, entity = await native_notify(native_hass, entry)
    assert entity.entity_id == old.entity_id and entity.unique_id == old.unique_id
    await platform.async_reset()


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["Alert", ""])
async def test_modern_unprefixed_name_prevents_duplicate_device_prefix(native_hass, suffix):
    entry = add_entry(native_hass)
    full_name = ("Free Mobile SMS (Keep Alias) " + suffix).strip()
    old = old_notify(native_hass, entry, full_name)
    if not hasattr(old, "entity_name"):
        # Old HA does not store this derived field: retain the original name.
        expected = full_name
    else:
        assert old.original_name_unprefixed == suffix
        expected = suffix
    migration.async_migrate_notify_name(native_hass, entry)
    new = er.async_get(native_hass).async_get(old.entity_id)
    assert new.name == expected
    assert getattr(new, "compat_name", None) is None
    platform, entity = await native_notify(native_hass, entry)
    assert native_hass.states.get(entity.entity_id).attributes["friendly_name"] == full_name
    await platform.async_reset()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [None, "Custom name", "", "12345678"])
async def test_existing_native_compat_name_retained_without_changing_user_aliases(native_hass, name):
    entry = add_entry(native_hass)
    old = old_notify(native_hass, entry, "Keep Alias Alert", name=name)
    registry = er.async_get(native_hass)
    if hasattr(old, "compat_name"):
        old = registry._async_update_entity(old.entity_id, compat_name="Existing full legacy name")
        with patch.object(registry, "async_update_entity", wraps=registry.async_update_entity) as update:
            migration.async_migrate_notify_name(native_hass, entry)
        update.assert_not_called()  # exactly the isolated cache-preservation path
        new = registry.async_get(old.entity_id)
        assert new.compat_name == "Existing full legacy name"
        assert new.aliases == old.aliases
        platform, entity = await native_notify(native_hass, entry)
        assert native_hass.states.get(entity.entity_id).attributes.get("friendly_name") == "Existing full legacy name"
        await platform.async_reset()
    else:
        migration.async_migrate_notify_name(native_hass, entry)
        assert registry.async_get(old.entity_id).has_entity_name
        assert registry.async_get(old.entity_id).aliases == old.aliases


@pytest.mark.asyncio
async def test_username_compat_cache_is_cleared_via_public_api(native_hass):
    entry = add_entry(native_hass)
    native_hass.config_entries.async_update_entry(entry, data={**entry.data, "name": "12345678"})
    old = old_notify(native_hass, entry, "12345678")
    registry = er.async_get(native_hass)
    if hasattr(old, "compat_name"):
        old = registry._async_update_entity(old.entity_id, compat_name="12345678")
    with patch.object(registry, "async_update_entity", wraps=registry.async_update_entity) as update:
        migration.async_migrate_notify_name(native_hass, entry)
    update.assert_called_once_with(old.entity_id, name=None, has_entity_name=True)
    assert getattr(registry.async_get(old.entity_id), "compat_name", None) is None
    platform, entity = await native_notify(native_hass, entry)
    assert "12345678" not in native_hass.states.get(entity.entity_id).attributes.get("friendly_name", "")
    await platform.async_reset()


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["Idle", "Last sent", "Quota", "Error", "unknown", "unavailable", "unexpected legacy value"])
async def test_enum_metadata_preserves_known_legacy_states_and_rejects_unknown_restore(native_hass, state):
    entry = add_entry(native_hass)
    entity = sensor.FreeSMSSensor(entry)
    entity.hass = native_hass
    entity.entity_id = "sensor.enum_restore"
    with patch.object(entity, "async_get_last_state", new=AsyncMock(return_value=State(entity.entity_id, state, {}))):
        await entity.async_added_to_hass()
    assert entity.device_class == "enum"
    assert entity.options == ["Idle", "Last sent", "Quota", "Error"]
    assert entity.native_value == (state if state in entity.options else "Idle")
    await entity.async_will_remove_from_hass()


async def prepare_native_entry(hass):
    loader.async_setup(hass)
    from homeassistant.helpers import frame
    frame.async_setup(hass)
    hass.http = Mock()  # HTTP view registration only; never bind a server
    source = ROOT / "custom_components/freesmsxa"
    manifest = json.loads((source / "manifest.json").read_text())
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {"freesmsxa": loader.Integration(
        hass, "custom_components.freesmsxa", source, manifest, {p.name for p in source.iterdir()})}
    hass.config.skip_pip = True  # dependencies already provisioned; no installations/network
    hass.config.components.update({"frontend", "http"})  # no real web server/UI
    return add_entry(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("retry_domain", ["notify", "button"])
async def test_real_domain_entry_platform_services_unload_reload_recover_without_setup_sms(native_hass, retry_domain, caplog):
    """Actual HA loader/setup/forwarding/services; frontend/HTTP resources are a UI boundary."""
    hass = native_hass
    entry = await prepare_native_entry(hass)
    client = Mock()
    client.send_sms.side_effect = [OSError("PRIVATE_TRANSPORT_DETAILS"), NS(status_code=200)]
    with patch.object(integration, "FreeClient", return_value=client), patch.object(integration.JSModuleRegistration, "async_register", new=AsyncMock()):
        assert await asyncio.wait_for(hass.config_entries.async_setup(entry.entry_id), 30)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        client.send_sms.assert_not_called()
        registry = er.async_get(hass)
        entities = {e.domain: e for e in registry.entities.values() if e.config_entry_id == entry.entry_id and e.domain != "sensor"}
        statuses = [e for e in registry.entities.values() if e.config_entry_id == entry.entry_id and e.unique_id.endswith("_status")]
        assert len(statuses) == 1
        status_id = statuses[0].entity_id
        assert len([e for e in registry.entities.values() if e.config_entry_id == entry.entry_id]) == 5
        assert hass.states.get(status_id).state == "Idle"
        assert hass.states.get(status_id).attributes["device_class"] == "enum"
        assert hass.services.has_service("freesmsxa", "send_sms")
        # New optional troubleshooting button starts disabled, never existing entities.
        assert entities["button"].disabled_by is er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get(entities["button"].entity_id) is None
        registry.async_update_entity(entities["button"].entity_id, disabled_by=None)
        # HA reenables disabled platforms through entry reload, like its UI.
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        client.send_sms.assert_not_called()
        assert hass.states.get(entities["button"].entity_id).state != "unavailable"
        # Use the real integration service and HA notify entity dispatcher.
        with pytest.raises(HomeAssistantError) as err:
            await hass.services.async_call("freesmsxa", "send_sms", {"target": entities["notify"].entity_id, "message": "PRIVATE_BODY"}, blocking=True)
        assert err.value.translation_key == "connection_error"
        assert hass.states.get(status_id).state == "unavailable"
        assert hass.states.get(entities["notify"].entity_id).state != "unavailable"
        assert hass.states.get(entities["button"].entity_id).state != "unavailable"
        await hass.async_block_till_done()
        assert client.send_sms.call_count == 1
        data = {"entity_id": entities[retry_domain].entity_id}
        if retry_domain == "notify": data["message"] = "PRIVATE_BODY"
        await hass.services.async_call(retry_domain, "send_message" if retry_domain == "notify" else "press", data, blocking=True)
        assert hass.states.get(status_id).state == "Last sent"
        assert client.send_sms.call_count == 2
        ids_before = {e.entity_id: e.unique_id for e in registry.entities.values() if e.config_entry_id == entry.entry_id}
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
        assert all(hass.states.get(eid).state == "unavailable" for eid in ids_before)
        assert client.send_sms.call_count == 2
        assert await asyncio.wait_for(hass.config_entries.async_setup(entry.entry_id), 30)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert {e.entity_id: e.unique_id for e in registry.entities.values() if e.config_entry_id == entry.entry_id} == ids_before
        assert entry.runtime_data.api_reachable is None
        assert hass.states.get(status_id).state != "unavailable"
        assert client.send_sms.call_count == 2  # reload never probes
        assert await hass.config_entries.async_unload(entry.entry_id)
    assert "PRIVATE_" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("disabled_by", [None, er.RegistryEntryDisabler.USER])
async def test_existing_button_enable_disable_choices_survive_changed_default(native_hass, disabled_by):
    hass = native_hass
    entry = await prepare_native_entry(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create("button", "freesmsxa", f"freesmsxa_test_button_{entry.entry_id}",
        config_entry=entry, suggested_object_id="existing_automation_button", disabled_by=disabled_by)
    with patch.object(integration, "FreeClient", return_value=Mock()) as client, patch.object(integration.JSModuleRegistration, "async_register", new=AsyncMock()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        new = registry.async_get(old.entity_id)
        assert new.entity_id == old.entity_id and new.unique_id == old.unique_id and new.disabled_by == disabled_by
        state = hass.states.get(old.entity_id)
        assert (state is None) == (disabled_by is not None)
        client.return_value.send_sms.assert_not_called()
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_runtime_auth_failure_deduplicates_reauth_and_recovers_same_entry(native_hass, caplog):
    hass = native_hass
    entry = await prepare_native_entry(hass)
    client = Mock()
    client.send_sms.return_value = NS(status_code=403)
    validator = Mock()
    validator.send_sms.return_value = NS(status_code=200)
    with patch.object(integration, "FreeClient", return_value=client), patch.object(config_flow, "FreeClient", return_value=validator), patch.object(integration.JSModuleRegistration, "async_register", new=AsyncMock()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        before = {e.entity_id: e.unique_id for e in registry.entities.values() if e.config_entry_id == entry.entry_id}
        notify_id = next(k for k in before if k.startswith("notify."))
        for _ in range(2):
            with pytest.raises(HomeAssistantError) as error:
                await hass.services.async_call("notify", "send_message", {"entity_id": notify_id, "message": "PRIVATE_BODY"}, blocking=True)
            assert error.value.translation_key == "invalid_auth"
            await hass.async_block_till_done()
            flows = [f for f in hass.config_entries.flow.async_progress() if f["handler"] == "freesmsxa"]
            assert len(flows) == 1 and flows[0]["step_id"] == "reauth_confirm"
            issue = ir.async_get(hass).async_get_issue("homeassistant", f"config_entry_reauth_freesmsxa_{entry.entry_id}")
            assert issue is not None and getattr(issue, "config_entry_id", entry.entry_id) == entry.entry_id
            assert issue.data["flow_id"] == flows[0]["flow_id"] and issue.issue_domain == "freesmsxa"
            assert issue.translation_key == "config_entry_reauth" and issue.severity is ir.IssueSeverity.ERROR
            validator.send_sms.assert_not_called()  # opening native reauth never sends
        assert client.send_sms.call_count == 2
        client.send_sms.return_value = NS(status_code=200)
        result = await hass.config_entries.flow.async_configure(flows[0]["flow_id"], {"access_token": "NEW_FAKE_TOKEN"})
        assert result["type"] == "abort" and result["reason"] == "reauth_successful"
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert entry.data["access_token"] == "NEW_FAKE_TOKEN"
        assert ir.async_get(hass).async_get_issue("homeassistant", f"config_entry_reauth_freesmsxa_{entry.entry_id}") is None
        assert {e.entity_id: e.unique_id for e in registry.entities.values() if e.config_entry_id == entry.entry_id} == before
        validator.send_sms.assert_called_once()  # explicit submission only, synthetic transport
        assert client.send_sms.call_count == 2  # reload is silent
        await hass.services.async_call("notify", "send_message", {"entity_id": notify_id, "message": "PRIVATE_BODY"}, blocking=True)
        assert client.send_sms.call_count == 3 and entry.runtime_data.api_reachable is True
        assert len(hass.config_entries.async_entries("freesmsxa")) == 1
        assert not [f for f in hass.config_entries.flow.async_progress() if f["handler"] == "freesmsxa"]
        assert await hass.config_entries.async_unload(entry.entry_id)
    assert "PRIVATE_" not in caplog.text and "NEW_FAKE_TOKEN" not in caplog.text


@pytest.mark.asyncio
async def test_derived_username_fallback_is_not_promoted_to_custom_name(native_hass):
    entry = add_entry(native_hass)
    old = old_notify(native_hass, entry, "Free Mobile SMS (Keep Alias) 12345678")
    migration.async_migrate_notify_name(native_hass, entry)
    new = er.async_get(native_hass).async_get(old.entity_id)
    if hasattr(old, "entity_name"):
        assert old.entity_name == "12345678" and new.name is None
        platform, entity = await native_notify(native_hass, entry)
        assert "12345678" not in native_hass.states.get(entity.entity_id).attributes.get("friendly_name", "")
        await platform.async_reset()
    else:
        # Old HA has no derived component: keep this non-default original alias.
        assert new.name == old.original_name
