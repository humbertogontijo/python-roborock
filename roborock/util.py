from __future__ import annotations

import asyncio
import functools
from asyncio import AbstractEventLoop
from typing import Callable, Coroutine, Optional, TypeVar

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


class CacheableResult:
    last_run_result = None
    use_count = 0


RT = TypeVar("RT", bound=Callable[..., Coroutine])


def fallback_cache(func: RT) -> RT:
    cache = CacheableResult()

    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            cache.last_run_result = await func(*args, **kwargs)
            cache.use_count = 0
        except Exception as e:
            if cache.last_run_result is None or cache.use_count > 0:
                raise e
            cache.last_run_result.is_cached = True
            cache.use_count += 1
        return cache.last_run_result

    return wrapped  # type: ignore
