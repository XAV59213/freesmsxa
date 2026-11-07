"""Round5: real registry migration and native translated platform lifecycle."""
from datetime import timedelta
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.entity_platform import EntityPlatform
from custom_components import freesmsxa as integration
from custom_components.freesmsxa import notify, sensor, button, helpers, migration
from custom_components.freesmsxa.const import DEFAULT_LINE_NAME
from test_round2 import add_entry, native_flow

ROOT = Path(__file__).resolve().parents[1]


def translations(language):
    data = json.loads((ROOT / f"custom_components/freesmsxa/translations/{language}.json").read_text())
    return {f"component.freesmsxa.entity.{domain}.{key}.name": values["name"]
            for domain, entities in data["entity"].items() for key, values in entities.items()}


async def native_notify(hass, entry, language="en"):
    platform = EntityPlatform(hass=hass, logger=logging.getLogger(__name__), domain="notify",
        platform_name="freesmsxa", platform=notify, scan_interval=timedelta(seconds=30), entity_namespace=None)
    platform.config_entry = entry
    # Feed the integration's real JSON names to HA's actual translation/naming engine.
    data = platform.platform_data
    data.platform_translations = translations(language)
    data.object_id_platform_translations = translations("en")
    data.default_language_platform_translations = translations("en")
    entity = notify.FreeSMSNotifyEntity(entry)
    await platform.async_add_entities([entity])
    assert entity.entity_id in platform.entities
    return platform, entity


def old_notify(hass, entry, original_name, *, name=None, disabled=False):
    device = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id,
        identifiers={("freesmsxa", f"freesmsxa_{entry.data['username']}")}, name=helpers.build_device_info(entry.data["username"], entry.data.get("name"))["name"])
    registry = er.async_get(hass)
    old = registry.async_get_or_create("notify", "freesmsxa", f"freesmsxa_notify_{entry.data['username']}",
        config_entry=entry, suggested_object_id="legacy_unchanged", original_name=original_name,
        device_id=device.id, has_entity_name=False)
    old = registry.async_update_entity(old.entity_id, new_entity_id="notify.my_automation_target",
        name=name, icon="mdi:star", aliases={"my voice alias"},
        disabled_by=er.RegistryEntryDisabler.USER if disabled else None,
        hidden_by=er.RegistryEntryHider.USER)
    return old


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [None, "My custom name", "", "12345678"])
@pytest.mark.parametrize("disabled", [False, True])
async def test_migration_preserves_registry_identity_customizations_and_reloads(native_hass, name, disabled):
    entry = add_entry(native_hass)
    before_data = dict(entry.data); before_options = dict(entry.options)
    old = old_notify(native_hass, entry, "Keep Alias", name=name, disabled=disabled)
    registry = er.async_get(native_hass)
    from homeassistant.helpers import area_registry, label_registry
    await area_registry.async_load(native_hass)
    await label_registry.async_load(native_hass)
    area = area_registry.async_get(native_hass).async_create("Temporary test area")
    label = label_registry.async_get(native_hass).async_create("Temporary test label")
    old = registry.async_update_entity(old.entity_id,
        area_id=area.id if name != "" else None, labels={label.label_id})
    old = registry.async_update_entity_options(old.entity_id, "conversation", {"should_expose": False})
    if hasattr(er, "async_get_legacy_friendly_name"):
        friendly_before = er.async_get_legacy_friendly_name(native_hass, old)
    else:
        friendly_before = name if name is not None else "Keep Alias"
    migration.async_migrate_notify_name(native_hass, entry)
    new = registry.async_get(old.entity_id)
    assert new.has_entity_name is True
    for key in ("id", "entity_id", "unique_id", "config_entry_id", "device_id", "icon", "aliases", "area_id", "labels", "options", "disabled_by", "hidden_by"):
        assert getattr(new, key) == getattr(old, key)
    assert new.name == ("Keep Alias" if name is None else name)
    migration.async_migrate_notify_name(native_hass, entry)
    assert registry.async_get(old.entity_id) is new  # idempotent, no persistence churn
    assert entry.data == before_data and entry.options == before_options and entry.title == "Keep Alias"
    if disabled:
        assert not native_hass.states.get(old.entity_id)
        return
    platform, entity = await native_notify(native_hass, entry)
    assert entity.entity_id == old.entity_id and entity.unique_id == old.unique_id
    if name == "" and not hasattr(new, "compat_name"):
        # HA 2025.12 treats an empty override as unset, so it follows the new default.
        assert native_hass.states.get(old.entity_id).attributes["friendly_name"].endswith(" SMS")
    else:
        assert native_hass.states.get(old.entity_id).attributes.get("friendly_name", "") == friendly_before
    assert len(registry.entities) == 1
    await platform.async_reset()
    platform, entity = await native_notify(native_hass, entry, "fr")
    assert entity.entity_id == old.entity_id
    if name == "" and not hasattr(new, "compat_name"):
        # HA 2025.12 treats an empty override as unset, so it follows the new default.
        assert native_hass.states.get(old.entity_id).attributes["friendly_name"].endswith(" SMS")
    else:
        assert native_hass.states.get(old.entity_id).attributes.get("friendly_name", "") == friendly_before
    await platform.async_reset()


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_name", ["12345678", None, "", " 12345678 "])
async def test_implicit_username_default_is_not_retained_as_display_name(native_hass, legacy_name):
    entry = add_entry(native_hass)
    native_hass.config_entries.async_update_entry(entry, data={**entry.data, "name": "12345678"})
    old = old_notify(native_hass, entry, legacy_name)
    migration.async_migrate_notify_name(native_hass, entry)
    new = er.async_get(native_hass).async_get(old.entity_id)
    assert new.name is None and new.has_entity_name
    platform, entity = await native_notify(native_hass, entry)
    state = native_hass.states.get(old.entity_id)
    assert state.attributes["friendly_name"] == DEFAULT_LINE_NAME + " SMS"
    assert "12345678" not in state.attributes["friendly_name"]
    assert entity.entity_id == old.entity_id  # no renaming of automation targets
    assert entry.data["name"] == "12345678"  # existing alias/event payload retained
    await platform.async_reset()


