"""Idempotent metadata migration before the notify platform is loaded."""
from __future__ import annotations

from inspect import signature
from typing import Protocol, runtime_checkable

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryError
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


@runtime_checkable
class _CompatNameUpdate(Protocol):
    """The single native legacy-cache operation required by this migration."""

    def __call__(
        self, entity_id: str, *, name: str, has_entity_name: bool, compat_name: str
    ) -> object:
        """Update metadata while keeping an existing compatibility cache."""


def _preserve_compat_name(
    registry: er.EntityRegistry, entity_id: str, name: str, compat_name: str
) -> None:
    """Check the private contract before touching an existing compatibility name.

    The public updater cannot retain this field. Do not pretend the old HA
    updater supports it: bind this exact keyword contract first and fail closed
    on API drift, without clearing names or putting their values in an error.
    """
    update: object = getattr(registry, "_async_update_entity", None)
    if not isinstance(update, _CompatNameUpdate):
        raise ConfigEntryError(translation_domain=DOMAIN, translation_key="unsupported_ha_contract")
    try:
        signature(update).bind(
            entity_id, name=name, has_entity_name=True, compat_name=compat_name
        )
    except (TypeError, ValueError):
        raise ConfigEntryError(translation_domain=DOMAIN, translation_key="unsupported_ha_contract") from None
    update(entity_id, name=name, has_entity_name=True, compat_name=compat_name)


@callback
def async_migrate_notify_name(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Retain registry identity and chosen legacy names; never generate IDs again.

    No config schema/version change is needed. has_entity_name is the migration
    marker. A user clearing the retained name later opts into translated defaults.
    Only this entry's original notify entity is touched, including if disabled.
    """
    registry = er.async_get(hass)
    username = entry.data[CONF_USERNAME]
    entity_id = registry.async_get_entity_id(
        "notify", DOMAIN, f"freesmsxa_notify_{username}"
    )
    if entity_id is None:
        return
    old = registry.async_get(entity_id)
    if old is None or old.config_entry_id != entry.entry_id or old.has_entity_name:
        return

    # The old configured alias was the entire notify name. Keep it as a name
    # override unless it was the implicit account-ID fallback. Explicit registry
    # names, even empty strings or an account ID, are always the user's choice.
    name = old.name
    if name is None and old.original_name and old.original_name.strip() != username:
        # Modern HA already calculated the unprefixed part. Reusing it avoids
        # repeating the device prefix when this legacy name becomes an override.
        fallback_name = getattr(old, "entity_name", old.original_name)
        if fallback_name.strip() != username:
            name = fallback_name

    compat_name = getattr(old, "compat_name", None)
    if isinstance(compat_name, str) and name is not None:
        # Only an existing native HA compatibility name needs the isolated
        # internal shim. The public preserve-as-alias helper changes aliases,
        # not the state's friendly_name; that is not an equivalent migration.
        _preserve_compat_name(registry, entity_id, name, compat_name)
    else:
        # Normal migrations, old HA and implicit username fallback all use the
        # public API. Do not manufacture a compatibility cache for normal names.
        registry.async_update_entity(entity_id, name=name, has_entity_name=True)
