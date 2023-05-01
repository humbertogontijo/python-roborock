from __future__ import annotations

import async_timeout
import asyncio
import logging
from asyncio import Lock, Transport
from typing import Optional

from .api import QUEUE_TIMEOUT, RoborockClient, SPECIAL_COMMANDS
from .containers import RoborockLocalDeviceInfo
from .exceptions import CommandVacuumError, RoborockConnectionException, RoborockException
from .roborock_message import AP_CONFIG, RoborockMessage, RoborockParser
from .roborock_typing import CommandInfoMap, RoborockCommand
from .util import get_running_loop_or_create_one

_LOGGER = logging.getLogger(__name__)


class RoborockLocalClient(RoborockClient, asyncio.Protocol):
    def __init__(self, device_info: RoborockLocalDeviceInfo):
        super().__init__("abc", device_info)
        self.loop = get_running_loop_or_create_one()
        self.ip = device_info.network_info.ip
        self._batch_structs: list[RoborockMessage] = []
        self._executing = False
        self.remaining = b""
        self.transport: Transport | None = None
        self._mutex = Lock()

    def data_received(self, message):
        if self.remaining:
            message = self.remaining + message
            self.remaining = b""
        (parser_msg, remaining) = RoborockParser.decode(message, self.device_info.device.local_key)
        self.remaining = remaining
        self.on_message_received(parser_msg)

    def connection_lost(self, exc: Optional[Exception]):
        self.on_connection_lost(exc)

    def is_connected(self):
        return self.transport and self.transport.is_reading()

    async def async_connect(self) -> None:
        async with self._mutex:
            try:
                if not self.is_connected():
                    async with async_timeout.timeout(QUEUE_TIMEOUT):
                        _LOGGER.info(f"Connecting to {self.ip}")
                        self.transport, _ = await self.loop.create_connection(  # type: ignore
                            lambda: self, self.ip, 58867
                        )
                        _LOGGER.info(f"Connected to {self.ip}")
            except Exception as e:
                raise RoborockConnectionException(f"Failed connecting to {self.ip}") from e

    def sync_disconnect(self) -> None:
        if self.transport and not self.loop.is_closed():
            self.transport.close()

    async def async_disconnect(self) -> None:
        async with self._mutex:
            self.sync_disconnect()

    def build_roborock_message(self, method: RoborockCommand, params: Optional[list | dict] = None) -> RoborockMessage:
        secured = True if method in SPECIAL_COMMANDS else False
        request_id, timestamp, payload = self._get_payload(method, params, secured)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        command_info = CommandInfoMap.get(method)
        if not command_info:
            raise RoborockException(f"Request {method} have unknown prefix. Can't execute in offline mode")
        command = CommandInfoMap.get(method)
        if command is None:
            raise RoborockException(f"No prefix found for {method}")
        prefix = command.prefix
        request_protocol = 4
        return RoborockMessage(
            prefix=prefix,
            timestamp=timestamp,
            protocol=request_protocol,
            payload=payload,
        )

    async def ping(self):
        command_info = CommandInfoMap[RoborockCommand.NONE]
        roborock_message = RoborockMessage(prefix=command_info.prefix, protocol=AP_CONFIG, payload=b"")
        return (await self.send_message(roborock_message))[0]

    async def send_command(self, method: RoborockCommand, params: Optional[list | dict] = None):
        roborock_message = self.build_roborock_message(method, params)
        return (await self.send_message(roborock_message))[0]

    async def async_local_response(self, roborock_message: RoborockMessage):
        request_id = roborock_message.get_request_id()
        if request_id is None:
            request_id = roborock_message.seq
        # response_protocol = 5 if roborock_message.prefix == secured_prefix else 4
        response_protocol = 4
        (response, err) = await self._async_response(request_id, response_protocol)
        if err:
            raise CommandVacuumError("", err) from err
        _LOGGER.debug(f"id={request_id} Response from {roborock_message.get_method()}: {response}")
        return response

    def _send_msg_raw(self, data: bytes):
        try:
            if not self.transport:
                raise RoborockException("Can not send message without connection")
            self.transport.write(data)
        except Exception as e:
            raise RoborockException(e) from e

    async def send_message(self, roborock_messages: list[RoborockMessage] | RoborockMessage):
        await self.validate_connection()
        if isinstance(roborock_messages, RoborockMessage):
            roborock_messages = [roborock_messages]
        local_key = self.device_info.device.local_key
        msg = RoborockParser.encode(roborock_messages, local_key)
        # Send the command to the Roborock device
        _LOGGER.debug(f"Requesting device with {roborock_messages}")
        self._send_msg_raw(msg)

        responses = await asyncio.gather(
            *[self.async_local_response(roborock_message) for roborock_message in roborock_messages],
            return_exceptions=True,
        )
        exception = next((response for response in responses if isinstance(response, BaseException)), None)
        if exception:
            await self.async_disconnect()
            raise exception
        return responses
