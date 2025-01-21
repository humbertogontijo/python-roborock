"""The Roborock api."""

from __future__ import annotations

import asyncio
import base64
import logging
import secrets
import time
from abc import ABC, abstractmethod
from typing import Any

from .containers import (
    DeviceData,
)
from .exceptions import (
    RoborockTimeout,
    UnknownMethodError,
)
from .roborock_future import RoborockFuture
from .roborock_message import (
    RoborockMessage,
)
from .util import get_next_int, get_running_loop_or_create_one

_LOGGER = logging.getLogger(__name__)
KEEPALIVE = 60


class RoborockClient(ABC):
    """Roborock client base class."""

    _logger: logging.LoggerAdapter

    def __init__(self, device_info: DeviceData, queue_timeout: int = 4) -> None:
        """Initialize RoborockClient."""
        self.event_loop = get_running_loop_or_create_one()
        self.device_info = device_info
        self._nonce = secrets.token_bytes(16)
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._last_device_msg_in = time.monotonic()
        self._last_disconnection = time.monotonic()
        self.keep_alive = KEEPALIVE
        self._diagnostic_data: dict[str, dict[str, Any]] = {
            "misc_info": {"Nonce": base64.b64encode(self._nonce).decode("utf-8")}
        }
        self.is_available: bool = True
        self.queue_timeout = queue_timeout

    def __del__(self) -> None:
        self.release()

    def release(self) -> None:
        self.sync_disconnect()

    async def async_release(self) -> None:
        await self.async_disconnect()

    @property
    def diagnostic_data(self) -> dict:
        return self._diagnostic_data

    @abstractmethod
    async def async_connect(self):
        """Connect to the Roborock device."""

    @abstractmethod
    def sync_disconnect(self) -> Any:
        """Disconnect from the Roborock device."""

    @abstractmethod
    async def async_disconnect(self) -> Any:
        """Disconnect from the Roborock device."""

    @abstractmethod
    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        """Handle received incoming messages from the device."""

    def on_connection_lost(self, exc: Exception | None) -> None:
        self._last_disconnection = time.monotonic()
        self._logger.info("Roborock client disconnected")
        if exc is not None:
            self._logger.warning(exc)

    def should_keepalive(self) -> bool:
        now = time.monotonic()
        # noinspection PyUnresolvedReferences
        if now - self._last_disconnection > self.keep_alive**2 and now - self._last_device_msg_in > self.keep_alive:
            return False
        return True

    async def validate_connection(self) -> None:
        if not self.should_keepalive():
            await self.async_disconnect()
        await self.async_connect()

    async def _wait_response(self, request_id: int, queue: RoborockFuture) -> Any:
        try:
            response = await queue.async_get(self.queue_timeout)
            if response == "unknown_method":
                raise UnknownMethodError("Unknown method")
            return response
        except (asyncio.TimeoutError, asyncio.CancelledError):
            raise RoborockTimeout(f"id={request_id} Timeout after {self.queue_timeout} seconds") from None
        finally:
            self._waiting_queue.pop(request_id, None)

    def _async_response(self, request_id: int, protocol_id: int = 0) -> Any:
        queue = RoborockFuture(protocol_id)
        if request_id in self._waiting_queue:
            new_id = get_next_int(10000, 32767)
            self._logger.warning(
                "Attempting to create a future with an existing id %s (%s)... New id is %s. "
                "Code may not function properly.",
                request_id,
                protocol_id,
                new_id,
            )
            request_id = new_id
        self._waiting_queue[request_id] = queue
        return asyncio.ensure_future(self._wait_response(request_id, queue))

    @abstractmethod
    async def send_message(self, roborock_message: RoborockMessage):
        """Send a message to the Roborock device."""
