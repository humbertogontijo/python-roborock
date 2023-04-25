from __future__ import annotations

import asyncio
import functools
from asyncio import AbstractEventLoop
from typing import Optional, TypeVar

T = TypeVar("T")


def unpack_list(value: list[T], size: int) -> list[Optional[T]]:
    return (value + [None] * size)[:size]  # type: ignore


def get_running_loop_or_create_one() -> AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_sync():
    loop = get_running_loop_or_create_one()

    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return loop.run_until_complete(func(*args, **kwargs))

        return wrapped

    return decorator
