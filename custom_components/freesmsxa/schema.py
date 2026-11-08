"""Use HA's actual validation engine for both runtime and static checking.

PLATFORM_SCHEMA is a public HA schema on both supported endpoints. Its class
selects the real native engine, without importing a different library only for
TYPE_CHECKING. Only the two standard marker factories are loaded from that same
engine; their callable and hashable contracts are checked before use.
"""
from __future__ import annotations

from collections.abc import Hashable
from importlib import import_module
from typing import Any

from homeassistant.helpers.config_validation import PLATFORM_SCHEMA

Schema = type(PLATFORM_SCHEMA)
_ENGINE = import_module(Schema.__module__.partition(".")[0])


def _marker(kind: str, key: str, **kwargs: Any) -> Hashable:
    factory: object = getattr(_ENGINE, kind)
    if not callable(factory):
        raise TypeError("HA validation marker is not callable")
    marker: object = factory(key, **kwargs)
    if not isinstance(marker, Hashable):
        raise TypeError("HA validation marker is not hashable")
    return marker


def Required(key: str, **kwargs: Any) -> Hashable:
    """Create the required marker belonging to HA's native schema engine."""
    return _marker("Required", key, **kwargs)


def Optional(key: str, **kwargs: Any) -> Hashable:
    """Create the optional marker belonging to HA's native schema engine."""
    return _marker("Optional", key, **kwargs)
