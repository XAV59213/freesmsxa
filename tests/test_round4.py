"""Observed availability and retries through HA's actual entity-action dispatcher."""
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch
import pytest
import voluptuous as vol
from homeassistant.core import HassJobType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import service
from custom_components import freesmsxa as integration
from custom_components.freesmsxa import sensor, notify, button, helpers
from test_round2 import add_entry
from test_round3 import attach_to_native_platform


async def make_entities(hass):
    entry = add_entry(hass)
    status = sensor.FreeSMSSensor(entry)
    count = sensor.FreeSMSCountSensor(entry, status)
    today = sensor.FreeSMSTodaySensor(entry, status)
    command = notify.FreeSMSNotifyEntity(entry)
    retry = button.TestSMSButton(entry)
    status.bind(count, today)
    entry.runtime_data.sensor = status
    for entity, entity_id in [(status, 'sensor.round4_status'), (count, 'sensor.round4_count'),
            (today, 'sensor.round4_today'), (command, 'notify.round4_line'),
            (retry, 'button.round4_retry')]:
        await attach_to_native_platform(entity, hass, entity_id)
    service.async_register_entity_service(hass, 'notify', 'send_message',
        entities={command.entity_id: command}, func='async_send_message',
        job_type=HassJobType.Coroutinefunction, schema={vol.Required('message'): str})
    service.async_register_entity_service(hass, 'button', 'press',
        entities={retry.entity_id: retry}, func='async_press',
        job_type=HassJobType.Coroutinefunction, schema={})
    return entry, status, count, today, command, retry


@pytest.mark.asyncio
@pytest.mark.parametrize('retry_domain', ['notify', 'button'])
async def test_native_entity_action_recovers_without_probing_or_blocking_retry(native_hass, retry_domain, caplog):
    entry, status, count, today, command, retry = await make_entities(native_hass)
    entry.runtime_data.client.send_sms.side_effect = [OSError('PRIVATE_TRANSPORT_DETAILS'), NS(status_code=200)]
    assert entry.runtime_data.api_reachable is None
    assert native_hass.states.get(status.entity_id).state == 'Idle'
    entry.runtime_data.client.send_sms.assert_not_called()
    # HA does its real entity-target and available checks, not a hand-written handler.
    with pytest.raises(HomeAssistantError) as err:
        await native_hass.services.async_call('notify', 'send_message',
            {'entity_id': command.entity_id, 'message': 'PRIVATE_BODY'}, blocking=True)
    assert err.value.translation_key == 'connection_error'
    assert native_hass.states.get(status.entity_id).state == 'unavailable'
    assert native_hass.states.get(count.entity_id).state == '0'
    assert native_hass.states.get(today.entity_id).state == '0'
    assert command.available and retry.available
    await native_hass.async_block_till_done()
    assert entry.runtime_data.client.send_sms.call_count == 1  # no hidden recovery probe
    if retry_domain == 'notify':
        await native_hass.services.async_call('notify', 'send_message',
            {'entity_id': command.entity_id, 'message': 'PRIVATE_BODY'}, blocking=True)
    else:
        await native_hass.services.async_call('button', 'press', {'entity_id': retry.entity_id}, blocking=True)
    assert native_hass.states.get(status.entity_id).state == 'Last sent'
    assert native_hass.states.get(count.entity_id).state == '1'
    assert native_hass.states.get(today.entity_id).state == '1'
    assert entry.runtime_data.api_reachable is True
    assert entry.runtime_data.client.send_sms.call_count == 2
    assert 'PRIVATE_' not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize('status_code', [400, 402, 403, 418, 500])
async def test_http_error_restores_observed_connection_without_pretending_delivery(native_hass, status_code):
    entry, status, count, today, command, retry = await make_entities(native_hass)
    entry.runtime_data.record_api_reachability(False)
    status.notify_failed('body', 'connection_error')
    assert native_hass.states.get(status.entity_id).state == 'unavailable'
    entry.runtime_data.client.send_sms.return_value = NS(status_code=status_code)
    with patch.object(native_hass.config_entries.flow, 'async_init', new=AsyncMock(return_value={'type': 'abort'})), patch.object(helpers.asyncio, 'sleep', new=AsyncMock()):
        with pytest.raises(HomeAssistantError):
            await native_hass.services.async_call('notify', 'send_message',
                {'entity_id': command.entity_id, 'message': 'body'}, blocking=True)
        await native_hass.async_block_till_done()
    assert status.available and entry.runtime_data.api_reachable is True
    assert native_hass.states.get(status.entity_id).state == ('Quota' if status_code == 402 else 'Error')
    assert native_hass.states.get(count.entity_id).state == '0'
    assert native_hass.states.get(today.entity_id).state == '0'


@pytest.mark.asyncio
async def test_actual_entry_setup_does_not_send_sms(native_hass):
    entry = add_entry(native_hass)
    with patch.object(native_hass.config_entries, 'async_forward_entry_setups', new=AsyncMock()) as forward, patch('requests.get', side_effect=AssertionError('NETWORK FORBIDDEN')) as sms:
        assert await integration.async_setup_entry(native_hass, entry)
    sms.assert_not_called()
    assert entry.runtime_data.api_reachable is None
    forward.assert_awaited_once()


def test_local_brand_icons_are_square_rgba_png():
    from pathlib import Path
    import struct
    root = Path(__file__).resolve().parents[1] / 'custom_components/freesmsxa/brand'
    for name, size in [('icon.png', 256), ('icon@2x.png', 512)]:
        data = (root / name).read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II', data[16:24]) == (size, size)
        assert data[25] == 6  # RGBA, transparent background; no brand recoloring



def test_manifest_keeps_core_compatible_dependency_and_cache_version():
    import importlib.metadata
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'custom_components/freesmsxa/manifest.json').read_text())
    from custom_components.freesmsxa.const import VERSION
    assert manifest['version'] == VERSION
    assert manifest['requirements'] == ['freesms>=0.2.0']
    from packaging.requirements import Requirement
    # The built-in core integration also uses this library in the same Python process.
    import homeassistant
    builtin = json.loads((Path(homeassistant.__file__).parent / 'components/free_mobile/manifest.json').read_text())
    ours = Requirement(manifest['requirements'][0])
    core_requirements = [Requirement(spec) for spec in builtin['requirements']
                         if Requirement(spec).name == 'freesms']
    assert len(core_requirements) == 1
    exact = [spec.version for spec in core_requirements[0].specifier if spec.operator == '==']
    assert len(exact) == 1
    assert ours.specifier.contains(exact[0])
    assert ours.specifier.contains(importlib.metadata.version('freesms'))
