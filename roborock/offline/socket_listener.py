from __future__ import annotations

import socket
from asyncio import AbstractEventLoop

import async_timeout


class RoborockSocketListener:
    roborock_port = 58867

    def __init__(self, ip: str, loop: AbstractEventLoop, on_message, timeout: float | int = 4):
        self.ip = ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.loop = loop
        self.on_message = on_message
        self.timeout = timeout

    async def connect(self):
        async with async_timeout.timeout(self.timeout):
            await self.loop.sock_connect(self.socket, ("192.168.1.232", 58867))

    async def send_message(self, data):
        response = {}
        async with async_timeout.timeout(self.timeout):
            await self.loop.sock_sendall(self.socket, data)
            while response.get('protocol') != 4:
                message = await self.loop.sock_recv(self.socket, 4096)
                response = self.on_message(message)
        return response
