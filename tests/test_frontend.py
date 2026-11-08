"""Behavioral checks of serving, resource sync, bounded retries and startup hooks."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path
import pytest

from custom_components.freesmsxa import frontend as front
from custom_components.freesmsxa.const import STATIC_CARD_PATH, VERSION, URL_BASE


def resources(*, items=(), loaded=True):
    return NS(
        loaded=loaded,
        async_load=AsyncMock(),
        async_items=Mock(return_value=list(items)),
        async_create_item=AsyncMock(),
        async_update_item=AsyncMock(),
    )


def frontend_hass(resource=None, running=True):
    return NS(
        data={"lovelace": {"resources": resource}},
        is_running=running,
        http=NS(async_register_static_paths=AsyncMock(), register_view=Mock()),
        bus=NS(async_listen_once=Mock()),
        async_create_task=Mock(),
    )


@pytest.mark.parametrize("value,expected", [(None, None), ({}, None), ({"resources": 42}, 42), (NS(resources=42), 42), (NS(), None)])
def test_resource_shapes(value, expected):
    assert front._resources(value) == expected
    assert front._path_only("/path.js?v=old") == "/path.js"
    assert front._lovelace_data(NS(data={"lovelace": value})) is value


@pytest.mark.asyncio
async def test_card_view_serves_bundled_js_via_real_executor(native_hass):
    response = await front.FreeSMSXACardView().get(NS(app={"hass": native_hass}))
    expected = (Path(front.__file__).parent / "freesmsxa-send-card.js").read_text()
    assert response.text == expected
    assert response.content_type == "text/javascript"
    assert response.headers["Cache-Control"] == "no-cache"
    assert not front.FreeSMSXACardView.requires_auth


@pytest.mark.asyncio
async def test_registration_when_running_preserves_existing_resources():
    existing = [{"id": "other", "url": "/other.js", "res_type": "module"}]
    res = resources(items=existing)
    hass = frontend_hass(res)
    reg = front.JSModuleRegistration(hass)
    with patch.object(front, "add_extra_js_url") as extra:
        await reg.async_register()
    config = hass.http.async_register_static_paths.call_args.args[0][0]
    assert config.url_path == URL_BASE
    assert isinstance(config.path, str)
    hass.http.register_view.assert_called_once()
    extra.assert_called_once_with(hass, f"{STATIC_CARD_PATH}?v={VERSION}")
    res.async_create_item.assert_awaited_once_with({"res_type": "module", "url": f"{STATIC_CARD_PATH}?v={VERSION}"})
    res.async_update_item.assert_not_awaited()
    assert existing[0]["url"] == "/other.js"


@pytest.mark.asyncio
async def test_registration_repeated_before_start_only_one_listener():
    hass = frontend_hass(resources(), running=False)
    reg = front.JSModuleRegistration(hass)
    reg._async_register_lovelace_resources = AsyncMock()
    tasks = []
    hass.async_create_task.side_effect = lambda coro: tasks.append(asyncio.create_task(coro))
    with patch.object(front, "add_extra_js_url"):
        await reg.async_register()
        await reg.async_register()
    hass.bus.async_listen_once.assert_called_once()
    reg._async_register_lovelace_resources.assert_not_awaited()
    callback = hass.bus.async_listen_once.call_args.args[1]
    callback(NS())
    await asyncio.gather(*tasks)
    reg._async_register_lovelace_resources.assert_awaited_once()


@pytest.mark.asyncio
async def test_already_registered_http_paths_and_view_do_not_break_resources():
    hass = frontend_hass(resources())
    hass.http.async_register_static_paths.side_effect = RuntimeError("existing static path")
    hass.http.register_view.side_effect = RuntimeError("existing view")
    with patch.object(front, "add_extra_js_url"):
        await front.JSModuleRegistration(hass).async_register()
    hass.data["lovelace"]["resources"].async_create_item.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("loaded", [False, True])
async def test_resource_loading_and_sync(loaded):
    res = resources(loaded=loaded)
    reg = front.JSModuleRegistration(frontend_hass(res))
    await reg._async_register_lovelace_resources()
    assert res.async_load.await_count == (0 if loaded else 1)
    res.async_items.assert_called_once()
    res.async_create_item.assert_awaited_once()


@pytest.mark.asyncio
async def test_legacy_resource_object_without_load_method():
    res = resources()
    del res.async_load
    reg = front.JSModuleRegistration(frontend_hass(res))
    await reg._async_register_lovelace_resources()
    res.async_create_item.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure,reason", [("missing", "Lovelace resources not available yet"), ("load", "async_load failed"), ("items", "async_items failed"), ("sync", "create/update failed")])
async def test_resource_errors_schedule_retry_instead_of_corrupting_other_resources(failure, reason):
    res = resources(loaded=False)
    if failure == "load":
        res.async_load.side_effect = RuntimeError("not ready")
    elif failure == "items":
        res.async_items.side_effect = RuntimeError("not loaded")
    elif failure == "sync":
        res.async_create_item.side_effect = RuntimeError("cannot create")
    reg = front.JSModuleRegistration(frontend_hass(None if failure == "missing" else res))
    with patch.object(reg, "_schedule_retry") as retry:
        await reg._async_register_lovelace_resources()
    retry.assert_called_once_with(reason)
    res.async_update_item.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_is_bounded_and_callback_retries_once(caplog):
    import logging
    reg = front.JSModuleRegistration(frontend_hass())
    caplog.set_level(logging.WARNING, logger="custom_components.freesmsxa.frontend")
    with patch.object(front, "async_call_later") as later:
        for _ in range(front._MAX_RESOURCE_RETRIES + 2):
            reg._schedule_retry("not ready")
    assert later.call_count == front._MAX_RESOURCE_RETRIES
    assert reg._retries == front._MAX_RESOURCE_RETRIES
    assert "Add" in caplog.text and STATIC_CARD_PATH in caplog.text
    reg._async_register_lovelace_resources = AsyncMock()
    await reg._retry_resources(None)
    reg._async_register_lovelace_resources.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("old_version", ["old", "6.12.8", "6.12.12"])
async def test_resource_sync_only_changes_matching_outdated_url(old_version):
    res = resources()
    reg = front.JSModuleRegistration(frontend_hass(res))
    versioned = f"{STATIC_CARD_PATH}?v={VERSION}"
    items = [
        {"id": "old", "url": f"{STATIC_CARD_PATH}?v={old_version}"},
        {"id": "current", "url": versioned},
        {"id": "other", "url": "/unrelated.js?v=old"},
    ]
    await reg._async_sync_modules(res, items)
    res.async_update_item.assert_awaited_once_with("old", {"res_type": "module", "url": versioned})
    res.async_create_item.assert_not_awaited()
    assert items[2]["url"] == "/unrelated.js?v=old"
