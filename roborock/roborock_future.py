from __future__ import annotations

from asyncio import Future
from typing import Any

import async_timeout

from .exceptions import VacuumError


class RoborockFuture:
    def __init__(self, protocol: int):
        self.protocol = protocol
        self.fut: Future = Future()
        self.loop = self.fut.get_loop()

    def resolve(self, item: tuple[Any, VacuumError | None]) -> None:
        self.loop.call_soon_threadsafe(self.fut.set_result, item)

    async def async_get(self, timeout: float | int) -> tuple[Any, VacuumError | None]:
        try:
            async with async_timeout.timeout(timeout):
                return await self.fut
        finally:
            self.fut.cancel()
