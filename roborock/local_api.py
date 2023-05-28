from __future__ import annotations

import asyncio
import logging
from asyncio import Lock, TimerHandle, Transport
from typing import Optional

import async_timeout

from . import DeviceData
from .api import COMMANDS_SECURED, QUEUE_TIMEOUT, RoborockClient
from .exceptions import CommandVacuumError, RoborockConnectionException, RoborockException
from .protocol import MessageParser
from .roborock_message import RoborockMessage, RoborockMessageProtocol
from .roborock_typing import CommandInfoMap, RoborockCommand
from .util import get_running_loop_or_create_one

_LOGGER = logging.getLogger(__name__)


class RoborockLocalClient(RoborockClient, asyncio.Protocol):
    def __init__(self, device_data: DeviceData):
        if device_data.host is None:
            raise RoborockException("Host is required")
        super().__init__("abc", device_data)
        self.loop = get_running_loop_or_create_one()
        self.host = device_data.host
        self._batch_structs: list[RoborockMessage] = []
        self._executing = False
        self.remaining = b""
        self.transport: Transport | None = None
        self._mutex = Lock()
        self.keep_alive_task: TimerHandle | None = None

    def data_received(self, message):
        if self.remaining:
            message = self.remaining + message
            self.remaining = b""
        parser_msg, self.remaining = MessageParser.parse(message, local_key=self.device_info.device.local_key)
        self.on_message_received(parser_msg)

    def connection_lost(self, exc: Optional[Exception]):
        self.sync_disconnect()
        self.on_connection_lost(exc)

    def is_connected(self):
        return self.transport and self.transport.is_reading()

    async def keep_alive_func(self, _=None):
        try:
            await self.ping()
        except RoborockException:
            pass
        self.keep_alive_task = self.loop.call_later(10, lambda: asyncio.create_task(self.keep_alive_func()))

    async def async_connect(self) -> None:
        should_ping = False
        async with self._mutex:
            try:
                if not self.is_connected():
                    self.sync_disconnect()
                    async with async_timeout.timeout(QUEUE_TIMEOUT):
                        _LOGGER.info(f"Connecting to {self.host}")
                        self.transport, _ = await self.loop.create_connection(  # type: ignore
                            lambda: self, self.host, 58867
                        )
                        _LOGGER.info(f"Connected to {self.host}")
                        should_ping = True
            except BaseException as e:
                raise RoborockConnectionException(f"Failed connecting to {self.host}") from e
        if should_ping:
            await self.hello()
            await self.keep_alive_func()

    def sync_disconnect(self) -> None:
        if self.transport and self.loop.is_running():
            _LOGGER.debug(f"Disconnecting from {self.host}")
            self.transport.close()
        if self.keep_alive_task:
            self.keep_alive_task.cancel()

    async def async_disconnect(self) -> None:
        async with self._mutex:
            self.sync_disconnect()

    def build_roborock_message(self, method: RoborockCommand, params: Optional[list | dict] = None) -> RoborockMessage:
        secured = True if method in COMMANDS_SECURED else False
        request_id, timestamp, payload = self._get_payload(method, params, secured)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        command_info = CommandInfoMap.get(method)
        if not command_info:
            raise RoborockException(f"Request {method} have unknown prefix. Can't execute in offline mode")
        command = CommandInfoMap.get(method)
        if command is None:
            raise RoborockException(f"No prefix found for {method}")
        request_protocol = 4
        return RoborockMessage(
            timestamp=timestamp,
            protocol=request_protocol,
            payload=payload,
        )

    async def hello(self):
        request_id = 1
        protocol = RoborockMessageProtocol.HELLO_REQUEST
        try:
            return await self.send_message(
                RoborockMessage(
                    protocol=protocol,
                    payload=None,
                    seq=request_id,
                    version=b"1.0",
                    random=22,
                )
            )
        except Exception as e:
            _LOGGER.error(e)

    async def ping(self):
        request_id = 2
        protocol = RoborockMessageProtocol.PING_REQUEST
        return await self.send_message(
            RoborockMessage(
                protocol=protocol,
                payload=None,
                seq=request_id,
                version=b"1.0",
                random=23,
            )
        )

    async def send_command(self, method: RoborockCommand, params: Optional[list | dict] = None):
        roborock_message = self.build_roborock_message(method, params)
        return (await self.send_message(roborock_message))[0]

    async def async_local_response(self, roborock_message: RoborockMessage):
        method = roborock_message.get_method()
        request_id: int | None
        if not method or not method.startswith("get"):
            request_id = roborock_message.seq
            response_protocol = request_id + 1
        else:
            request_id = roborock_message.get_request_id()
            response_protocol = 4
        if request_id is None:
            raise RoborockException(f"Failed build message {roborock_message}")
        (response, err) = await self._async_response(request_id, response_protocol)
        if err:
            raise CommandVacuumError("", err) from err
        if roborock_message.protocol == 4:
            _LOGGER.debug(f"id={request_id} Response from method {roborock_message.get_method()}: {response}")
        return response

    def _send_msg_raw(self, data: bytes):
        try:
            if not self.transport:
                raise RoborockException("Can not send message without connection")
            self.transport.write(data)
        except Exception as e:
            raise RoborockException(e) from e

    async def _send_message(self, roborock_messages: list[RoborockMessage] | RoborockMessage):
        if isinstance(roborock_messages, RoborockMessage):
            roborock_messages = [roborock_messages]
        local_key = self.device_info.device.local_key
        msg = MessageParser.build(roborock_messages, local_key=local_key)
        # Send the command to the Roborock device
        self._send_msg_raw(msg)

        responses = await asyncio.gather(
            *[self.async_local_response(roborock_message) for roborock_message in roborock_messages],
            return_exceptions=True,
        )
        exception = next(
            (response for response in responses if isinstance(response, BaseException)),
            None,
        )
        if exception:
            raise exception
        return responses

    async def send_message(self, roborock_messages: list[RoborockMessage] | RoborockMessage):
        await self.validate_connection()
        return await self._send_message(roborock_messages)
