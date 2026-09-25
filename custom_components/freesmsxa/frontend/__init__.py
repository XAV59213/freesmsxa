"""Register the Lovelace send-SMS card with Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from ..const import CARD_FILENAME, JSMODULES, LOCAL_CARD_PATH, URL_BASE, VERSION

_LOGGER = logging.getLogger(__name__)

_MAX_RESOURCE_RETRIES = 12
_RETRY_SECONDS = 5


def _lovelace_data(hass: HomeAssistant) -> Any:
    return hass.data.get("lovelace")


def _resources(lovelace: Any) -> Any:
    if lovelace is None:
        return None
    if isinstance(lovelace, dict):
        return lovelace.get("resources")
    return getattr(lovelace, "resources", None)


def _path_only(url: str) -> str:
    return str(url).split("?", 1)[0]


def _copy_card_to_www(hass: HomeAssistant) -> Path:
    """Copy the card JS into /config/www so Lovelace can load /local/."""
    src = Path(__file__).parent / CARD_FILENAME
    dest = Path(hass.config.path("www")) / CARD_FILENAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return dest


class JSModuleRegistration:
    """Serve and register the FreeSMS XA Lovelace card."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._retries = 0
        self._started_listen = False

    async def async_register(self) -> None:
        """Expose JS files and register them as Lovelace resources."""
        await self._async_register_path()
        await self.hass.async_add_executor_job(_copy_card_to_www, self.hass)

        versioned_static = f"{URL_BASE}/{CARD_FILENAME}?v={VERSION}"
        versioned_local = f"{LOCAL_CARD_PATH}?v={VERSION}"
        add_extra_js_url(self.hass, versioned_static)
        add_extra_js_url(self.hass, versioned_local)

        if self.hass.is_running:
            await self._async_register_lovelace_resources()
        elif not self._started_listen:
            self._started_listen = True

            @callback
            def _schedule_started(_event: Event) -> None:
                self.hass.async_create_task(self._async_register_lovelace_resources())

            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _schedule_started)

    async def _async_register_path(self) -> None:
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, Path(__file__).parent, False)]
            )
        except RuntimeError:
            _LOGGER.debug("Static path already registered: %s", URL_BASE)

    async def _async_register_lovelace_resources(self) -> None:
        resources = _resources(_lovelace_data(self.hass))
        if resources is None:
            self._schedule_retry("Lovelace resources not available yet")
            return

        load = getattr(resources, "async_load", None)
        if callable(load) and not getattr(resources, "loaded", False):
            try:
                await load()
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Could not load Lovelace resources yet", exc_info=True)
                self._schedule_retry("async_load failed")
                return

        try:
            items = list(resources.async_items())
        except Exception:  # noqa: BLE001
            self._schedule_retry("async_items failed")
            return

        try:
            await self._async_sync_modules(resources, items)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to register Lovelace card resource")
            self._schedule_retry("create/update failed")

    def _schedule_retry(self, reason: str) -> None:
        if self._retries >= _MAX_RESOURCE_RETRIES:
            _LOGGER.warning(
                "Could not auto-register the Lovelace card after %s tries (%s). "
                "Add %s as a JavaScript module in Settings > Dashboards > Resources",
                _MAX_RESOURCE_RETRIES,
                reason,
                f"{LOCAL_CARD_PATH}?v={VERSION}",
            )
            return
        self._retries += 1
        _LOGGER.debug("Retry %s/%s registering card: %s", self._retries, _MAX_RESOURCE_RETRIES, reason)
        async_call_later(self.hass, _RETRY_SECONDS, self._retry_resources)

    async def _retry_resources(self, _now: Any) -> None:
        await self._async_register_lovelace_resources()

    async def _async_sync_modules(self, resources: Any, items: list[dict]) -> None:
        """Ensure one up-to-date module resource exists."""
        wanted_paths = {LOCAL_CARD_PATH, f"{URL_BASE}/{CARD_FILENAME}"}
        versioned_local = f"{LOCAL_CARD_PATH}?v={VERSION}"

        matching = [
            item
            for item in items
            if _path_only(item.get("url", "")) in wanted_paths
        ]

        if matching:
            primary = matching[0]
            current = _path_only(primary.get("url", ""))
            current_ver = "0"
            if "v=" in str(primary.get("url", "")):
                current_ver = str(primary["url"]).split("v=", 1)[1]
            if current != LOCAL_CARD_PATH or current_ver != VERSION:
                await resources.async_update_item(
                    primary["id"],
                    {"res_type": "module", "url": versioned_local},
                )
                _LOGGER.info("Updated Lovelace card resource to %s", versioned_local)
            for extra in matching[1:]:
                delete = getattr(resources, "async_delete_item", None)
                if callable(delete):
                    await delete(extra["id"])
            return

        await resources.async_create_item(
            {"res_type": "module", "url": versioned_local}
        )
        _LOGGER.info("Registered Lovelace card resource %s", versioned_local)
