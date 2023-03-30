from __future__ import annotations

import socket
import threading
from asyncio import AbstractEventLoop

import async_timeout

from roborock.exceptions import RoborockException


class RoborockSocketListener:
    roborock_port = 58867

    def __init__(self, ip: str, loop: AbstractEventLoop, on_message):
        self.ip = ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.loop = loop
        self.on_message = on_message

    def connect(self):
        self.socket.connect(("192.168.1.232", 58867))

    async def send_message(self, data, timeout: float | int = 4):
        response = {}
        async with async_timeout.timeout(timeout):
            await self.loop.sock_sendall(self.socket, data)
            while response.get('protocol') != 4:
                message = await self.loop.sock_recv(self.socket, 4096)
                response = self.on_message(message)
        return response
