from __future__ import annotations

import asyncio
import logging
from asyncio import Lock, TimerHandle, Transport

import async_timeout

from . import DeviceData
from .api import RoborockClient
from .exceptions import RoborockConnectionException, RoborockException
from .protocol import MessageParser
from .roborock_message import RoborockMessage, RoborockMessageProtocol
from .roborock_typing import RoborockCommand
from .util import RoborockLoggerAdapter

_LOGGER = logging.getLogger(__name__)


class RoborockLocalClient(RoborockClient, asyncio.Protocol):
    def __init__(self, device_data: DeviceData, queue_timeout: int = 4):
        if device_data.host is None:
            raise RoborockException("Host is required")
        self.host = device_data.host
        self._batch_structs: list[RoborockMessage] = []
        self._executing = False
        self.remaining = b""
        self.transport: Transport | None = None
        self._mutex = Lock()
        self.keep_alive_task: TimerHandle | None = None
        self._logger = RoborockLoggerAdapter(device_data.device.name, _LOGGER)
        RoborockClient.__init__(self, "abc", device_data, queue_timeout)

    def data_received(self, message):
        if self.remaining:
            message = self.remaining + message
            self.remaining = b""
        parser_msg, self.remaining = MessageParser.parse(message, local_key=self.device_info.device.local_key)
        self.on_message_received(parser_msg)

    def connection_lost(self, exc: Exception | None):
        self.sync_disconnect()
        self.on_connection_lost(exc)

    def is_connected(self):
        return self.transport and self.transport.is_reading()

    async def keep_alive_func(self, _=None):
        try:
            await self.ping()
        except RoborockException:
            pass
        self.keep_alive_task = self.event_loop.call_later(10, lambda: asyncio.create_task(self.keep_alive_func()))

    async def async_connect(self) -> None:
        should_ping = False
        async with self._mutex:
            try:
                if not self.is_connected():
                    self.sync_disconnect()
                    async with async_timeout.timeout(self.queue_timeout):
                        self._logger.debug(f"Connecting to {self.host}")
                        self.transport, _ = await self.event_loop.create_connection(  # type: ignore
                            lambda: self, self.host, 58867
                        )
                        self._logger.info(f"Connected to {self.host}")
                        should_ping = True
            except BaseException as e:
                raise RoborockConnectionException(f"Failed connecting to {self.host}") from e
        if should_ping:
            await self.hello()
            await self.keep_alive_func()

    def sync_disconnect(self) -> None:
        if self.transport and self.event_loop.is_running():
            self._logger.debug(f"Disconnecting from {self.host}")
            self.transport.close()
        if self.keep_alive_task:
            self.keep_alive_task.cancel()

    async def async_disconnect(self) -> None:
        async with self._mutex:
            self.sync_disconnect()

    async def hello(self):
        request_id = 1
        protocol = RoborockMessageProtocol.HELLO_REQUEST
        try:
            return await self.send_message(
                RoborockMessage(
                    protocol=protocol,
                    seq=request_id,
                    random=22,
                )
            )
        except Exception as e:
            self._logger.error(e)

    async def ping(self) -> None:
        request_id = 2
        protocol = RoborockMessageProtocol.PING_REQUEST
        return await self.send_message(
            RoborockMessage(
                protocol=protocol,
                seq=request_id,
                random=23,
            )
        )

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        raise NotImplementedError

    def _send_msg_raw(self, data: bytes):
        try:
            if not self.transport:
                raise RoborockException("Can not send message without connection")
            self.transport.write(data)
        except Exception as e:
            raise RoborockException(e) from e
