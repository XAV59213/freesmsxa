"""Register the Lovelace send-SMS card with Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import JSMODULES, URL_BASE

_LOGGER = logging.getLogger(__name__)


class JSModuleRegistration:
    """Serve and register the FreeSMS XA Lovelace card."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.lovelace = self.hass.data.get("lovelace")

    async def async_register(self) -> None:
        """Expose JS files and register them as Lovelace resources."""
        await self._async_register_path()
        for module in JSMODULES:
            add_extra_js_url(
                self.hass,
                f"{URL_BASE}/{module['filename']}?v={module['version']}",
            )

        if self.lovelace is not None and getattr(self.lovelace, "mode", None) == "storage":
            await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, Path(__file__).parent, False)]
            )
        except RuntimeError:
            _LOGGER.debug("Static path already registered: %s", URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        async def _check_loaded(_now: Any) -> None:
            resources = getattr(self.lovelace, "resources", None)
            if resources is not None and getattr(resources, "loaded", False):
                await self._async_register_modules()
                return
            async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(0)

    async def _async_register_modules(self) -> None:
        resources = self.lovelace.resources
        existing = [
            item
            for item in resources.async_items()
            if str(item.get("url", "")).startswith(URL_BASE)
        ]
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            versioned = f"{url}?v={module['version']}"
            found = False
            for resource in existing:
                if resource["url"].split("?")[0] == url:
                    found = True
                    current = resource["url"].split("v=")[-1] if "v=" in resource["url"] else "0"
                    if current != module["version"]:
                        await resources.async_update_item(
                            resource["id"],
                            {"res_type": "module", "url": versioned},
                        )
                    break
            if not found:
                await resources.async_create_item(
                    {"res_type": "module", "url": versioned}
                )
