from __future__ import annotations

import asyncio
import logging
import socket
from asyncio import Lock
from typing import Callable, Coroutine

import async_timeout

from roborock.api import RoborockClient, SPECIAL_COMMANDS
from roborock.exceptions import RoborockTimeout, CommandVacuumError
from roborock.typing import RoborockCommand
from roborock.util import get_running_loop_or_create_one

secured_prefix = 199
get_prefix = 119
app_prefix = 135
set_prefix = 151

_LOGGER = logging.getLogger(__name__)


class RoborockLocalClient(RoborockClient):

    def __init__(self, ip: str, endpoint: str, device_localkey: dict[str, str]):
        super().__init__(endpoint, device_localkey, True)
        self.device_listener: dict[str, RoborockSocketListener] = {
            device_id: RoborockSocketListener(ip, device_id, self.on_message)
            for device_id in device_localkey
        }

    async def async_connect(self):
        await asyncio.gather(*[
            listener.connect()
            for listener in self.device_listener.values()
        ])

    async def send_command(
            self, device_id: str, method: RoborockCommand, params: list = None
    ):
        secured = True if method in SPECIAL_COMMANDS else False
        request_id, timestamp, payload = self._get_payload(method, params, secured)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        prefix = secured_prefix if method in SPECIAL_COMMANDS else get_prefix
        protocol = 4
        msg = self._encode_msg(device_id, protocol, timestamp, payload, prefix)
        _LOGGER.debug(f"Requesting with prefix {prefix} and payload {payload}")
        # Send the command to the Roborock device
        listener = self.device_listener.get(device_id)
        await listener.send_message(msg, self.device_localkey.get(device_id))
        (response, err) = await self._async_response(request_id, 4)
        if err:
            raise CommandVacuumError(method, err) from err
        _LOGGER.debug(f"id={request_id} Response from {method}: {response}")
        return response

class RoborockSocket(socket.socket):
    _closed = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def is_closed(self):
        return self._closed

class RoborockSocketListener:
    roborock_port = 58867

    def __init__(self, ip: str, device_id: str, on_message: Callable[[str, bytes], Coroutine[bool] | bool],
                 timeout: float | int = 4):
        self.ip = ip
        self.device_id = device_id
        self.socket = RoborockSocket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.loop = get_running_loop_or_create_one()
        self.on_message = on_message
        self.timeout = timeout
        self.is_connected = False
        self._lock = Lock()

    async def _main_coro(self):
        while not self.socket.is_closed:
            try:
                message = await self.loop.sock_recv(self.socket, 4096)
                accepted = await self.on_message(self.device_id, message)
                if accepted:
                    self._lock.release() if self._lock.locked() else None
            except Exception as e:
                _LOGGER.exception(e)
                self.is_connected = False
        await self.connect()

    async def connect(self):
        async with async_timeout.timeout(self.timeout):
            await self.loop.sock_connect(self.socket, (self.ip, 58867))
            self.is_connected = True
        self.loop.create_task(self._main_coro())

    async def send_message(self, data: bytes, local_key: str):
        response = {}
        try:
            async with async_timeout.timeout(self.timeout):
                await self._lock.acquire()
                await self.loop.sock_sendall(self.socket, data)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            self._lock.release() if self._lock.locked() else None
            raise RoborockTimeout(
                f"Timeout after {self.timeout} seconds waiting for response"
            ) from None
        return response
