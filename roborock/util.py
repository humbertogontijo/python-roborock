from __future__ import annotations

import asyncio
import datetime
import functools
from asyncio import AbstractEventLoop
from typing import Callable, Coroutine, Optional, TypeVar

T = TypeVar("T")
DEFAULT_TIME_ZONE: datetime.tzinfo = datetime.timezone.utc


def unpack_list(value: list[T], size: int) -> list[Optional[T]]:
    return (value + [None] * size)[:size]  # type: ignore


def get_running_loop_or_create_one() -> AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def parse_time_to_datetime(initial_time: datetime.time) -> datetime.datetime:
    """Help to handle time data."""
    time = datetime.datetime.now(DEFAULT_TIME_ZONE).replace(
        hour=initial_time.hour, minute=initial_time.minute, second=0, microsecond=0
    )

    if time < datetime.datetime.now(DEFAULT_TIME_ZONE):
        time += datetime.timedelta(days=1)

    return time


def run_sync():
    loop = get_running_loop_or_create_one()

    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return loop.run_until_complete(func(*args, **kwargs))

        return wrapped

    return decorator


class CacheableResult:
    last_run_result = None


RT = TypeVar("RT", bound=Callable[..., Coroutine])


def fallback_cache(func: RT) -> RT:
    cache = CacheableResult()

    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            last_run_result = await func(*args, **kwargs)
            cache.last_run_result = last_run_result
        except Exception as e:
            if cache.last_run_result is None:
                raise e
            last_run_result = cache.last_run_result
            cache.last_run_result = None
            return last_run_result
        return last_run_result

    return wrapped  # type: ignore
