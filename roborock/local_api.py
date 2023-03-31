from __future__ import annotations

import asyncio
import logging
import socket

import async_timeout

from roborock.api import RoborockClient
from roborock.typing import RoborockCommand
from roborock.util import get_running_loop_or_create_one
from roborock.exceptions import RoborockTimeout

secured_prefix = 199
_LOGGER = logging.getLogger(__name__)


class RoborockLocalClient(RoborockClient):

    def __init__(self, ip: str, endpoint: str, device_localkey: dict[str, str]):
        super().__init__(endpoint, device_localkey, True)
        self.listener = RoborockSocketListener(ip, super()._decode_msg)

    async def async_connect(self):
        await self.listener.connect()

    async def send_command(
            self, device_id: str, method: RoborockCommand, params: list = None
    ):
        request_id, timestamp, payload = super()._get_payload(method, params)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        prefix = secured_prefix
        protocol = 4
        msg = self._get_msg_raw(device_id, protocol, timestamp, payload, prefix)
        _LOGGER.debug(f"Requesting with prefix {prefix} and payload {payload}")
        # Send the command to the Roborock device
        response = await self.listener.send_message(msg, self.device_localkey.get(device_id))
        _LOGGER.debug(f"id={request_id} Response from {method}: {response}")
        return response


class RoborockSocketListener:
    roborock_port = 58867

    def __init__(self, ip: str, on_message, timeout: float | int = 4):
        self.ip = ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.loop = get_running_loop_or_create_one()
        self.on_message = on_message
        self.timeout = timeout

    async def connect(self):
        async with async_timeout.timeout(self.timeout):
            await self.loop.sock_connect(self.socket, (self.ip, 58867))

    async def send_message(self, data: bytes, local_key: str):
        response = {}
        try:
            async with async_timeout.timeout(self.timeout):
                await self.loop.sock_sendall(self.socket, data)
                while response.get('protocol') != 4:
                    message = await self.loop.sock_recv(self.socket, 4096)
                    response = self.on_message(message, local_key)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            raise RoborockTimeout(
                f"Timeout after {self.timeout} seconds waiting for response"
            ) from None
        return response
