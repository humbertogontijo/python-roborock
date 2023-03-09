from __future__ import annotations

from asyncio import Queue
from typing import Any

import async_timeout

from .exceptions import VacuumError


class RoborockQueue(Queue):
    def __init__(self, protocol: int, *args):
        super().__init__(*args)
        self.protocol = protocol

    async def async_put(self, item: tuple[Any, VacuumError | None], timeout: float | int) -> None:
        async with async_timeout.timeout(timeout):
            await self.put(item)

    async def async_get(self, timeout: float | int) -> tuple[Any, VacuumError | None]:
        async with async_timeout.timeout(timeout):
            return await self.get()