@pytest.mark.asyncio
async def test_user_clearing_retained_name_opts_into_translations(native_hass):
    entry = add_entry(native_hass); old = old_notify(native_hass, entry, "Keep Alias")
    migration.async_migrate_notify_name(native_hass, entry)
    registry = er.async_get(native_hass); registry.async_update_entity(old.entity_id, name=None)
    migration.async_migrate_notify_name(native_hass, entry)
    assert registry.async_get(old.entity_id).name is None
    platform, entity = await native_notify(native_hass, entry)
    assert entity.name == "SMS"
    await platform.async_reset()


@pytest.mark.asyncio
async def test_migration_does_not_touch_other_entry(native_hass):
    entry = add_entry(native_hass); foreign = add_entry(native_hass, "other")
    old = old_notify(native_hass, foreign, "Foreign")
    migration.async_migrate_notify_name(native_hass, entry)
    assert er.async_get(native_hass).async_get(old.entity_id) is old


@pytest.mark.asyncio
async def test_setup_runs_migration_before_platform_forward_without_sending(native_hass):
    entry = add_entry(native_hass); old = old_notify(native_hass, entry, "Keep Alias")
    async def forward(current_entry, platforms):
        assert er.async_get(native_hass).async_get(old.entity_id).has_entity_name
    with patch.object(native_hass.config_entries, "async_forward_entry_setups", new=AsyncMock(side_effect=forward)), patch.object(integration, "FreeClient") as client:
        assert await integration.async_setup_entry(native_hass, entry)
        client.return_value.send_sms.assert_not_called()
    assert entry.runtime_data.alias == "Keep Alias"


