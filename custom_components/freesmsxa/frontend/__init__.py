"""Register the Lovelace send-SMS card with Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import JSMODULES, URL_BASE

_LOGGER = logging.getLogger(__name__)


def _lovelace_data(hass: HomeAssistant) -> Any:
    """Return Lovelace storage across HA versions."""
    return hass.data.get("lovelace")


def _resource_mode(lovelace: Any) -> str | None:
    if lovelace is None:
        return None
    if isinstance(lovelace, dict):
        return lovelace.get("resource_mode") or lovelace.get("mode")
    return getattr(lovelace, "resource_mode", None) or getattr(lovelace, "mode", None)


def _resources(lovelace: Any) -> Any:
    if lovelace is None:
        return None
    if isinstance(lovelace, dict):
        return lovelace.get("resources")
    return getattr(lovelace, "resources", None)


class JSModuleRegistration:
    """Serve and register the FreeSMS XA Lovelace card."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_register(self) -> None:
        """Expose JS files and register them as Lovelace resources."""
        await self._async_register_path()
        for module in JSMODULES:
            add_extra_js_url(
                self.hass,
                f"{URL_BASE}/{module['filename']}?v={module['version']}",
            )

        if self.hass.is_running:
            await self._async_register_lovelace_resources()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._async_started
            )

    async def _async_started(self, _event: Event) -> None:
        await self._async_register_lovelace_resources()

    async def _async_register_path(self) -> None:
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, Path(__file__).parent, False)]
            )
        except RuntimeError:
            _LOGGER.debug("Static path already registered: %s", URL_BASE)

    async def _async_register_lovelace_resources(self) -> None:
        lovelace = _lovelace_data(self.hass)
        if _resource_mode(lovelace) not in (None, "storage", "yaml"):
            return
        resources = _resources(lovelace)
        if resources is None:
            async_call_later(self.hass, 5, self._retry_resources)
            return
        if not getattr(resources, "loaded", True):
            load = getattr(resources, "async_load", None)
            if callable(load):
                await load()
        await self._async_register_modules(resources)

    async def _retry_resources(self, _now: Any) -> None:
        await self._async_register_lovelace_resources()

    async def _async_register_modules(self, resources: Any) -> None:
        try:
            items = list(resources.async_items())
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Lovelace resources not ready yet")
            async_call_later(self.hass, 5, self._retry_resources)
            return

        existing = [
            item for item in items if str(item.get("url", "")).startswith(URL_BASE)
        ]
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            versioned = f"{url}?v={module['version']}"
            found = False
            for resource in existing:
                if resource["url"].split("?")[0] == url:
                    found = True
                    current = (
                        resource["url"].split("v=")[-1]
                        if "v=" in resource["url"]
                        else "0"
                    )
                    if current != module["version"]:
                        await resources.async_update_item(
                            resource["id"],
                            {"res_type": "module", "url": versioned},
                        )
                    break
            if not found:
                _LOGGER.info("Registering Lovelace module %s", versioned)
                await resources.async_create_item(
                    {"res_type": "module", "url": versioned}
                )
