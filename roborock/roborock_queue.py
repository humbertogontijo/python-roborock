import asyncio
from asyncio import Queue
from typing import Any

from .exceptions import RoborockException


class RoborockQueue(Queue):

    def __init__(self, protocol: int, *args):
        super().__init__(*args)
        self.protocol = protocol

    async def async_put(self, item: tuple[Any, RoborockException | None], timeout: float | int) -> None:
        return await asyncio.wait_for(self.put(item), timeout=timeout)

    async def async_get(self, timeout: float | int) -> tuple[Any, RoborockException | None]:
        return await asyncio.wait_for(self.get(), timeout=timeout)
