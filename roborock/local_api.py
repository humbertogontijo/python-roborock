from __future__ import annotations

import asyncio
import logging
import socket
from asyncio import Lock
from typing import Callable, Coroutine

import async_timeout

from roborock.api import RoborockClient, SPECIAL_COMMANDS
from roborock.containers import RoborockLocalDeviceInfo
from roborock.exceptions import RoborockTimeout, CommandVacuumError, RoborockConnectionException, RoborockException
from roborock.roborock_message import RoborockParser, RoborockMessage
from roborock.typing import RoborockCommand, CommandInfoMap
from roborock.util import get_running_loop_or_create_one

_LOGGER = logging.getLogger(__name__)


class RoborockLocalClient(RoborockClient):

    def __init__(self, devices_info: dict[str, RoborockLocalDeviceInfo]):
        super().__init__("abc", devices_info)
        self.loop = get_running_loop_or_create_one()
        self.device_listener: dict[str, RoborockSocketListener] = {
            device_id: RoborockSocketListener(
                device_info.network_info.ip,
                device_info.device.local_key,
                self.on_message
            )
            for device_id, device_info in devices_info.items()
        }
        self._mutex = Lock()
        self._batch_structs: list[RoborockMessage] = []
        self._executing = False

    async def async_connect(self):
        await asyncio.gather(*[
            listener.connect()
            for listener in self.device_listener.values()
        ])

    async def async_disconnect(self) -> None:
        await asyncio.gather(*[listener.disconnect() for listener in self.device_listener.values()])

    def build_roborock_message(
            self, method: RoborockCommand, params: list = None
    ) -> RoborockMessage:
        secured = True if method in SPECIAL_COMMANDS else False
        request_id, timestamp, payload = self._get_payload(method, params, secured)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        command_info = CommandInfoMap.get(method)
        if not command_info:
            raise RoborockException(f"Request {method} have unknown prefix. Can't execute in offline mode")
        prefix = CommandInfoMap.get(method).prefix
        request_protocol = 4
        return RoborockMessage(
            prefix=prefix,
            timestamp=timestamp,
            protocol=request_protocol,
            payload=payload
        )

    async def send_command(
            self, device_id: str, method: RoborockCommand, params: list = None
    ):
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

    async def send_message(
            self, device_id: str, roborock_messages: list[RoborockMessage] | RoborockMessage
    ):
        if isinstance(roborock_messages, RoborockMessage):
            roborock_messages = [roborock_messages]
        local_key = self.devices_info[device_id].device.local_key
        msg = RoborockParser.encode(roborock_messages, local_key)
        # Send the command to the Roborock device
        listener = self.device_listener.get(device_id)
        _LOGGER.debug(f"Requesting device with {roborock_messages}")
        await listener.send_message(msg)

        return await asyncio.gather(
            *[self.async_local_response(roborock_message) for roborock_message in roborock_messages],
            return_exceptions=True)


class RoborockSocket(socket.socket):
    _closed = None

    @property
    def is_closed(self):
        return self._closed


class RoborockSocketListener:
    roborock_port = 58867

    def __init__(self, ip: str, local_key: str, on_message: Callable[[list[RoborockMessage]], Coroutine[None] | None],
                 timeout: float | int = 4):
        self.ip = ip
        self.local_key = local_key
        self.socket = RoborockSocket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.loop = get_running_loop_or_create_one()
        self.on_message = on_message
        self.timeout = timeout
        self.is_connected = False
        self._mutex = Lock()
        self.remaining = b''

    async def _main_coro(self):
        while not self.socket.is_closed:
            try:
                message = await self.loop.sock_recv(self.socket, 4096)
                try:
                    if self.remaining:
                        message = self.remaining + message
                        self.remaining = b''
                    (parser_msg, remaining) = RoborockParser.decode(message, self.local_key)
                    self.remaining = remaining
                    await self.on_message(parser_msg)
                except Exception as e:
                    _LOGGER.exception(e)
            except BrokenPipeError as e:
                _LOGGER.exception(e)
                await self.disconnect()

    async def connect(self):
        async with self._mutex:
            if not self.is_connected or self.socket.is_closed:
                self.socket = RoborockSocket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setblocking(False)
                try:
                    async with async_timeout.timeout(self.timeout):
                        _LOGGER.info(f"Connecting to {self.ip}")
                        await self.loop.sock_connect(self.socket, (self.ip, 58867))
                        self.is_connected = True
                except Exception as e:
                    await self.disconnect()
                    raise RoborockConnectionException(f"Failed connecting to {self.ip}") from e
                self.loop.create_task(self._main_coro())

    async def disconnect(self):
        self.socket.close()
        self.is_connected = False

    async def send_message(self, data: bytes):
        response = {}
        await self.connect()
        try:
            async with self._mutex:
                async with async_timeout.timeout(self.timeout):
                    await self.loop.sock_sendall(self.socket, data)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            raise RoborockTimeout(
                f"Timeout after {self.timeout} seconds waiting for response"
            ) from None
        except BrokenPipeError as e:
            _LOGGER.exception(e)
            await self.disconnect()
        return response
