"""Reachability, local state restoration and compatibility of diagnostic metadata."""
from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch
import json
from pathlib import Path
import pytest

from homeassistant.core import State
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import EntityPlatform
from custom_components import freesmsxa as integration
from custom_components.freesmsxa import sensor, button, notify, helpers, diagnostics
from test_round2 import add_entry


async def attach_to_native_platform(entity, hass, entity_id):
    domain = entity_id.split(".", 1)[0]
    platform = EntityPlatform(hass=hass, logger=logging.getLogger(__name__),
        domain=domain, platform_name="freesmsxa", platform=None,
        scan_interval=timedelta(seconds=30), entity_namespace=None)
    entity.entity_id = entity_id
    entity.add_to_platform_start(hass, platform, None)
    await entity.add_to_platform_finish()



@pytest.mark.asyncio
async def test_reachability_transitions_once_per_entry_without_blocking_retry(native_hass, caplog):
    import logging
    entry = add_entry(native_hass)
    caplog.set_level(logging.INFO, logger="custom_components.freesmsxa")
    answers = [OSError("PRIVATE_REQUEST"), OSError("PRIVATE_REQUEST"), NS(status_code=403), NS(status_code=200), OSError("PRIVATE_REQUEST"), NS(status_code=200)]
    with patch.object(native_hass, "async_add_executor_job", new=AsyncMock(side_effect=answers)), patch.object(native_hass.config_entries.flow, "async_init", new=AsyncMock(return_value={"type": "abort"})):
        for i in range(len(answers)):
            if i in (3, 5):
                await helpers.async_send_and_record(native_hass, entry, "PRIVATE_BODY")
            else:
                with pytest.raises(HomeAssistantError):
                    await helpers.async_send_and_record(native_hass, entry, "PRIVATE_BODY")
            assert entry.runtime_data.api_reachable is (i in (2, 3, 5))
            # Commands remain reachable: no unavailability lock or polling.
            assert notify.FreeSMSNotifyEntity(entry).available
            assert button.TestSMSButton(entry).available
        await native_hass.async_block_till_done()
    messages = [record.getMessage() for record in caplog.records]
    assert messages.count("Free Mobile API connection unavailable") == 2
    assert messages.count("Free Mobile API connection restored") == 2
    assert "PRIVATE_" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 402, 403, 418, 500])
async def test_http_error_proves_transport_reachable_not_success(native_hass, status):
    entry = add_entry(native_hass)
    entry.runtime_data.api_reachable = False
    with patch.object(native_hass, "async_add_executor_job", new=AsyncMock(return_value=NS(status_code=status))), patch.object(helpers.asyncio, "sleep", new=AsyncMock()), patch.object(native_hass.config_entries.flow, "async_init", new=AsyncMock(return_value={"type": "abort"})):
        with pytest.raises(HomeAssistantError):
            await helpers.async_send_and_record(native_hass, entry, "body")
        await native_hass.async_block_till_done()
    assert entry.runtime_data.api_reachable is True


@pytest.mark.asyncio
async def test_local_validation_does_not_invent_connection_state(native_hass):
    entry = add_entry(native_hass)
    with patch.object(native_hass, "async_add_executor_job", new=AsyncMock()) as request:
        with pytest.raises(ServiceValidationError):
            await helpers.async_send_and_record(native_hass, entry, " ")
    request.assert_not_awaited()
    assert entry.runtime_data.api_reachable is None


@pytest.mark.asyncio
async def test_diagnostic_reachability_is_boolean_only(native_hass):
    entry = add_entry(native_hass)
    entry.runtime_data.api_reachable = "PRIVATE_LEGACY_VALUE"
    result = await diagnostics.async_get_config_entry_diagnostics(native_hass, entry)
    assert result["runtime"]["api_reachable"] is None
    assert "PRIVATE_" not in json.dumps(result)
    entry.runtime_data.api_reachable = False
    assert (await diagnostics.async_get_config_entry_diagnostics(native_hass, entry))["runtime"]["api_reachable"] is False