@pytest.mark.asyncio
async def test_fresh_entry_defaults_private_and_native_action_targets_stable(native_hass):
    entry = add_entry(native_hass)
    native_hass.config_entries.async_update_entry(entry, data={**entry.data, "name": DEFAULT_LINE_NAME})
    migration.async_migrate_notify_name(native_hass, entry)  # no old registry entity
    platform, entity = await native_notify(native_hass, entry)
    assert entity.name == "SMS" and entity.has_entity_name
    assert "12345678" not in entity.entity_id
    assert native_hass.states.get(entity.entity_id).attributes["friendly_name"] == DEFAULT_LINE_NAME + " SMS"
    await platform.async_reset()


@pytest.mark.parametrize("alias", [None, "", "  ", "12345678", " 12345678 ", DEFAULT_LINE_NAME])
def test_device_default_does_not_expose_user_id(alias):
    assert helpers.build_device_info("12345678", alias)["name"] == DEFAULT_LINE_NAME


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["en", "fr"])
async def test_all_entities_use_real_localized_names_and_icons(native_hass, language):
    entry = add_entry(native_hass); status = sensor.FreeSMSSensor(entry)
    entities = [status, sensor.FreeSMSCountSensor(entry, status), sensor.FreeSMSTodaySensor(entry, status), button.TestSMSButton(entry), notify.FreeSMSNotifyEntity(entry)]
    icons = json.loads((ROOT / "custom_components/freesmsxa/icons.json").read_text())["entity"]
    values = translations(language)
    for entity in entities:
        domain = "notify" if isinstance(entity, notify.FreeSMSNotifyEntity) else "button" if isinstance(entity, button.TestSMSButton) else "sensor"
        platform = EntityPlatform(hass=native_hass, logger=logging.getLogger(__name__), domain=domain,
            platform_name="freesmsxa", platform=None, scan_interval=timedelta(seconds=30), entity_namespace=None)
        platform.platform_data.platform_translations = values
        entity.add_to_platform_start(native_hass, platform, None)
        assert entity.has_entity_name
        assert entity.name == values[f"component.freesmsxa.entity.{domain}.{entity.translation_key}.name"]
        assert icons[domain][entity.translation_key]["default"].startswith("mdi:")
        entity.add_to_platform_abort()


@pytest.mark.asyncio
async def test_new_config_blank_alias_never_uses_username(native_hass):
    entry = add_entry(native_hass); flow = native_flow(native_hass, entry)
    flow.context = {"source": "user"}
    with patch.object(flow, "async_set_unique_id", new=AsyncMock()), patch.object(flow, "_abort_if_unique_id_configured"), patch.object(native_hass, "async_add_executor_job", new=AsyncMock()) as request:
        result = await flow.async_step_user({"username": "87654321", "access_token": "FAKE_TOKEN", "send_test_sms": False, "name": "  "})
    assert result["title"] == DEFAULT_LINE_NAME and result["data"]["name"] == DEFAULT_LINE_NAME
    request.assert_not_awaited()


@pytest.mark.asyncio
async def test_ha_compatibility_name_survives_native_reregistration(native_hass):
    entry = add_entry(native_hass); old = old_notify(native_hass, entry, "Keep Alias", name="Chosen name")
    registry = er.async_get(native_hass)
    if hasattr(old, "compat_name"):
        # Simulate the native HA 1.24 storage migration of a custom full name.
        old = registry._async_update_entity(old.entity_id, compat_name="Chosen name")
    migration.async_migrate_notify_name(native_hass, entry)
    platform, entity = await native_notify(native_hass, entry)
    assert native_hass.states.get(old.entity_id).attributes["friendly_name"] == "Chosen name"
    assert registry.async_get(old.entity_id).name == "Chosen name"
    await platform.async_reset()


@pytest.mark.asyncio
async def test_device_user_name_is_not_overwritten(native_hass):
    entry = add_entry(native_hass); old = old_notify(native_hass, entry, "Keep Alias", name="Custom entity")
    devices = dr.async_get(native_hass)
    devices.async_update_device(old.device_id, name_by_user="My custom device")
    await native_hass.async_block_till_done()
    migration.async_migrate_notify_name(native_hass, entry)
    platform, entity = await native_notify(native_hass, entry)
    assert devices.async_get(old.device_id).name_by_user == "My custom device"
    assert er.async_get(native_hass).async_get(old.entity_id).name == "Custom entity"
    assert entity.entity_id == old.entity_id
    await platform.async_reset()


