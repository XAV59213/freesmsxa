"""Hard guard: tests must not send HTTP requests to the real SMS API."""
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def block_real_http():
    from contextlib import ExitStack
    from importlib.util import find_spec
    targets = ["requests.sessions.Session.request", "aiohttp.ClientSession._request",
               "httpx.AsyncClient.send", "httpx.Client.send"]
    if find_spec("httpx2") is not None:
        targets += ["httpx2.AsyncClient.send", "httpx2.Client.send"]
    with ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, side_effect=AssertionError("REAL HTTP FORBIDDEN")))
        yield

import asyncio
import pytest_asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries
from homeassistant.helpers import entity_registry as er, device_registry as dr

@pytest_asyncio.fixture
async def native_hass(tmp_path):
    hass=HomeAssistant(str(tmp_path))
    hass.config_entries=ConfigEntries(hass,{})
    await hass.config_entries.async_initialize()
    if hasattr(dr, "async_setup"):
        dr.async_setup(hass)
    await asyncio.wait_for(dr.async_get(hass).async_load(), 10)
    await asyncio.wait_for(er.async_get(hass).async_load(), 10)
    with patch.object(hass.config_entries,"_async_schedule_save"):
        yield hass
        await hass.async_block_till_done()
    await hass.async_stop(force=True)