@pytest.mark.asyncio
async def test_disabled_status_still_records_without_writing_detached_states(native_hass):
    entry = add_entry(native_hass)
    status = sensor.FreeSMSSensor(entry)
    total = sensor.FreeSMSCountSensor(entry, status)
    today = sensor.FreeSMSTodaySensor(entry, status)
    status.bind(total, today)
    entry.runtime_data.sensor = status
    with patch.object(status, "async_write_ha_state") as write:
        status.notify_sent("body")
        status.notify_failed("body", "quota_exceeded")
        write.assert_not_called()
    assert status.sms_count == 1
    assert status.quota_status == "throttled"
    assert total.native_value == 1 and today.native_value == 1
    assert status.extra_state_attributes["api_reachable"] is None


@pytest.mark.asyncio
async def test_publish_updates_attached_status_and_counter_entities(native_hass):
    entry = add_entry(native_hass)
    status = sensor.FreeSMSSensor(entry)
    total = sensor.FreeSMSCountSensor(entry, status)
    today = sensor.FreeSMSTodaySensor(entry, status)
    status.bind(total, today)
    for entity, entity_id in [(status, "sensor.audit_status"), (total, "sensor.audit_total"), (today, "sensor.audit_today")]:
        await attach_to_native_platform(entity, native_hass, entity_id)
    entry.runtime_data.record_api_reachability(True)
    status.notify_sent("body")
    assert native_hass.states.get("sensor.audit_total").state == "1"
    assert native_hass.states.get("sensor.audit_today").state == "1"
    assert native_hass.states.get("sensor.audit_status").attributes["api_reachable"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("old_state,expected", [("Last sent", "Last sent"), ("unknown", "Idle"), ("unavailable", "Idle")])
async def test_restore_preserves_counters_and_strips_old_sms_text(native_hass, old_state, expected):
    entry = add_entry(native_hass)
    status = sensor.FreeSMSSensor(entry)
    fixed_now = datetime(2026, 11, 7, 10, tzinfo=ZoneInfo("Europe/Paris"))
    old = State("sensor.audit_status", old_state, {
        "sms_count": "7", "sms_today": "2", "sms_today_date": "2026-11-07",
        "last_sent": "2026-11-07T09:00:00+01:00", "last_error": "quota_exceeded", "quota_status": "throttled",
        "api_reachable": True,
        "sms_log": [{"message": "PRIVATE_OLD_BODY", "status": "sent", "length": 3}, "bad-item"],
    })
    with patch.object(RestoreEntity, "async_added_to_hass", new=AsyncMock()) as super_added, patch.object(status, "async_get_last_state", new=AsyncMock(return_value=old)), patch.object(sensor.dt_util, "now", return_value=fixed_now):
        await status.async_added_to_hass()
        assert status.sms_count == 7 and status.sms_today == 2
    super_added.assert_awaited_once()
    assert status.native_value == expected
    assert status.quota_status == "throttled"
    assert status.sms_log == [{"status": "sent", "length": 3}]
    assert "PRIVATE_" not in json.dumps(status.extra_state_attributes)
    # Restored transport state is not a live observation after restart.
    assert entry.runtime_data.api_reachable is None


@pytest.mark.asyncio
@pytest.mark.parametrize("log", [None, "bad-log"])
async def test_restore_no_history_or_malformed_log_stays_usable(native_hass, log):
    entry = add_entry(native_hass)
    status = sensor.FreeSMSSensor(entry)
    old = State("sensor.audit_status", "Idle", {"sms_log": log})
    with patch.object(RestoreEntity, "async_added_to_hass", new=AsyncMock()), patch.object(status, "async_get_last_state", new=AsyncMock(return_value=old)):
        await status.async_added_to_hass()
    assert status.sms_log == [] and status.sms_count == 0
    fresh = sensor.FreeSMSSensor(entry)
    with patch.object(RestoreEntity, "async_added_to_hass", new=AsyncMock()), patch.object(fresh, "async_get_last_state", new=AsyncMock(return_value=None)):
        await fresh.async_added_to_hass()
    assert fresh.sms_count == 0


@pytest.mark.asyncio
async def test_day_rollover_and_explicit_test_button_do_not_poll(native_hass):
    entry = add_entry(native_hass)
    status = sensor.FreeSMSSensor(entry)
    status._sms_today = 3
    status._sms_today_date = "2026-11-06"
    fixed_now = datetime(2026, 11, 7, 10, tzinfo=ZoneInfo("Europe/Paris"))
    with patch.object(sensor.dt_util, "now", return_value=fixed_now):
        assert status.sms_today == 0
    test_button = button.TestSMSButton(entry)
    await attach_to_native_platform(test_button, native_hass, "button.audit_test")
    with patch.object(button, "async_send_and_record", new=AsyncMock()) as send:
        await test_button.async_press()
    send.assert_awaited_once_with(native_hass, entry, "Keep Body", source="button")


@pytest.mark.asyncio
async def test_shared_lookup_and_missing_runtime_client(native_hass):
    entry = add_entry(native_hass)
    assert helpers.async_get_entry_by_username(native_hass, "12345678") is entry
    assert helpers.async_get_entry_by_username(native_hass, "not-configured") is None
    entry.runtime_data = None
    with pytest.raises(HomeAssistantError) as err:
        await helpers.async_send_and_record(native_hass, entry, "body")
    assert err.value.translation_key == "connection_error"


@pytest.mark.asyncio
async def test_diagnostic_categories_and_icons_preserve_unique_ids(native_hass):
    entry = add_entry(native_hass)
    root = Path(__file__).resolve().parents[1]
    icons = json.loads((root / "custom_components/freesmsxa/icons.json").read_text())["entity"]
    assert icons["sensor"]["sms_status"]["default"] == "mdi:message-text"
    assert icons["button"]["test_sms"]["default"] == "mdi:message-alert-outline"
    assert sensor.FreeSMSSensor(entry).entity_category == EntityCategory.DIAGNOSTIC
    assert button.TestSMSButton(entry).entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.FreeSMSCountSensor(entry, sensor.FreeSMSSensor(entry)).has_entity_name
    assert notify.FreeSMSNotifyEntity(entry).has_entity_name is True


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["status", "count", "today", "button", "notify"])
async def test_registry_metadata_refresh_keeps_custom_entity_id_name_and_icon(native_hass, kind):
    """Exercise the native registry update contract, without a naming migration."""
    from homeassistant.helpers import entity_registry as er
    entry = add_entry(native_hass)
    status = sensor.FreeSMSSensor(entry)
    entities = {
        "status": status,
        "count": sensor.FreeSMSCountSensor(entry, status),
        "today": sensor.FreeSMSTodaySensor(entry, status),
        "button": button.TestSMSButton(entry),
        "notify": notify.FreeSMSNotifyEntity(entry),
    }
    entity = entities[kind]
    domain = "sensor" if kind in ("status", "count", "today") else kind
    registry = er.async_get(native_hass)
    original = registry.async_get_or_create(domain, "freesmsxa", entity.unique_id,
        config_entry=entry, suggested_object_id="old_sms_alias")
    custom_id = f"{domain}.my_existing_sms"
    registry.async_update_entity(original.entity_id, new_entity_id=custom_id,
        name="My chosen name", icon="mdi:star")
    refreshed = registry.async_get_or_create(domain, "freesmsxa", entity.unique_id,
        config_entry=entry, suggested_object_id="different_new_default",
        entity_category=entity.entity_category, has_entity_name=entity.has_entity_name,
        original_icon=None, translation_key=entity.translation_key)
    assert refreshed.entity_id == custom_id
    assert refreshed.unique_id == entity.unique_id
    assert refreshed.name == "My chosen name" and refreshed.icon == "mdi:star"
    assert len(registry.entities) == 1
    assert refreshed.entity_category == (EntityCategory.DIAGNOSTIC if kind in ("status", "button") else None)


@pytest.mark.asyncio
async def test_counters_publish_before_status_add_and_after_status_removal(native_hass):
    entry = add_entry(native_hass)
    status = sensor.FreeSMSSensor(entry)
    total = sensor.FreeSMSCountSensor(entry, status)
    today = sensor.FreeSMSTodaySensor(entry, status)
    status.bind(total, today)
    await attach_to_native_platform(total, native_hass, "sensor.retained_total")
    await attach_to_native_platform(today, native_hass, "sensor.retained_today")
    status.notify_sent("before status was added")
    assert native_hass.states.get("sensor.retained_total").state == "1"
    await attach_to_native_platform(status, native_hass, "sensor.removed_status")
    await status.async_remove(force_remove=True)
    # Native HA removal does NOT clear entity.hass; checking hass alone is unsafe.
    assert status.hass is native_hass
    status.notify_sent("in-flight send completed after removal")
    assert native_hass.states.get("sensor.removed_status") is None
    assert native_hass.states.get("sensor.retained_total").state == "2"
    assert native_hass.states.get("sensor.retained_today").state == "2"