@pytest.mark.asyncio
async def test_legacy_username_entity_id_is_preserved_but_not_default_name(native_hass):
    entry = add_entry(native_hass)
    native_hass.config_entries.async_update_entry(entry, data={**entry.data, "name": "12345678"})
    old = old_notify(native_hass, entry, "12345678")
    registry = er.async_get(native_hass)
    old = registry.async_update_entity(old.entity_id, new_entity_id="notify.12345678")
    migration.async_migrate_notify_name(native_hass, entry)
    platform, entity = await native_notify(native_hass, entry)
    assert entity.entity_id == "notify.12345678" and entity.unique_id == old.unique_id
    assert "12345678" not in native_hass.states.get(entity.entity_id).attributes["friendly_name"]
    await platform.async_reset()


@pytest.mark.asyncio
async def test_existing_automation_action_still_targets_same_notify_entity(native_hass):
    from homeassistant.helpers import service
    from homeassistant.core import HassJobType
    from types import SimpleNamespace
    import voluptuous as vol
    entry = add_entry(native_hass); old = old_notify(native_hass, entry, "Keep Alias")
    entry.runtime_data.client.send_sms.return_value = SimpleNamespace(status_code=200)
    events = []
    native_hass.bus.async_listen("freesmsxa_sms_sent", lambda event: events.append(event.data))
    migration.async_migrate_notify_name(native_hass, entry)
    platform, entity = await native_notify(native_hass, entry)
    service.async_register_entity_service(native_hass, "notify", "send_message",
        entities=platform.entities, func="async_send_message", job_type=HassJobType.Coroutinefunction,
        schema={vol.Required("message"): str})
    await native_hass.services.async_call("notify", "send_message",
        {"entity_id": old.entity_id, "message": "FAKE_BODY"}, blocking=True)
    await native_hass.async_block_till_done()
    entry.runtime_data.client.send_sms.assert_called_once()
    assert entry.runtime_data.alias == "Keep Alias" and entry.data["name"] == "Keep Alias"
    assert events and events[0]["alias"] == "Keep Alias"
    await platform.async_reset()


@pytest.mark.asyncio
@pytest.mark.parametrize("chosen_name", [None, "Chosen custom name"])
async def test_actual_setup_privacy_device_rename_keeps_custom_fields_and_targets(native_hass, chosen_name):
    entry = add_entry(native_hass)
    native_hass.config_entries.async_update_entry(entry, data={**entry.data, "name": "12345678"})
    old = old_notify(native_hass, entry, "12345678", name=chosen_name)
    registry = er.async_get(native_hass)
    devices = dr.async_get(native_hass)
    devices.async_update_device(old.device_id, name="Free Mobile SMS (12345678)")
    await native_hass.async_block_till_done()
    if chosen_name and hasattr(old, "compat_name"):
        registry._async_update_entity(old.entity_id, compat_name=chosen_name)
    loaded = []
    async def forward(current_entry, platforms):
        loaded.append(await native_notify(native_hass, entry))
    with patch.object(native_hass.config_entries, "async_forward_entry_setups", new=AsyncMock(side_effect=forward)), patch.object(integration, "FreeClient") as client:
        assert await integration.async_setup_entry(native_hass, entry)
        client.return_value.send_sms.assert_not_called()
    await native_hass.async_block_till_done()
    new = registry.async_get(old.entity_id)
    assert new.name == chosen_name and new.icon == old.icon and new.unique_id == old.unique_id
    assert devices.async_get(old.device_id).name == DEFAULT_LINE_NAME
    assert "12345678" not in native_hass.states.get(old.entity_id).attributes["friendly_name"]
    if chosen_name:
        assert chosen_name in native_hass.states.get(old.entity_id).attributes["friendly_name"]
    assert entry.runtime_data.alias == "12345678" and entry.data["name"] == "12345678"
    await loaded[0][0].async_reset()
