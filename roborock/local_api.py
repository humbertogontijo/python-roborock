from __future__ import annotations

import asyncio
import logging
import socket
from asyncio import Transport, BaseTransport
from typing import Callable, Mapping, Optional

import async_timeout

from .api import QUEUE_TIMEOUT, SPECIAL_COMMANDS, RoborockClient
from .containers import RoborockLocalDeviceInfo
from .exceptions import CommandVacuumError, RoborockConnectionException, RoborockException
from .roborock_message import RoborockMessage, RoborockParser
from .typing import CommandInfoMap, RoborockCommand
from .util import get_running_loop_or_create_one

_LOGGER = logging.getLogger(__name__)


class RoborockLocalClient(RoborockClient):
    def __init__(self, devices_info: Mapping[str, RoborockLocalDeviceInfo]):
        super().__init__("abc", devices_info)
        self.loop = get_running_loop_or_create_one()
        self.device_listener: dict[str, RoborockSocketListener] = {
            device_id: RoborockSocketListener(
                device_info.network_info.ip,
                device_info.device.local_key,
                self.on_message,
            )
            for device_id, device_info in devices_info.items()
        }
        self._batch_structs: list[RoborockMessage] = []
        self._executing = False

    async def async_connect(self) -> None:
        await asyncio.gather(*[listener.connect() for listener in self.device_listener.values()])

    async def async_disconnect(self) -> None:
        for listener in self.device_listener.values():
            listener.disconnect()

    def build_roborock_message(self, method: RoborockCommand, params: Optional[list] = None) -> RoborockMessage:
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

    async def send_command(self, device_id: str, method: RoborockCommand, params: Optional[list] = None):
        roborock_message = self.build_roborock_message(method, params)
        response = (await self.send_message(device_id, roborock_message))[0]
        if isinstance(response, BaseException):
            raise response
        return response

    async def async_local_response(self, roborock_message: RoborockMessage):
        request_id = roborock_message.get_request_id()
        if request_id is not None:
            # response_protocol = 5 if roborock_message.prefix == secured_prefix else 4
            response_protocol = 4
            (response, err) = await self._async_response(request_id, response_protocol)
            if err:
                raise CommandVacuumError("", err) from err
            _LOGGER.debug(f"id={request_id} Response from {roborock_message.get_method()}: {response}")
            return response

    async def send_message(self, device_id: str, roborock_messages: list[RoborockMessage] | RoborockMessage):
        if isinstance(roborock_messages, RoborockMessage):
            roborock_messages = [roborock_messages]
        local_key = self.devices_info[device_id].device.local_key
        msg = RoborockParser.encode(roborock_messages, local_key)
        # Send the command to the Roborock device
        listener = self.device_listener.get(device_id)
        if listener is None:
            raise RoborockException(f"No device listener for {device_id}")
        _LOGGER.debug(f"Requesting device with {roborock_messages}")
        await listener.send_message(msg)

        return await asyncio.gather(
            *[self.async_local_response(roborock_message) for roborock_message in roborock_messages],
            return_exceptions=True,
        )


class RoborockSocket(socket.socket):
    _closed = None

    @property
    def is_closed(self):
        return self._closed


class RoborockSocketListener(asyncio.Protocol):
    roborock_port = 58867

    def __init__(
        self,
        ip: str,
        local_key: str,
        on_message: Callable[[list[RoborockMessage]], None],
        timeout: float | int = QUEUE_TIMEOUT,
    ):
        self.ip = ip
        self.local_key = local_key
        self.loop = get_running_loop_or_create_one()
        self.on_message = on_message
        self.timeout = timeout
        self.remaining = b""
        self.transport: Transport | None = None

    def data_received(self, message):
        if self.remaining:
            message = self.remaining + message
            self.remaining = b""
        (parser_msg, remaining) = RoborockParser.decode(message, self.local_key)
        self.remaining = remaining
        self.on_message(parser_msg)

    def connection_lost(self, exc):
        print("The server closed the connection")

    def is_connected(self):
        return self.transport and self.transport.is_reading()

    async def connect(self):
        try:
            if not self.is_connected():
                async with async_timeout.timeout(self.timeout):
                    _LOGGER.info(f"Connecting to {self.ip}")
                    self.transport, _ = await self.loop.create_connection(lambda: self, self.ip, 58867)  # type: ignore
        except Exception as e:
            raise RoborockConnectionException(f"Failed connecting to {self.ip}") from e

    def disconnect(self):
        if self.transport:
            self.transport.close()

    async def send_message(self, data: bytes) -> None:
        await self.connect()
        try:
            if not self.transport:
                raise RoborockException("Can not send message without connection")
            self.transport.write(data)
        except Exception as e:
            raise RoborockException(e) from e
