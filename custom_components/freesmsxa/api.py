"""Typed boundary for the synchronous freesms client.

The upstream methods used here are unannotated and remain in the executor. This module models
only the constructor/method contract used here; it does not claim upstream is
asyncio-native or fully typed.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

from freesms import FreeClient as _FreeClient


class SMSResponse(Protocol):
    """HTTP result exposed by freesms."""

    @property
    def status_code(self) -> int:
        """HTTP response status."""


class SMSClient(Protocol):
    """Only the client contract used by this integration."""

    def send_sms(self, text: str, **kwargs: Any) -> SMSResponse:
        """Send to this client's own line, passing requests keyword arguments."""


FreeClient = cast(Callable[[str, str], SMSClient], _FreeClient)
