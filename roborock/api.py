"""The Roborock api."""

from __future__ import annotations

import asyncio
import base64
import logging
import secrets
import time
from collections.abc import Callable, Coroutine
from typing import Any

from .containers import (
    DeviceData,
)
from .exceptions import (
    RoborockTimeout,
    UnknownMethodError,
    VacuumError,
)
from .roborock_future import RoborockFuture
from .roborock_message import (
    RoborockMessage,
)
from .roborock_typing import RoborockCommand
from .util import RoborockLoggerAdapter, get_running_loop_or_create_one

_LOGGER = logging.getLogger(__name__)
KEEPALIVE = 60


class RoborockClient:
    def __init__(self, endpoint: str, device_info: DeviceData, queue_timeout: int = 4) -> None:
        self.event_loop = get_running_loop_or_create_one()
        self.device_info = device_info
        self._endpoint = endpoint
        self._nonce = secrets.token_bytes(16)
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._last_device_msg_in = self.time_func()
        self._last_disconnection = self.time_func()
        self.keep_alive = KEEPALIVE
        self._diagnostic_data: dict[str, dict[str, Any]] = {
            "misc_info": {"Nonce": base64.b64encode(self._nonce).decode("utf-8")}
        }
        self._logger = RoborockLoggerAdapter(device_info.device.name, _LOGGER)
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

    @property
    def time_func(self) -> Callable[[], float]:
        try:
            # Use monotonic clock if available
            time_func = time.monotonic
        except AttributeError:
            time_func = time.time
        return time_func

    async def async_connect(self):
        raise NotImplementedError

    def sync_disconnect(self) -> Any:
        raise NotImplementedError

    async def async_disconnect(self) -> Any:
        raise NotImplementedError

    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        raise NotImplementedError

    def on_connection_lost(self, exc: Exception | None) -> None:
        self._last_disconnection = self.time_func()
        self._logger.info("Roborock client disconnected")
        if exc is not None:
            self._logger.warning(exc)

    def should_keepalive(self) -> bool:
        now = self.time_func()
        # noinspection PyUnresolvedReferences
        if now - self._last_disconnection > self.keep_alive**2 and now - self._last_device_msg_in > self.keep_alive:
            return False
        return True

    async def validate_connection(self) -> None:
        if not self.should_keepalive():
            await self.async_disconnect()
        await self.async_connect()

    async def _wait_response(self, request_id: int, queue: RoborockFuture) -> tuple[Any, VacuumError | None]:
        try:
            (response, err) = await queue.async_get(self.queue_timeout)
            if response == "unknown_method":
                raise UnknownMethodError("Unknown method")
            return response, err
        except (asyncio.TimeoutError, asyncio.CancelledError):
            raise RoborockTimeout(f"id={request_id} Timeout after {self.queue_timeout} seconds") from None
        finally:
            self._waiting_queue.pop(request_id, None)

    def _async_response(
        self, request_id: int, protocol_id: int = 0
    ) -> Coroutine[Any, Any, tuple[Any, VacuumError | None]]:
        queue = RoborockFuture(protocol_id)
        self._waiting_queue[request_id] = queue
        return self._wait_response(request_id, queue)

    async def send_message(self, roborock_message: RoborockMessage):
        raise NotImplementedError

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        raise NotImplementedError
